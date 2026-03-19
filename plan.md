# Plan : Proxy OpenAI-compatible via Claude Code CLI

## Objectif

Créer un serveur proxy local qui expose une API OpenAI-compatible (`/v1/chat/completions`) et route les requêtes vers la CLI `claude` (Claude Code). Cela permet à MiroFish d'utiliser Claude via le plan Max sans payer l'API Anthropic.

## Architecture

```
MiroFish Backend (OpenAI SDK)
        │
        ▼
   LLM_BASE_URL=http://localhost:8082/v1
        │
        ▼
┌─────────────────────────────┐
│  Claude Proxy Server (8082) │
│  - Flask/FastAPI            │
│  - /v1/chat/completions     │
│  - /v1/models               │
└──────────┬──────────────────┘
           │ subprocess
           ▼
     claude -p --output-format json
           │
           ▼
     Claude (plan Max)
```

## Étapes d'implémentation

### Étape 1 : Créer le proxy server (`claude-proxy/`)

**Fichier : `claude-proxy/server.py`**

Serveur Flask léger qui :
- Écoute sur le port 8082 (configurable via env `CLAUDE_PROXY_PORT`)
- Implémente `POST /v1/chat/completions` (format OpenAI)
- Implémente `GET /v1/models` (liste les modèles Claude disponibles)
- Traduit les messages OpenAI en prompt pour `claude -p`
- Gère le `response_format: {"type": "json_object"}` en ajoutant une instruction dans le system prompt
- Retourne les réponses au format OpenAI

**Logique de traduction des messages :**
```python
# Input OpenAI format:
{"messages": [
    {"role": "system", "content": "Tu es un expert..."},
    {"role": "user", "content": "Analyse ce texte"},
    {"role": "assistant", "content": "Voici mon analyse..."},
    {"role": "user", "content": "Continue"}
]}

# → Extraction du system prompt → --system-prompt flag
# → Formatage des messages user/assistant en prompt unique :
#   "Previous conversation:\nUser: Analyse ce texte\nAssistant: Voici mon analyse...\n\nUser: Continue"
# → Appel: claude -p "<prompt>" --system-prompt "<system>" --output-format json --model <model>
```

**Format de réponse retourné :**
```json
{
  "id": "chatcmpl-<uuid>",
  "object": "chat.completion",
  "model": "claude-sonnet-4-6",
  "choices": [{
    "index": 0,
    "message": {"role": "assistant", "content": "..."},
    "finish_reason": "stop"
  }],
  "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
}
```

### Étape 2 : Créer le script d'appel CLI (`claude-proxy/claude_runner.py`)

Module Python qui :
- Exécute `claude -p` via `subprocess.run()` avec timeout configurable
- Passe `--system-prompt` si un system message est présent
- Passe `--model` selon le modèle demandé (mapping : `gpt-4o` → `sonnet`, `gpt-4` → `opus`, etc.)
- Passe `--output-format json` pour parser la réponse
- Gère les erreurs (timeout, CLI non trouvée, etc.)
- Supporte un pool de workers pour les requêtes concurrentes (via `concurrent.futures.ThreadPoolExecutor`)

### Étape 3 : Gestion du JSON mode

Quand MiroFish envoie `response_format: {"type": "json_object"}` :
- Ajouter au system prompt : `"IMPORTANT: You MUST respond with valid JSON only. No markdown, no explanation, just a JSON object."`
- Valider que la réponse est du JSON valide
- Si ce n'est pas du JSON, tenter d'extraire le JSON du texte (entre ```json``` blocks)
- Retenter une fois si échec

### Étape 4 : Configuration et lancement

**Fichier : `claude-proxy/requirements.txt`**
```
flask>=3.0
```

**Fichier : `claude-proxy/run.sh`**
```bash
#!/bin/bash
# Lance le proxy Claude
pip install flask  # ou uv pip install
python server.py
```

**Variables d'environnement du proxy :**
- `CLAUDE_PROXY_PORT` : Port du proxy (défaut: 8082)
- `CLAUDE_PROXY_MODEL` : Modèle par défaut (défaut: `sonnet`)
- `CLAUDE_PROXY_TIMEOUT` : Timeout en secondes (défaut: 120)
- `CLAUDE_PROXY_MAX_WORKERS` : Nombre max de requêtes concurrentes (défaut: 4)

### Étape 5 : Intégration avec MiroFish

**Changements minimaux dans MiroFish :**

1. **`.env.example`** — Ajouter un commentaire/section pour le mode Claude proxy :
   ```env
   # Option B: Claude via Claude Code proxy (plan Max)
   # LLM_BASE_URL=http://localhost:8082/v1
   # LLM_API_KEY=not-needed
   # LLM_MODEL_NAME=claude-sonnet-4-6
   ```

2. **`backend/app/utils/llm_client.py`** — Aucune modification nécessaire ! Le proxy est OpenAI-compatible, donc le SDK OpenAI existant fonctionne tel quel.

3. **`backend/app/config.py`** — Rendre `LLM_API_KEY` optionnel quand on utilise le proxy (le proxy n'a pas besoin de clé API).

4. **OASIS/CAMEL** — Les scripts de simulation utilisent aussi `OpenAI()` client, donc ils fonctionneront avec le proxy sans modification.

5. **`package.json`** (root) — Ajouter un script pour lancer le proxy :
   ```json
   "proxy": "cd claude-proxy && python server.py",
   "dev:claude": "concurrently \"npm run proxy\" \"npm run backend\" \"npm run frontend\""
   ```

6. **`docker-compose.yml`** — Ajouter un service optionnel pour le proxy.

### Étape 6 : Documentation

Ajouter une section dans `CLAUDE.md` ou créer `claude-proxy/README.md` expliquant :
- Prérequis : Claude Code CLI installé et authentifié avec plan Max
- Comment lancer le proxy
- Comment configurer MiroFish pour utiliser le proxy
- Limitations connues

## Limitations connues

1. **Pas de temperature/max_tokens via CLI** — La CLI `claude` ne supporte pas ces paramètres. Le proxy les ignorera silencieusement.
2. **Latence** — Chaque requête lance un subprocess `claude`, ajoutant ~1-2s de latence.
3. **Concurrence limitée** — Le plan Max peut avoir des limites d'utilisation concurrente. Le pool de workers (défaut: 4) limite les appels parallèles.
4. **Pas de streaming** — La v1 du proxy ne supportera pas le streaming SSE. Les réponses seront complètes.
5. **Contexte multi-tour** — Les conversations multi-tour sont "aplaties" en un seul prompt, ce qui peut perdre de la nuance sur de longues conversations.
6. **JSON mode** — Pas de garantie native comme avec OpenAI. Mitigation via prompt engineering + validation.

## Ordre d'implémentation

1. `claude-proxy/claude_runner.py` — Module d'appel CLI (testable isolément)
2. `claude-proxy/server.py` — Serveur proxy Flask
3. Intégration `.env.example` + `config.py` (clé API optionnelle)
4. Scripts `package.json` pour lancement facile
5. `docker-compose.yml` — Service optionnel
6. Tests manuels end-to-end avec MiroFish

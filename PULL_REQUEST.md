# PR — feat: Private Impact Simulation Mode

**Branche** : `feature/private-impact` → `main`
**Date** : 2026-04-16
**Auteur** : Cyril / iapluska

---

## Description

Ajout d'un second mode de simulation : **Private Impact**.

Contrairement au mode public (réseau social ouvert, diffusion virale), le mode Private Impact simule la propagation d'une décision dans un **réseau relationnel fermé et pondéré** : entourage professionnel, conseil d'administration, associés, investisseurs, équipe dirigeante.

Chaque agent est modélisé avec 8 champs relationnels (rôle, loyauté, influence, résistance au changement, historique de conflit, visibilité publique, accès décisionnel, sensibilité financière). La simulation prédit comment la décision se propage, qui bloque, qui amplifie, et quel est l'impact final agrégé.

---

## Cas d'usage concrets

### 1 — PDG envisage d'acheter une Rolls-Royce (dépense de prestige)
- Agents : DRH, DAF, actionnaires principaux, conseil, assistante de direction
- Question : cette dépense va-t-elle générer un retour d'image interne positif ou créer des tensions ?
- Résultat : score d'impact + profils de résistance identifiés

### 2 — Fondateur annonce une levée de fonds série A
- Agents : co-fondateurs, investisseurs seed, équipe technique, board advisor
- Question : quels agents freinent l'annonce, quels agents l'amplifient ?
- Résultat : carte de propagation + recommandations de communication interne

### 3 — Collectivité locale annonce une fermeture de service
- Agents : élus, directeurs de service, syndicats, presse locale, usagers clés
- Question : quel est le risque de crise avant annonce publique ?
- Résultat : score de risque + délai de propagation estimé

---

## Fichiers créés (nouveaux)

| Fichier | Rôle |
|---|---|
| `backend/app/api/private.py` | Blueprint Flask — 7 endpoints `/api/private-impact/*` |
| `backend/app/services/private_impact_profile_generator.py` | Génération des profils relationnels via LLM |
| `backend/app/services/private_impact_config_generator.py` | Configuration réseau + paramètres de simulation |
| `backend/app/services/private_impact_runner.py` | Moteur de simulation fermé (sans plateforme sociale) |
| `backend/scripts/run_private_simulation.py` | Script standalone — exécution sans API |
| `frontend/src/api/private.js` | Client API frontend pour les endpoints private |
| `frontend/src/components/ModeSelector.vue` | Sélecteur de mode (Public / Private) sur Home |
| `frontend/src/views/PrivateImpactView.vue` | Wizard 5 étapes — interface complète Private Impact |
| `CONTEXT.md` | Journal de développement de la feature (12 prompts) |

---

## Fichiers modifiés (extensions chirurgicales)

| Fichier | Modification |
|---|---|
| `backend/app/__init__.py` | Enregistrement du blueprint `private_impact` |
| `backend/app/api/__init__.py` | Export du blueprint |
| `backend/app/services/simulation_runner.py` | 6 extensions — support mode privé dans le runner public |
| `backend/run.py` | Import du blueprint private |
| `backend/scripts/action_logger.py` | Support logging mode private |
| `frontend/src/api/index.js` | Export centralisé des API |
| `frontend/src/router/index.js` | Nouvelle route `/private/:projectId` |
| `frontend/src/views/Home.vue` | Intégration ModeSelector |
| `frontend/src/views/MainView.vue` | Redirection post-création selon `pendingSimMode` |
| `frontend/vite.config.js` | Ajustement proxy pour nouveaux endpoints |

---

## Zéro breaking change — garanti

- Le mode public est **inchangé fonctionnellement** : toutes les routes, composants et services existants conservent leur comportement exact.
- Le `ModeSelector` est **opt-in** : sans sélection, le comportement par défaut reste le mode public.
- La lecture de `sessionStorage.pendingSimMode` est **non-bloquante** : si absent, fallback silencieux sur le flow public.
- Le blueprint `/api/private-impact` est un **module isolé**, sans dépendance croisée avec `/api/graph` ou `/api/simulation`.
- Les 6 modifications de `simulation_runner.py` sont toutes **conditionnelles** (guards `if mode == 'private'`).

---

## Instructions de test

### Prérequis
```bash
# Backend
pip install -r backend/requirements.txt
python backend/run.py

# Frontend
cd frontend && npm install && npm run dev
```

### Test mode Public (régression)
1. Aller sur `http://localhost:5173`
2. Ne pas interagir avec le ModeSelector (ou sélectionner "Public")
3. Uploader des fichiers et lancer une simulation
4. Vérifier : redirection vers `/main/:projectId` → comportement inchangé

### Test mode Private Impact
1. Aller sur `http://localhost:5173`
2. Cliquer sur **"Private Impact"** dans le ModeSelector
3. Uploader des documents (ex : organigramme, biographies courtes des agents)
4. Remplir le champ "simulation_requirement" avec une décision à tester
5. Vérifier : après création projet → redirection vers `/private/:projectId`
6. Suivre le wizard 5 étapes :
   - Étape 1 : Génération des profils relationnels
   - Étape 2 : Configuration du réseau
   - Étape 3 : Lancement simulation
   - Étape 4 : Rapport d'impact
   - Étape 5 : Recommandations

### Test API standalone
```bash
cd backend
python scripts/run_private_simulation.py \
  --project-id <project_id> \
  --decision "Acquisition véhicule de prestige 350k€"
```

### Endpoints à vérifier
```
POST /api/private-impact/generate-profiles
POST /api/private-impact/generate-config
POST /api/private-impact/run
GET  /api/private-impact/status/<task_id>
GET  /api/private-impact/result/<project_id>
GET  /api/private-impact/project/<project_id>
DELETE /api/private-impact/project/<project_id>
```

---

## Notes de merge

- Ne pas squash : l'historique des 12 prompts est documenté dans `CONTEXT.md`
- Aucune migration de base de données requise
- Aucune variable d'environnement nouvelle requise (réutilise les clés LLM existantes)

# MiroFish — Fork Context (Private Impact Feature)

## Branche de travail
`feature/private-impact`

## Remotes
- `origin` → https://github.com/CyrilDEVIA/MiroResult.git (fork perso)
- `upstream` → https://github.com/666ghj/MiroFish.git (repo original)

---

## Historique des sessions

### 2026-04-16 — Session 1

#### Étapes terminées
- [x] **Prompt N°01** — Lecture complète du code source (audit, zéro modification)
- [x] **Prompt N°02** — Setup Git : fork + remote + branche `feature/private-impact`
- [x] **Prompt N°03** — Création `backend/scripts/run_private_simulation.py`
- [x] **Prompt N°04** — Création `backend/app/services/private_impact_profile_generator.py`
- [x] **Prompt N°05** — Création `backend/app/services/private_impact_config_generator.py`
- [x] **Prompt N°06** — Création `backend/app/services/private_impact_runner.py`
- [x] **Prompt N°07** — Blueprint `backend/app/api/private.py` + enregistrement (`api/__init__.py`, `app/__init__.py`)
- [x] **Prompt N°08** — Modification `backend/app/services/simulation_runner.py` (7 zones : champs private_*, start, monitor, read_log, check_completed, get_actions, cleanup)
- [x] **Prompt N°09** — Frontend : `api/private.js` + `ModeSelector.vue` + `PrivateImpactView.vue` + route `/private/:projectId`
- [x] **Prompt N°10** — `action_logger.py` : ajout `get_private_logger()` + suppression fallback `run_private_simulation.py` + intégration `ModeSelector` dans `Home.vue`

#### Fichiers créés / modifiés
| Fichier | Action |
|---|---|
| `backend/scripts/run_private_simulation.py` | Créé — moteur de simulation privé |
| `backend/scripts/private/` | Créé — répertoire de sortie actions.jsonl |
| `backend/app/services/private_impact_profile_generator.py` | Créé — générateur de profils relationnels |
| `backend/app/services/private_impact_config_generator.py` | Créé — générateur de paramètres comportementaux |
| `backend/app/services/private_impact_runner.py` | Créé — orchestrateur subprocess + monitoring |
| `CONTEXT.md` | Créé — ce fichier |
| `backend/app/api/private.py` | Créé — blueprint Flask /api/private-impact (7 routes) |
| `backend/app/api/__init__.py` | Modifié — ajout private_bp + import private |
| `backend/app/__init__.py` | Modifié — enregistrement private_bp |
| `backend/app/services/simulation_runner.py` | Modifié — 7 zones private (champs, start, monitor, read_log, check, get_actions, cleanup) |
| `frontend/src/api/private.js` | Créé — client API private impact (7 fonctions) |
| `frontend/src/components/ModeSelector.vue` | Créé — sélecteur Public / Private Impact (2 cartes) |
| `frontend/src/views/PrivateImpactView.vue` | Créé — wizard 5 étapes (form → prepare → run → report → chat) |
| `frontend/src/router/index.js` | Modifié — route `/private/:projectId` ajoutée |
| `backend/scripts/action_logger.py` | Modifié — ajout `get_private_logger()` à `SimulationLogManager` |
| `backend/scripts/run_private_simulation.py` | Modifié — suppression fallback `hasattr`, appel direct `log_manager.get_private_logger()` |
| `frontend/src/views/Home.vue` | Modifié — intégration `ModeSelector` (right panel) + `handleModeSelected` + sessionStorage `pendingSimMode` |

#### Décisions d'architecture prises
- Pas d'env OASIS (pas de Twitter/Reddit/PlatformConfig)
- Appels LLM directs via `camel-ai ChatAgent` + `asyncio.to_thread()`
- Graphe relationnel construit depuis `cascade_influence` dans agent_configs
- `REACT_PRIVATELY` = invisible → ne propage pas l'exposition
- Tous les autres actions (sauf `DO_NOTHING`) cascade vers `cascade_influence` targets
- `zep_graph_memory_updater.py` réutilisé sans modification (platform="private")
- IPC `PrivateIPCHandler` : interviews via LLM direct (pas de SQLite)
- Output : `private/actions.jsonl` (même format JSONL que twitter/reddit)
- `RelationalAgentProfile` hérite de `OasisAgentProfile` — 8 champs relationnels ajoutés
- Encodage des dimensions relationnelles dans le champ `persona` (texte naturel)
- Fallback rule-based par type : Employee, Manager, Client, Competitor, Partner, FamilyMember
- `to_private_format()` retourne le dict lu par `run_private_simulation.py`
- `PrivateImpactConfigGenerator.generate_config()` : entrée = liste de dicts agents (issue de profile_generator), pas d'EntityNode direct
- `PrivateTimeConfig` : jours + rounds/jour (matin/midi/soir) — pas d'heures ni timezone
- `PrivateEventConfig` : injection par `decision_statement` — pas de posts sociaux
- `RelationalActivityConfig.exposure_round` : round 0 = exposition directe (distance 1)
- Fallback rule-based : table `RELATIONAL_FALLBACKS` dans le générateur (6 types)
- `PrivateImpactRunner` : même pattern classmethods que `SimulationRunner` (états en mémoire de classe)
- Config lue depuis `private_simulation_config.json` (≠ `simulation_config.json` OASIS)
- Log unique : `{sim_dir}/private/actions.jsonl` (une seule plateforme)
- `PrivateRunnerStatus` : enum séparé — pas de réutilisation de `RunnerStatus`
- `private_simulated_days` lu depuis le champ `simulated_day` du `round_end` event
- Frontend : CSS plain (pas Tailwind — non présent dans package.json) — même style que les vues existantes
- `ModeSelector.vue` : composant standalone, émet `@mode-selected` avec `"public"` ou `"private"`, à intégrer manuellement dans `Home.vue` ou `Process.vue`
- `PrivateImpactView.vue` : route `/private/:projectId` — charge le projet via `getProject()` pour récupérer `graph_id`
- Step 3 : polling `/api/private-impact/status/{simId}` toutes les 3s + affichage `recent_actions` depuis `to_detail_dict()`
- Step 4 : report via `generatePrivateReport()` → task_id → polling `getReportStatus(reportId)` → `getReport(reportId)` (réutilise le ReportManager existant)
- Step 5 : `chatAgents` reconstruit depuis la liste d'actions (agent_id + agent_name) ; chat via `interviewAgents()` (réutilise simulation.js)
- `SimulationRunState` : 5 champs `private_*` ajoutés (current_round, simulated_days, running, actions_count, completed)
- `add_action()` : elif platform=="private" → private_actions_count (évite comptage dans reddit)
- `to_dict()` : private_* inclus dans total_actions_count
- `start_simulation()` : elif platform=="private" → run_private_simulation.py + private_running=True
- `_monitor_simulation()` : lecture `private/actions.jsonl` dans la boucle ET en final ; private_running=False à la fin
- `_read_action_log()` : simulation_end → private_completed=True ; round_end → private_current_round + private_simulated_days (depuis simulated_day)
- `_check_all_platforms_completed()` : private_log + private_enabled + check private_completed
- `get_all_actions()` : bloc private après reddit (même pattern)
- `cleanup_simulation_logs()` : private_simulation.db + dirs_to_clean inclut "private"
- Blueprint `private_bp` enregistré sans url_prefix (les routes déclarent `/api/private-impact/...` en entier)
- `/prepare` stocke les métadonnées (graph_id, sim_requirement, agent_count…) dans `private_meta.json` dans le sim_dir
- `/prepare` appelle `ZepEntityReader.get_entities_by_type()` en boucle sur les types relationnels puis `PrivateImpactProfileGenerator.generate_profiles_from_entities()`
- `/start` lit `private_simulation_config.json` via `PrivateImpactRunner.start_simulation()`
- `/status` retourne `to_detail_dict()` (inclut `recent_actions`)
- `/report` réutilise `ReportAgent` avec `simulation_id=sim_id` et `graph_id` lu depuis `private_meta.json`
- `/cleanup` délègue entièrement à `PrivateImpactRunner.cleanup()`
- `get_private_logger()` ajouté à `SimulationLogManager` — même pattern que `get_twitter_logger()` / `get_reddit_logger()` ; fallback supprimé dans `run_private_simulation.py`
- `ModeSelector` intégré dans `Home.vue` (right panel, au-dessus de `.console-box`) ; mode stocké dans `sessionStorage` (`pendingSimMode`) — `MainView.vue` (N°11) doit lire ce flag et rediriger vers `/private/:projectId` après création du projet

---

## Prochaines étapes

| Prompt | Fichier cible | Action |
|---|---|---|
| N°04 | `backend/app/services/private_impact_profile_generator.py` | ✅ Terminé |
| N°05 | `backend/app/services/private_impact_config_generator.py` | ✅ Terminé |
| N°06 | `backend/app/services/private_impact_runner.py` | ✅ Terminé |
| N°07 | `backend/app/api/private.py` | ✅ Terminé |
| N°07 | `backend/app/api/__init__.py` | ✅ Terminé |
| N°07 | `backend/app/__init__.py` | ✅ Terminé |
| N°08 | `backend/app/services/simulation_runner.py` | ✅ Terminé |
| N°09 | `frontend/src/views/PrivateImpactView.vue` | ✅ Terminé |
| N°09 | `frontend/src/components/ModeSelector.vue` | ✅ Terminé |
| N°10 | `backend/scripts/action_logger.py` | ✅ Terminé — `get_private_logger()` ajouté |
| N°10 | `backend/scripts/run_private_simulation.py` | ✅ Terminé — fallback supprimé |
| N°10 | `frontend/src/views/Home.vue` | ✅ Terminé — ModeSelector intégré |
| N°11 | `frontend/src/views/MainView.vue` | Lire `sessionStorage.pendingSimMode` après création du projet → rediriger vers `/private/:projectId` si 'private' |
| N°11 | Test end-to-end | Préparer → Lancer → Observer actions.jsonl |

## Point d'attention — `MainView.vue` (N°11)
**Status : ⏳ PENDING**

`Home.vue` stocke `sessionStorage.pendingSimMode = 'private'` quand l'utilisateur sélectionne Private Impact.
`MainView.vue` doit être modifié pour lire ce flag après la création du projet + le build du graphe Zep, et rediriger vers `/private/:projectId` au lieu de rester sur la vue OASIS standard.

**Action requise** dans `MainView.vue` — après la séquence upload → create_project → build_graph :
```javascript
const pendingMode = sessionStorage.getItem('pendingSimMode')
if (pendingMode === 'private') {
  sessionStorage.removeItem('pendingSimMode')
  router.push(`/private/${projectId}`)
}
```

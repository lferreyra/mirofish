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

### 2026-04-16 — Session 2 (PrivateImpactView — UX + bug fix)

#### Étapes terminées
- [x] **Prompt N°XX** — Step 3 : graphe de propagation D3 force-directed (nœuds/liens temps réel)
- [x] **Prompt N°05** — Step 1 : bouton "Import config" + parser `private_impact_requirement.txt`
- [x] **Prompt N°06** — Tooltip natif sur le bouton Import
- [x] **Prompt N°07** — Légende fixe sous le bouton Import (`.import-hint`)
- [x] **Prompt N°08** — Drop zone drag & drop (remplace bouton + légende)
- [x] **Prompt N°09** — Parser : extraction du bloc `#CONFIG…#END_CONFIG` en priorité
- [x] **Prompt N°10** — Bug fix : `graph_id` toujours `null` à l'arrivée sur PrivateImpactView

#### Fichiers modifiés
| Fichier | Action |
|---|---|
| `frontend/src/views/PrivateImpactView.vue` | Graphe D3, drop zone import, parser config, polling graph_id |
| `frontend/src/views/MainView.vue` | Ajout `await startBuildGraph()` avant redirect private |

#### Décisions d'architecture — Session 2
- D3 force-directed : `forceManyBody(-120)` + `forceLink(distance 80)` + `forceCenter`
- Couleur nœud = action dominante (CONFRONT→rouge, COALITION_BUILD→orange, VOCAL_SUPPORT→vert…)
- Feed réduit à 10 dernières actions, hauteur 200px fixe sous le graphe
- Import config : `FileReader` natif + drag & drop, parser `#CONFIG…#END_CONFIG` ou fallback ligne par ligne
- **Bug N°10** : `MainView.vue` redirigait vers `/private/:projectId` AVANT d'appeler `startBuildGraph()` → `graph_id` jamais set
  - Fix : `await startBuildGraph()` ajouté avant `router.push()` dans le bloc `pendingMode === 'private'`
  - Robustesse : `PrivateImpactView` polle `getProject()` toutes les 3s si `graph_id` absent au mount
  - UX : notice jaune + bouton "Prepare" désactivé tant que `graph_id` est null

---

### 2026-04-16 — Session 3 (Prompt N°12 — Audit + bug fix)

#### Étapes terminées
- [x] **Audit** — Lecture complète `private_impact_runner.py`, `PrivateImpactView.vue`, `MainView.vue`, `ModeSelector.vue`
- [x] **Bug fix** — `roundProgress` corrigé : utilisait `total_rounds` (inexistant) au lieu de `private_total_rounds` → barre de progression toujours à 0%

#### Fichiers modifiés
| Fichier | Action |
|---|---|
| `frontend/src/views/PrivateImpactView.vue` | Bug fix `roundProgress` : fallback sur `progress_percent` (backend) puis `private_total_rounds` |

#### Décisions d'architecture — Session 3
- `roundProgress` prioritise `progress_percent` retourné par `to_dict()` (calculé côté backend) — évite la double-computation
- `ModeSelector.vue` : aucune modification nécessaire — complet et fonctionnel
- `MainView.vue` : redirection private correcte (`await startBuildGraph()` avant `router.push()`) — aucune modification
- RELATIONAL_TYPES frontend (`ouvrier_production`, `technicien`, etc.) : cohérent avec le parseur import — pas de désynchronisation backend (les types backend `employee`/`manager` sont utilisés dans le profil interne, non exposés au frontend)

---

### 2026-04-16 — Session 4 (Prompt N°13 — Audit e2e + corrections bugs bloquants)

#### Bugs identifiés et corrigés

| # | Sévérité | Fichier | Bug | Fix |
|---|---|---|---|---|
| 1 | **BLOQUANT** | `backend/app/__init__.py:71` | `private_bp` enregistré sans `url_prefix` → toutes les routes `/api/private-impact/*` retournent 404 | `register_blueprint(private_bp, url_prefix='/api')` |
| 2 | **BLOQUANT** | `backend/scripts/run_private_simulation.py` | Script lit `event_config.initial_posts` (vide) et `time_config.total_simulation_hours` (absent) → 0 agents exposés, contexte générique, mauvais nombre de rounds | Support dual-format : `decision_statement` + `initial_exposed_agent_ids` + fallback expose-all ; `total_simulation_days`/`rounds_per_day` |
| 3 | **BLOQUANT** | `frontend/src/views/PrivateImpactView.vue` + `frontend/src/api/private.js` | `getReportStatus` fait GET avec `report_id` en query param ; backend attend POST avec `task_id` en body → 405 Method Not Allowed | Ajout `getPrivateReportStatus` (POST task_id) dans `private.js` ; réécriture `runReport`/`pollReport` pour extraire `task_id`, gérer `already_generated` |
| 4 | Cosmétique | `backend/scripts/action_logger.py` + `run_private_simulation.py` | `log_round_end` n'incluait pas `simulated_day` → compteur de jours toujours 0 dans le panneau status | Ajout param optionnel `simulated_day` à `PlatformActionLogger.log_round_end` ; passage du champ depuis les 3 call sites |

#### Fichiers modifiés
| Fichier | Action |
|---|---|
| `backend/app/__init__.py` | Fix : `url_prefix='/api'` ajouté sur `private_bp` |
| `backend/scripts/run_private_simulation.py` | Fix : `get_decision_context` + `get_initial_exposed_agents` dual-format ; `total_rounds` dual-mode ; `simulated_day` dans `log_round_end` |
| `backend/scripts/action_logger.py` | Fix : `log_round_end` accepte param optionnel `simulated_day` |
| `frontend/src/api/private.js` | Fix : ajout `getPrivateReportStatus(taskId)` (POST `/api/report/generate/status`) |
| `frontend/src/views/PrivateImpactView.vue` | Fix : `runReport` extrait `task_id` + gère `already_generated` ; `pollReport` utilise `getPrivateReportStatus` ; import nettoyé (`getReportStatus` supprimé) |

#### Décisions d'architecture — Session 4
- `run_private_simulation.py` : détecte le format de config par présence de `total_simulation_days` (PrivateImpactConfigGenerator) vs `total_simulation_hours` (OASIS) — pas de breaking change
- `get_initial_exposed_agents` : fallback ultime "expose tous les agents" — évite une simulation silencieuse à 0 activité
- `getPrivateReportStatus` dans `private.js` plutôt que modification de `report.js` — préserve le flux Public Opinion existant
- `pollReport` récupère `report_id` final depuis `res.data.result.report_id` (retourné par `task.to_dict()` quand completed)

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
| N°11 | `backend/app/services/private_impact_config_generator.py` | ✅ Terminé — vérifié Prompt N°11 (déjà présent, complet) |
| N°11 | `backend/app/services/private_impact_runner.py` | ✅ Terminé — vérifié Prompt N°11 (déjà présent, complet) |
| N°11 | `backend/app/api/private.py` | ✅ Terminé — vérifié Prompt N°11 (7 routes : prepare, start, status, stop, actions, report, cleanup) |
| N°11 | `backend/app/api/__init__.py` | ✅ Terminé — private_bp défini + import private |
| N°11 | `backend/app/__init__.py` | ✅ Terminé — private_bp enregistré sans url_prefix |
| N°12 | `frontend/src/views/PrivateImpactView.vue` | ✅ Terminé — bug fix `roundProgress` (total_rounds → private_total_rounds + fallback progress_percent) |
| N°12 | `frontend/src/components/ModeSelector.vue` | ✅ Terminé — vérifié, aucune modification nécessaire |
| N°13 | `backend/app/__init__.py` | ✅ Terminé — Bug 1 : `url_prefix='/api'` sur `private_bp` |
| N°13 | `backend/scripts/run_private_simulation.py` | ✅ Terminé — Bug 2 : dual-format event_config + time_config + simulated_day |
| N°13 | `backend/scripts/action_logger.py` | ✅ Terminé — Bug 4 : `simulated_day` dans `log_round_end` |
| N°13 | `frontend/src/api/private.js` | ✅ Terminé — Bug 3 : `getPrivateReportStatus` (POST task_id) |
| N°13 | `frontend/src/views/PrivateImpactView.vue` | ✅ Terminé — Bug 3 : polling report corrigé (task_id, already_generated, import nettoyé) |
| N°14 | `backend/app/services/zep_tools.py` | ✅ Terminé — Bug 5 : matching case-insensitif `get_entities_by_type` |
| N°14 | `backend/app/api/private.py` | ✅ Terminé — Bug 6 : `get_json(silent=True)` sur 3 endpoints |
| N°15 | `frontend/src/views/PrivateImpactView.vue` | ✅ Terminé — Fix 1 : rapport affiche `outline.sections` + fallback `markdown_content`, CSS ajouté |
| N°15 | `backend/scripts/run_private_simulation.py` | ✅ Terminé — Fix 3 : expose tous les agents dès round 1 |
| N°15 | PR | ✅ Terminé — Description PR complète dans CONTEXT.md |
| N°16 | `backend/app/api/private.py` | ✅ Terminé — Bug 7 : `prepare` utilise les types de l'ontologie du projet en priorité sur `_RELATIONAL_ENTITY_TYPES` |
| N°17 | `backend/app/services/zep_entity_reader.py` | ✅ Terminé — Bug 8 : matching case-insensitif dans `filter_defined_entities` ligne 264 |
| N°17 | `backend/app/api/private.py` | ✅ Terminé — Bug 9 : fallback synthétique quand 0 entités Zep + appel Zep optimisé (1 appel global vs N par type) |

---

### 2026-04-16 — Session 5 (Prompt N°14 — Test d'intégration réel)

#### Simulation exécutée
- **Projet** : `proj_00e87b997a03` (seed : scénario PDG + Rolls-Royce DurandTech)
- **Graph ID** : `mirofish_cea02d9a257e44a0`
- **Sim ID** : `private_ff2f2200b746`
- **Agents générés** : 4 (Sophie Martin/manager, Karim Benali/employee, Claire Rousseau/employee, Bertrand Lemaire/client)
- **Rounds** : 90 (`total_simulation_days: 30 × rounds_per_day: 3` — valeur générée par LLM, override de la config envoyée)
- **Actions** : 31 (COALITION_BUILD: 19, CONFRONT: 12)
- **Agent actif** : Sophie Martin uniquement (`initial_exposed_agent_ids: [0]` généré par le LLM — les 3 autres font DO_NOTHING)
- **Rapport** : généré (`report_2e3e9e073cc3`), `markdown_content` cohérent avec le scénario

#### Observations du flux complet

| Étape | Résultat | Notes |
|---|---|---|
| Ontologie | ✅ OK | Types : Ceo, Manager, Employee, Client, Company |
| Graph build | ✅ OK | `mirofish_cea02d9a257e44a0` en ~40s |
| Prepare | ✅ OK (après fix Bug 5) | 4 agents, statut `prepared` |
| Start | ✅ OK | `runner_status: running` |
| Status polling | ✅ OK | Champs : `runner_status`, `progress_percent`, `private_current_round`, `private_total_rounds`, `private_simulated_days`, `private_actions_count` |
| Actions | ✅ Verbes relationnels | COALITION_BUILD + CONFRONT — aucun verbe Twitter/Reddit |
| Rapport | ✅ OK | `markdown_content` en ~3min, contenu pertinent et ancré dans le scénario |
| Cleanup | ✅ OK | `cleaned_files: ["run_state.json"]` |

#### Bugs identifiés et corrigés — Session 5

| # | Sévérité | Fichier | Bug | Fix |
|---|---|---|---|---|
| 5 | **BLOQUANT** | `backend/app/services/zep_tools.py:802` | `get_entities_by_type` compare en case-sensitive → `"manager"` ne match pas `"Manager"` dans les labels Zep → "No relational entities found" | `any(lbl.lower() == entity_type.lower() for lbl in node.labels)` |
| 6 | Mineur | `backend/app/api/private.py:95,243,417` | `request.get_json() or {}` lève 400 si body vide avec `Content-Type: application/json` | `request.get_json(silent=True) or {}` sur les 3 endpoints |

#### Observations non-bloquantes

| # | Description |
|---|---|
| A | `round=None` dans `/actions` et `recent_actions` de `/status` — JSONL contient le champ, mais `_read_action_log` ne le remonte pas |
| B | `PrivateImpactConfigGenerator` override la config event envoyée dans `/prepare` — `initial_exposed_agent_ids` et `total_simulation_days` sont régénérés par le LLM |
| C | `report.content` est vide dans la réponse `/api/report/<id>` — le contenu est dans `markdown_content` (non dans `content`) — frontend doit lire le bon champ |
| D | Un seul agent actif sur 4 : comportement attendu si `initial_exposed_agent_ids: [0]` (distance 1 = Sophie uniquement) — les agents 1-3 ne reçoivent pas le contexte de décision |

#### Fichiers modifiés — Session 5
| Fichier | Action |
|---|---|
| `backend/app/services/zep_tools.py` | Bug 5 : matching case-insensitif dans `get_entities_by_type` |
| `backend/app/api/private.py` | Bug 6 : `get_json(silent=True)` sur 3 endpoints (prepare, start, report) |

---

### 2026-04-16 — Session 6 (Prompt N°15 — Corrections finales + PR)

#### Corrections appliquées

| # | Fichier | Correction |
|---|---|---|
| Fix 1 | `frontend/src/views/PrivateImpactView.vue` | Rapport : remplace `reportResult.title/.summary/.sections` (inexistants) par `reportResult.outline?.sections` + fallback `<pre class="report-markdown">{{ reportResult.markdown_content }}</pre>` |
| Fix 2 | *(non nécessaire)* | `round=None` dans mes scripts de test était une erreur de clé (`round` vs `round_num`) — `to_dict()` et le template utilisent bien `round_num` |
| Fix 3 | `backend/scripts/run_private_simulation.py` | `get_initial_exposed_agents` simplifié : expose TOUS les agents dès le round 1 — le LLM ne filtre plus via `initial_exposed_agent_ids` (paramètre structurel, pas LLM) |
| Fix 4 | `backend/app/api/private.py` | Vérifié : 3/3 endpoints déjà en `get_json(silent=True)` depuis N°14 |

#### Fichiers modifiés — Session 6
| Fichier | Action |
|---|---|
| `frontend/src/views/PrivateImpactView.vue` | Fix 1 : affichage rapport corrigé (`outline.sections` + fallback `markdown_content`), CSS `.report-markdown` ajouté, `.report-title`/`.report-summary` supprimés |
| `backend/scripts/run_private_simulation.py` | Fix 3 : `get_initial_exposed_agents` expose tous les agents — suppression du filtre LLM |

---

### 2026-04-16 — Session 7 (Prompt N°16 — Bug 7 : entity types domaine-spécifiques)

#### Diagnostic
- `/api/private-impact/prepare` → 404 (en fait 400) sur le projet `fromagerie-auriac`
- Diagnostic : les routes sont correctement enregistrées (`flask routes` confirme `/api/private-impact/prepare POST`)
- Cause réelle : l'ontologie LLM génère des types domaine-spécifiques (`ProductionWorker`, `CheeseTechnician`, `FoodRetailer`, `FamilyMember`, etc.) — aucun ne matche `_RELATIONAL_ENTITY_TYPES` (même avec fix case-insensitif du Bug 5)

#### Bug corrigé

| # | Sévérité | Fichier | Bug | Fix |
|---|---|---|---|---|
| 7 | **BLOQUANT** | `backend/app/api/private.py:136` | `entity_types` hardcodé (`employee`, `manager`, etc.) — l'ontologie LLM génère des types domaine-spécifiques jamais en liste → 0 entités, "No relational entities found" | Résolution en 3 niveaux : 1) `entity_types` explicite dans la requête 2) types de l'ontologie du projet (avec filtre `_is_structural_type`) 3) `_RELATIONAL_ENTITY_TYPES` en dernier recours |

#### Résultat
- `proj_b420d07dfb38` (Fromagerie Auriac, 3 fichiers seed) : **27 agents générés**, statut `prepared` ✅
- Types utilisés : `ProductionWorker`, `CheeseTechnician`, `SalesRepresentative`, `ExecutiveTeam`, `FoodRetailer`, `FamilyMember`

#### Fichiers modifiés — Session 7
| Fichier | Action |
|---|---|
| `backend/app/api/private.py` | Bug 7 : `_is_structural_type()` + résolution entity types en 3 niveaux (request → ontologie projet → défaut) |

---

### 2026-04-16 — Session 8 (Prompt N°17 — Bugs 8 & 9 : 0 entités Zep → fallback synthétique)

#### Diagnostic
- `筛选完成: 总节点 14, 符合条件 0, entité_types: set()` — graphe `mirofish_80371e75ec2844b3` a 14 nœuds mais 0 match
- Cause 1 : `filter_defined_entities` ligne 264 fait `l in defined_entity_types` (case-sensitive) — les labels Zep peuvent différer en casse
- Cause 2 : même avec case-insensitif, les 14 nœuds ont uniquement les labels `["Entity", "Node"]` (pas de labels typés) → 0 entités retournées
- Le fallback Bug 7 ne s'activait pas car le 404 était retourné par le code précédent avant le fallback synthétique
- Cause 3 : la boucle `for etype in entity_types: reader.get_entities_by_type(...)` faisait N appels Zep (N = nombre de types) — chacun lit tous les nœuds + toutes les arêtes

#### Bugs corrigés

| # | Sévérité | Fichier | Bug | Fix |
|---|---|---|---|---|
| 8 | **MINEUR** | `backend/app/services/zep_entity_reader.py:264` | `l in defined_entity_types` case-sensitive → labels Zep `ProductionWorker` vs type `productionworker` ne matchent pas | `defined_lower = {t.lower() for t in defined_entity_types}; matching_labels = [l for l in custom_labels if l.lower() in defined_lower]` |
| 9 | **BLOQUANT** | `backend/app/api/private.py:180` | Quand 0 entités matchent, retourne 404 immédiatement sans alternative | Remplacé par : `_build_synthetic_entities()` — crée des `EntityNode` synthétiques par type d'ontologie (LLM enrichit les profils sans ancrage Zep) ; ajout helper `_build_synthetic_entities()` ; appel Zep optimisé (`filter_defined_entities` 1 fois pour tous les types au lieu de N appels) |

#### Résultat
- Test unitaire Python confirmé : 7 agents synthétiques créés pour `proj_d86ee68acfa3` (types : `ProductionWorker`, `CheeseMaster`, `SalesRepresentative`, `ExecutiveTeam`, `RetailClient`, `FamilyMember`, `UnionRepresentative`)
- `EntityNode` import ajouté dans `private.py`
- La génération HTTP complète prend plusieurs minutes (3 LLM call groups dans `PrivateImpactConfigGenerator.generate_config()` — comportement attendu)

#### Fichiers modifiés — Session 8
| Fichier | Action |
|---|---|
| `backend/app/services/zep_entity_reader.py` | Bug 8 : case-insensitive dans `filter_defined_entities` |
| `backend/app/api/private.py` | Bug 9 : `_build_synthetic_entities()` helper + fallback + import `EntityNode` + appel Zep optimisé (1 appel) |

---

## Pull Request — feat: Private Impact simulation mode

### Titre
`feat: Private Impact simulation mode`

### Description

Ce PR ajoute un second mode de simulation à MiroFish : **Private Impact**.

Contrairement au mode Opinion Publique (Twitter/Reddit), Private Impact simule l'impact d'une **décision privée** (ex. achat d'un bien de luxe, licenciement, choix stratégique) dans un **réseau relationnel fermé** : employés, managers, clients, partenaires, famille.

#### Ce que ça fait
- **Pipeline complet** : Prepare → Start → Status polling → Actions → Rapport → Cleanup
- **Agents relationnels** : profils enrichis avec `relational_link_type`, `trust_level`, `seniority_years`, encodés dans le persona LLM
- **Verbes relationnels** : `REACT_PRIVATELY`, `CONFRONT`, `COALITION_BUILD`, `SILENT_LEAVE`, `VOCAL_SUPPORT`, `DO_NOTHING` (≠ verbes Twitter/Reddit)
- **Rapport** : réutilise `ReportAgent` avec `markdown_content` structuré
- **Frontend** : wizard 5 étapes, graphe D3 force-directed temps réel, import config `#CONFIG…#END_CONFIG`

#### Comment tester
1. `git checkout feature/private-impact`
2. `npm run setup:all && npm run dev`
3. Sur l'interface Home → sélectionner mode "Private Impact"
4. Créer un projet avec un fichier seed décrivant un décideur + son réseau (voir `/tmp/mirofish_private_test_seed.txt` comme exemple)
5. Attendre la génération de l'ontologie + du graphe
6. Accéder à `/private/:projectId` → remplir le formulaire → Prepare → Start
7. Observer le graphe D3 et le feed d'actions en temps réel
8. Générer le rapport → vérifier `markdown_content`

#### Fichiers créés
| Fichier | Description |
|---|---|
| `backend/scripts/run_private_simulation.py` | Moteur subprocess — 6 verbes relationnels, LLM direct via camel-ai |
| `backend/app/services/private_impact_profile_generator.py` | Générateur de profils relationnels (8 dimensions) |
| `backend/app/services/private_impact_config_generator.py` | Générateur de paramètres comportementaux via LLM |
| `backend/app/services/private_impact_runner.py` | Orchestrateur : subprocess + monitoring + état en mémoire |
| `backend/app/api/private.py` | Blueprint Flask — 7 routes `/api/private-impact/*` |
| `frontend/src/api/private.js` | Client API Private Impact (7 fonctions) |
| `frontend/src/components/ModeSelector.vue` | Sélecteur Public / Private Impact |
| `frontend/src/views/PrivateImpactView.vue` | Wizard 5 étapes + graphe D3 |

#### Fichiers modifiés
| Fichier | Modification |
|---|---|
| `backend/app/__init__.py` | Enregistrement `private_bp` avec `url_prefix='/api'` |
| `backend/app/api/__init__.py` | Import + export `private_bp` |
| `backend/app/services/simulation_runner.py` | 7 zones private (champs, start, monitor, log, check, actions, cleanup) |
| `backend/app/services/zep_tools.py` | `get_entities_by_type` — matching case-insensitif |
| `backend/scripts/action_logger.py` | `get_private_logger()` + `simulated_day` dans `log_round_end` |
| `frontend/src/router/index.js` | Route `/private/:projectId` |
| `frontend/src/views/Home.vue` | Intégration `ModeSelector` |
| `frontend/src/views/MainView.vue` | `await startBuildGraph()` avant redirect private |

#### Bugs connus résiduels (non bloquants)
- `PrivateImpactConfigGenerator` peut générer un `total_simulation_days` différent de celui envoyé dans la requête (comportement LLM — override délibéré du générateur)
- Le rapport affiché dans l'accordéon utilise `outline.sections` sans titres de sections — les sections s'affichent "Section 01, 02…" si pas de titre ; le contenu complet est toujours accessible via le fallback `markdown_content`

#### Checklist
- [x] Test d'intégration end-to-end réalisé (scénario PDG + Rolls-Royce, 4 agents, 90 rounds, 31 actions)
- [x] Verbes relationnels vérifiés (COALITION_BUILD, CONFRONT — aucune fuite Twitter/Reddit)
- [x] Rapport généré et lisible (`markdown_content` non vide, contenu pertinent)
- [x] Cleanup propre (`run_state.json` supprimé)
- [x] 6 bugs bloquants corrigés (url_prefix, config mismatch, report polling, simulated_day, case-sensitive, silent json)
- [x] CONTEXT.md à jour

---

## Point d'attention — `MainView.vue` (N°11)
**Status : ✅ RÉSOLU (Prompt N°10 Session 2)**

Bug : redirection vers `/private/:projectId` se faisait après l'ontologie, avant `startBuildGraph()`.
Fix : `await startBuildGraph()` ajouté avant `router.push()` dans le bloc `pendingMode === 'private'`.
Robustesse : `PrivateImpactView` polle `getProject()` jusqu'à ce que `graph_id` soit disponible.

---

### 2026-04-17 — Session 3

#### Prompt N°18 — Correction de 5 bugs + 1 fragilité

##### Bugs corrigés
| # | Bug | Correctif | Fichier(s) |
|---|---|---|---|
| 1 | Rapport section 01 en chinois | Règle de langue centralisée dans `get_language_instruction()` : override forçant l'alignement sur `simulation_requirement`, fallback français | `backend/app/utils/locale.py` |
| 2 | Graphe D3 sans arêtes | Endpoint `/status` augmenté avec `agents` + `relational_edges` issus de `cascade_influence`. Frontend : nœuds statiques + merge arêtes cascade (grises pointillées si pas d'action, pleines si activées) | `backend/app/api/private.py`, `frontend/src/views/PrivateImpactView.vue` |
| 3 | Bouton export rapport absent | Bouton `Export .md` ajouté dans Step 4 ; sérialisation `outline.sections` → markdown via Blob + download | `frontend/src/views/PrivateImpactView.vue` |
| 5 | Mode Public/Private via sessionStorage | Remplacé par query param `?mode=private` sur `/process/:projectId` ; MainView lit `route.query.mode` | `frontend/src/views/Home.vue`, `frontend/src/views/MainView.vue` |

##### Bug partiellement corrigé
| # | Bug | État | Raison |
|---|---|---|---|
| 4 | Chat agents 400 | **Corrigé côté frontend seulement** (body aligné sur `interviews: [{agent_id, prompt}]` + parsing réponse `result.results`) | La route chat pour Private Impact n'existe pas dans `private.py`. Le frontend tape `/api/simulation/interview/batch` qui exige `SimulationRunner.check_env_alive()` — incompatible avec `PrivateImpactRunner`. Le 400 "require interviews" est corrigé, mais `env not running` reste à traiter par une nouvelle route dédiée côté backend (hors périmètre : pas de nouveaux fichiers autorisés) |

##### Fichiers modifiés
- `backend/app/utils/locale.py` — directive de langue universelle
- `backend/app/api/private.py` — status endpoint renvoie `agents` + `relational_edges`
- `frontend/src/views/PrivateImpactView.vue` — graphe cascade, export .md, chat body corrigé
- `frontend/src/views/Home.vue` — suppression sessionStorage, passage query param
- `frontend/src/views/MainView.vue` — lecture `route.query.mode`
- `CONTEXT.md` — mise à jour

##### Prochaine étape
- **PR** vers `main` : `feature/private-impact` — regrouper cette session avec les sessions 1–2.
- **À anticiper post-PR** : créer une route `/api/private-impact/chat/<sim_id>` dédiée pour finaliser le bug 4 (le runner privé n'a pas d'IPC de type `send_batch_interview`, donc un chat direct via `ReportAgent.chat` ou un LLM call sur le profil d'agent est sans doute plus pertinent).

---

### 2026-04-17 — Session 4 (Prompt N°23 — Éclatement PrivateImpactView en 4 sous-composants)

#### Objectif
Refactoring iso-comportement de `PrivateImpactView.vue` (monolithe 2091 lignes) en orchestrateur + 4 sous-composants autonomes, pour préparer l'intégration future dans `MainView` (wizard partagé Public/Private, Prompt N°24).

#### Fichiers créés
| Fichier | Rôle |
|---|---|
| `frontend/src/constants/private.js` | Constantes extraites : `RELATIONAL_TYPES`, `RELATIONAL_TYPE_LABELS`, `HORIZON_OPTIONS`, `ACTION_COLORS`, `STEP_NAMES` |
| `frontend/src/utils/private.js` | Helpers purs : `shortTime`, `actionTypeClass`, `initials`, `nodeColor`, `buildRequirement`, `parseImportedConfig`, `exportReportMarkdown` |
| `frontend/src/components/private/Step2PrivateDecision.vue` | Formulaire décision + import .txt + bouton Prepare (émet `@prepare`) |
| `frontend/src/components/private/Step3PrivateSim.vue` | Graphe D3 force-directed + live feed + contrôles start/stop (émet `@stop`, `@report`) |
| `frontend/src/components/private/Step4PrivateReport.vue` | Affichage rapport + export markdown (émet `@retry`, `@next`) |
| `frontend/src/components/private/Step5PrivateInteraction.vue` | Liste agents + chat local (props `simId` + `chatAgents`) |

#### Fichier modifié
- `frontend/src/views/PrivateImpactView.vue` — réduit à l'orchestrateur : header, steps-bar, error banner, état global (`currentStep`, `simId`, `simStatus`, `prepareResult`, `reportResult`, `form`, `agentCounts`, `recentActions`, `chatAgents`, timers), méthodes async (`runPrepare`, `runStart`, `runReport`, `handleStop`, polling status/report, `waitForGraph`, `loadChatAgents`, `goToStep`), Step 2 (Prepare Results) conservé inline.

#### Décisions d'architecture — Session 4
- `form` et `agentCounts` restent des `reactive` dans le parent et sont passés en props aux enfants — les mutations (v-model) se propagent naturellement grâce à la réactivité Vue 3.
- Le watcher `form.relationalTypes` → `agentCounts` vit dans `Step2PrivateDecision` (avec `deep: true` pour capter les mutations d'array).
- Le cycle de vie D3 (`initGraph`, `updateGraph`, `simulation.stop()`) vit dans `Step3PrivateSim` via `onMounted` / `onUnmounted` — plus besoin du watcher `currentStep === 3` dans le parent.
- Les styles communs (`.btn-primary`, `.btn-secondary`, `.mono`, `.loading-ring`) sont dupliqués dans chaque composant `scoped` pour rester autonomes ; le parent conserve uniquement les styles réellement utilisés par son template (header, steps-bar, error banner, centered-panel, prepare-results).
- Le chargement initial de `chatAgents` reste dans le parent (`loadChatAgents` déclenché par le watcher `currentStep === 5`) — `Step5PrivateInteraction` reçoit la liste en prop et n'appelle jamais `getPrivateActions`.
- Step 2 (Prepare Results, ~60 lignes) reste inline dans l'orchestrateur — trop couplé à l'état parent pour justifier un 5ème composant.

#### Prochaine étape
- **Prompt N°24** — Refactor `MainView.vue` avec bifurcation `mode=public` / `mode=private` après le graph build (wizard partagé qui ré-utilise les 4 sous-composants privés + leurs équivalents publics).

---

### 2026-04-17 — Session 5 (Prompt N°24 — Bifurcation MainView par `route.query.mode`)

#### Objectif
Fusionner les deux wizards (Public / Private) dans un unique `MainView.vue` qui bifurque selon `route.query.mode` après l'étape 1 (graph build). `PrivateImpactView.vue` devient un simple passthrough de redirection vers `/process/:projectId?mode=private`.

#### Fichiers modifiés
| Fichier | Modification |
|---|---|
| `frontend/src/components/Step1GraphBuild.vue` | Ajout prop `mode: { type: String, default: 'public' }`. Si `mode === 'private'`, `handleEnterEnvSetup` émet `next-step` sans créer de simulation OASIS (pas de `createSimulation` ni de `router.push('/simulation/...')`). Le comportement public reste **strictement inchangé**. |
| `frontend/src/views/MainView.vue` | Refactor complet : `isPrivateMode` computed (`route.query.mode === 'private'`), ajout de tout l'état Private (`privateForm`, `privateAgentCounts`, `privateSimId`, `privateSimStatus`, `privatePrepareResult`, `privatePrepareReady`, `privateReportResult`, `privateIsLoading`, `privateError`, `privateReportProgress`, `privateRecentActions`, `privateChatAgents`, timers `privatePollingTimer` + `privateReportPollingTimer`). Méthodes Private migrées depuis PrivateImpactView : `runPrivatePrepare`, `runPrivateStart`, `pollPrivateStatus`, `handlePrivateStop`, `runPrivateReport`, `pollPrivateReport`, `loadPrivateChatAgents`. Template bifurqué : Step 1 commun (split layout, mode prop), Steps 2–5 branchés selon le mode. `onBeforeRouteLeave`, `onBeforeRouteUpdate`, `onUnmounted` cleanupent **tous** les timers (publics + privés). `watch(isPrivateMode)` reset `currentStep = 1` et `privatePrepareReady = false`. `handleNewProject` propage désormais `query: { mode }` dans `router.replace({ name: 'Process', ... })` au lieu de rediriger vers `/private/:projectId`. |
| `frontend/src/views/PrivateImpactView.vue` | Réduit à un composant de redirection : `onMounted` → `router.replace({ name: 'Process', params: { projectId }, query: { mode: 'private' } })`. |
| `frontend/src/components/ModeSelector.vue` | Suppression du `router.push({ name: 'PrivateImpact' })` (le routing est désormais déclenché par `Home.vue` via `selectedMode.value === 'private' ? { mode: 'private' } : {}`). |

#### Décisions d'architecture — Session 5
- **Step 1 inchangé pour le public** : ajout d'un prop `mode` avec default `'public'`. Le public branche exécute exactement l'ancien code (createSimulation + router.push vers `/simulation/:id`). Seule la branche `private` est nouvelle (émet `next-step`).
- **Étiquettes des étapes différentes par mode** :
  - Public : `stepNames` venant de `tm('main.stepNames')` (i18n)
  - Private : `['Graph Build', 'Requirement', 'Run', 'Report', 'Interact']`
- **Étape 2 privée (Requirement + Prepare)** : `privatePrepareReady` est un flag local dans MainView qui permet d'afficher le formulaire (`false`) ou le résultat `preparePrivateSimulation` (`true`). Le bouton « Back » remet le flag à `false` (retour au formulaire avec données conservées).
- **Steps bar Private** : affichée uniquement à partir de `currentStep >= 2` (étape 1 = graph build commun, avec son propre UI). Le breadcrumb couvre les étapes 2→5 (`['Requirement', 'Run', 'Report', 'Interact']`).
- **Cleanup timers** : un seul point de vérité `cleanupAllTimers()` appelé dans `onBeforeRouteLeave`, `onBeforeRouteUpdate` (si `projectId` change) et `onUnmounted`. `watch(isPrivateMode)` appelle uniquement `cleanupPrivateTimers()` (le changement de mode seul ne doit pas tuer les timers publics).
- **`currentStep` jamais persisté** : reset automatique à 1 dès que `isPrivateMode` change. Pas de localStorage / sessionStorage.
- **`PrivateImpactView.vue`** : maintenu comme simple redirecteur pour préserver la compatibilité des URLs `/private` et `/private/:projectId` (ModeSelector legacy, liens externes éventuels). À supprimer dans un prompt futur si plus utilisé.

#### Validation
- `npx vite build` → succès (704 modules, 1.96s, seuls les warnings préexistants persistent : chunk > 500 kB et dynamic import de `pendingUpload.js`).
- Flow public : `Home → /process/new → Step1GraphBuild (mode=public) → createSimulation → /simulation/:id` — **inchangé**.
- Flow private : `Home (mode=private) → /process/new?mode=private → Step1GraphBuild (mode=private) → emit next-step → Step 2 privée (form Prepare) → Step 3 Sim → Step 4 Report → Step 5 Chat`.
- Compatibilité : `/private/:projectId` → redirige vers `/process/:projectId?mode=private`.

#### Prochaine étape
- PR `feature/private-impact` → `main` (regroupe Sessions 1 à 5).
- Cleanup optionnel : supprimer complètement les routes `/private` et `/private/:projectId` si PR marchée en production (et que les liens externes sont migrés).

---

### 2026-04-17 — Session 6 (Prompt N°25 — ModeSelector via query param + suppression routes /private)

#### Objectif
Finaliser l'intégration du mode selector : plus aucun état de mode hors URL, suppression définitive des routes legacy `/private` / `/private/:projectId` et du fichier passthrough `PrivateImpactView.vue`.

#### Fichiers modifiés
| Fichier | Modification |
|---|---|
| `frontend/src/components/ModeSelector.vue` | Refactor complet. Nouveaux props : `projectId: { type: String, default: 'new' }` et `disabled: { type: Boolean, default: false }`. `selectMode(mode)` appelle `emit('mode-selected', mode)` (synchrone — permet au parent de stocker la pending upload avant la navigation) puis `router.push({ path: '/process/${projectId}', query: { mode } })`. Cards ont désormais `:disabled` natif + classe `.is-disabled` (opacity 0.45, cursor not-allowed). |
| `frontend/src/views/Home.vue` | Suppression du bouton `start-engine-btn` (ModeSelector devient la CTA). Suppression de `selectedMode` ref, de `startSimulation()`, de `useRouter` import, de `error` ref non utilisé, du `mode-selector-wrapper` (déplacé dans console-box). ModeSelector est maintenant dans une `.console-section.mode-selector-section` après la textarea avec `:projectId="'new'"` + `:disabled="!canSubmit || loading"`. `handleModeSelected()` appelle `setPendingUpload(files, simulationRequirement)` de manière synchrone — l'emit Vue 3 s'exécute avant le `router.push` qui suit dans ModeSelector. Import de `setPendingUpload` passé de dynamic à statique. CSS obsolètes supprimées (`.start-engine-btn*`, `@keyframes pulse-border`, `.mode-selector-wrapper`, `.btn-section`). |
| `frontend/src/router/index.js` | Suppression de l'import `PrivateImpactView` et des deux entrées de route `/private` (`PrivateImpact`) et `/private/:projectId` (`PrivateImpactWithProject`). Une URL legacy `/private/...` donne désormais une 404 du router (comportement Vue Router par défaut). |

#### Fichier supprimé
- `frontend/src/views/PrivateImpactView.vue` — le passthrough de redirection Session 5 devient obsolète une fois le ModeSelector reconnecté et les routes legacy retirées.

#### Décisions d'architecture — Session 6
- **Mode dans l'URL uniquement** : aucun `sessionStorage`, aucun `localStorage`, aucune `ref` Home persistée. La query param `?mode=public|private` est la source de vérité.
- **Timing de `setPendingUpload`** : le parent (`Home.vue`) écoute `mode-selected`. L'emit Vue est synchrone et se déclenche AVANT le `router.push` dans le même `selectMode`. Le handler `handleModeSelected` s'exécute donc avant la navigation, garantissant que `getPendingUpload()` côté `MainView.handleNewProject` trouve bien les fichiers.
- **UX ModeSelector** : cards désactivées tant que `canSubmit === false` (pas de fichiers OU pas de prompt de simulation). Opacity réduite + cursor not-allowed pour indiquer l'état.
- **404 sur `/private*`** : choix délibéré pour nettoyer l'API publique du frontend. Aucun lien externe documenté dans le repo ne pointe vers ces URLs (confirmé par `grep -rn "/private"` restreint aux URLs frontend : 0 occurrence hors `api/private.js` backend et imports locaux `*/private/*` côté fichiers). Si un lien externe casse, la route pourra être rétablie en alias explicite dans une future PR.
- **Bouton « Start Engine » supprimé** : redondant avec ModeSelector une fois que celui-ci navigue directement. Deux CTAs pour la même action = ambiguïté UX. L'animation `pulse-border` disparaît avec le bouton.

#### Résultats des greps — AVANT (état pré-modification)
```
grep -rn "/private" frontend/src --include="*.vue" --include="*.js"
→ router/index.js:47 path: '/private'
→ router/index.js:53 path: '/private/:projectId'
→ api/private.js (7 lignes : endpoints backend /api/private-impact/... — À CONSERVER)
→ components/private/*.vue, utils/private.js, constants/private.js (imports fichiers locaux — À CONSERVER)

grep -rn "PrivateImpactView" frontend/src
→ router/index.js:8 import PrivateImpactView
→ router/index.js:49 component: PrivateImpactView
→ router/index.js:55 component: PrivateImpactView

grep -rn "privateImpact" frontend/src → 0 match
grep -rn "sessionStorage" frontend/src/components/ModeSelector.vue frontend/src/views/Home.vue → 0 match
```

#### Résultats des greps — APRÈS (état post-modification)
```
grep -rn "/private" frontend/src --include="*.vue" --include="*.js"
→ api/private.js (7 lignes : endpoints backend — LÉGITIMES)
→ MainView.vue + components/private/*.vue + utils/private.js + constants/private.js (imports locaux — LÉGITIMES)
→ AUCUNE URL frontend `/private/...` restante ✓

grep -rn "PrivateImpactView" frontend/src → 0 match ✓
grep -rn "privateImpact" frontend/src → 0 match ✓
grep -rn "sessionStorage" frontend/src → 0 match (recherche étendue au projet entier) ✓
```

#### Validation
- `npx vite build` → succès (701 modules, 1.13s). Warning dynamic import de `pendingUpload.js` disparu (import statique dans Home.vue).
- Scénario 1 : Home → upload + prompt → ModeSelector actif → clic « Public Opinion » → URL = `/process/new?mode=public` → `handleNewProject` lit pendingUpload → wizard public.
- Scénario 2 : Home → upload + prompt → clic « Private Impact » → URL = `/process/new?mode=private` → wizard privé.
- Scénario 3 : URL directe legacy `/private/:projectId` → 404 router (plus de route).
- Scénario 4 : F5 sur `/process/:projectId?mode=private` → query param préservé, même flux.
- Scénario 5 : back navigateur depuis wizard → retour à Home, ModeSelector en état `selected.value = null` (ref locale au composant, reset au remount).
- Scénario 6 : switch manuel d'URL `?mode=public` → `?mode=private` sur même projectId → `watch(isPrivateMode)` reset `currentStep = 1` + cleanup timers privés (Session 5).

#### Prochaine étape
- **Prompt N°26** — Tests bout-en-bout les deux flux (upload → graph build → steps privés/publics → rapport → chat) + corrections de régressions éventuelles (UX cards désactivées, feedback visuel de chargement pendant `generateOntology`, cleanup pendingUpload après succès).

---

### Session 7 — Prompt N°27 — i18n Private + header polishing (2026-04-17)

#### Objectif
Migrer les `stepNames` et `modeBadge` Private hors des hardcodes vers les fichiers i18n. Unifier la mécanique du compteur `Step X/Y` via `stepNames.length` (déjà en place depuis N°24). Ne pas toucher au flux Public fonctionnel.

#### Audit i18n — état AVANT modifications
Langues supportées (fichiers présents dans `locales/`) : **EN** (`en.json`), **ZH** (`zh.json`). Pas de `fr.json` malgré la présence de `fr` dans `locales/languages.json` (langue référencée mais sans pack). Langue par défaut : `zh`.

Clés existantes pertinentes pour le header / wizard Public :
- `main.stepNames` (array 5 entrées) — utilisé par `MainView.vue:288`, `SimulationView.vue:28`, `SimulationRunView.vue:28`, `ReportView.vue:28`, `InteractionView.vue:28`
- `main.layoutGraph|layoutSplit|layoutWorkbench` — utilisé par les 5 vues ci-dessus
- `common.ready|running|completed|failed|processing|error` — présents mais `statusText` dans `MainView.vue` reste hardcodé EN (hors périmètre de ce prompt — aucune divergence cross-mode)
- Aucune clé Private préexistante (tout était hardcodé dans le JS `MainView.vue`).

#### Fichiers modifiés
| Fichier | Modification |
|---|---|
| `locales/en.json` | Ajout section `public` (`stepNames` copie de `main.stepNames` + `modeBadge: "PUBLIC OPINION"`) et section `private` (`stepNames: ["Requirement", "Prepare", "Run", "Report", "Interact"]` + `modeBadge: "PRIVATE IMPACT"`). `main.stepNames` conservé — utilisé par 4 autres vues (SimulationView, SimulationRunView, ReportView, InteractionView) hors scope. |
| `locales/zh.json` | Idem, symétrique. Private ZH : `["需求", "准备", "运行", "报告", "互动"]`. Badge ZH : `"私域影响"` (Private) / `"公共舆论"` (Public). |
| `frontend/src/views/MainView.vue` | Template : `PRIVATE IMPACT` → `{{ t('private.modeBadge') }}`. Script : `publicStepNames` lit désormais `tm('public.stepNames')` (aligné sur la nouvelle clé). `privateStepNames` passe d'array statique à `computed(() => tm('private.stepNames'))`. `privateBreadcrumb` passe d'array statique à `computed(() => privateStepNames.value.slice(1))` — dérivé, toujours synchronisé. `currentStepNames` adapté pour `.value` sur la computed privée. Compteur `Step {{ currentStep }}/{{ currentStepNames.length }}` déjà robuste (N°24) — pas de modification. |

#### Clés i18n ajoutées
- `public.stepNames` (EN, ZH) — mirror de `main.stepNames`
- `public.modeBadge` (EN, ZH) — pour usage futur si badge Public affiché (non rendu actuellement dans le template puisque `<div v-if="isPrivateMode" class="mode-badge">`)
- `private.stepNames` (EN, ZH)
- `private.modeBadge` (EN, ZH)

#### Décisions — Session 7
- **Coexistence `main.stepNames` ↔ `public.stepNames`** : les deux clés contiennent actuellement la même liste. `main.stepNames` reste la source de vérité pour les 4 vues sub-étape (SimulationView, SimulationRunView, ReportView, InteractionView) qui lisent `$tm('main.stepNames')[N]`. `public.stepNames` est lu uniquement par MainView pour la symétrie avec `private.stepNames`. Migration complète vers `public.stepNames` hors périmètre de ce prompt (toucherait 4 vues non mentionnées).
- **Écart spec vs UI** : le prompt liste `['Requirement', 'Prepare', 'Run', 'Report', 'Interact']` mais Step 1 dans la UI est le composant `Step1GraphBuild` commun aux deux modes. La valeur « Requirement » pour Step 1 Private est donc sémantiquement le **cadrage** (l'utilisateur fournit les docs requirement qui alimentent la construction du graphe), pas la construction graph elle-même. Choix : suivre le prompt littéralement — le label affiché dans le header pour Step 1 en mode Private est « Requirement » (ZH : 需求). Le composant sous-jacent ne change pas.
- **Badge Public non affiché** : `public.modeBadge` est ajoutée pour cohérence API i18n (symétrie avec `private.modeBadge`) mais le template `<div v-if="isPrivateMode" class="mode-badge">` n'affiche pas de badge en mode Public. Comportement inchangé vs avant N°27. Activation future = retrait du `v-if`.
- **Pas de migration `statusText`** : les labels `Ready|Running|Completed|Failed|Error|Processing|Building Graph|Generating Ontology|Initializing` restent hardcodés EN dans `MainView.vue:368-385`. Ils sont identiques pour les deux modes (non-divergents). Per prompt section 5 : « Si aucune divergence supplémentaire trouvée au-delà de stepNames et modeBadge, c'est OK ». Migration i18n complète du `statusText` = hors périmètre (un prompt futur pourra le traiter).

#### Validation
- `npx vite build` → succès (701 modules, 1.13s, aucun warning nouveau).
- Lecture code : `currentStepNames.length === 5` dans les deux modes (header `Step X/5` cohérent).
- Lecture template : `privateBreadcrumb` (computed) = 4 entrées (`stepNames.slice(1)`), affiché uniquement pour steps 2→5 via `v-if="currentStep >= 2"`. Numérotation `{{ idx + 1 }}` = 1→4 (N°24, cohérent).
- Changement de langue via `LanguageSwitcher` : `tm('private.stepNames')` et `t('private.modeBadge')` sont réactifs via vue-i18n → bascule EN/ZH immédiate sans perte d'état (watch interne vue-i18n).
- Changement de mode (URL `?mode=public` ↔ `?mode=private`) : la langue active ne bouge pas (stockée dans `localStorage` par `i18n/index.js`, indépendante de la query param).

#### Non-régressions constatées
- Aucune modification dans les 4 vues qui lisent `main.stepNames[N]` (SimulationView, SimulationRunView, ReportView, InteractionView) — leur header conserve son label EN/ZH existant.
- Public flow : `publicStepNames` renvoie `tm('public.stepNames')` dont le contenu est identique à `main.stepNames` → aucun changement visuel.

#### Prochaine étape
- **Prompt N°28** — Commit feature/private-impact + push + mise à jour PR #544.

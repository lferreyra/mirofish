# Architecture — MiroFish SIPE

## High-Level System Design

MiroFish SIPE is a foresight workbench that transforms policy/domain documents into running social simulations and generates analytical reports. The system follows a strict 5-step pipeline:

```
Document Upload → Ontology Generation → Knowledge Graph Build
    → Simulation Preparation → Simulation Run → Report Generation
```

### Deployment Topology

```
Browser (Vue 3 SPA)
    ↕ REST/HTTP
Flask Backend (Python 3.11, Waitress in prod)
    ├── KuzuDB (embedded graph DB, persistent on disk)
    ├── File-based stores (projects, sessions, tasks, simulations, reports)
    ├── OASIS simulation subprocesses (Twitter/Reddit)
    │       ↔ IPC via JSON command/response files + polling
    └── LLM providers (OpenAI API / Anthropic API / Claude CLI / Codex CLI)
```

In Docker, a `codex-proxy` sidecar wraps the Codex CLI as an OpenAI-compatible HTTP API endpoint.

---

## Core Domain Model

### Project
The top-level unit. Created when a user uploads documents and sets a simulation requirement.
- Stored in `uploads/projects/{proj_id}/`
- Contains: uploaded files, extracted text, project metadata (name, requirement, ontology, graph_id)
- Managed by `ProjectStore`

### WorkbenchSession
Ties together the four IDs at the heart of a workflow run: `project_id`, `graph_id`, `simulation_id`, `report_id`. Acts as a workflow cursor.
- Persisted to `uploads/workbench_sessions/wb_{id}.json`
- Managed by `SessionManager` with get/create/attach operations
- Created once per workflow start, mutated as IDs are generated

### Task
Background job tracker for long-running operations (graph build, simulation prep, report generation).
- Persisted to `uploads/tasks/{uuid}.json`
- Singleton `TaskManager` (thread-safe, in-memory cache + disk fallback)
- Statuses: `pending → processing → completed / failed`
- Polled by frontend via `/api/tasks/{task_id}`

### SimulationState
Tracks the full lifecycle of one simulation run.
- Persisted to `uploads/simulations/{sim_id}/state.json`
- Statuses: `created → preparing → ready → running → completed / stopped / failed`
- Owned by `SimulationManager`

### Report
Generated Markdown report from simulation analysis.
- Stored in `uploads/reports/{report_id}/`
- Multi-section: `outline.json`, `section_N.md`, `full_report.md`, `agent_log.jsonl`

---

## Data Flow

### Step 1 — Ontology Generation
1. User uploads PDF/MD/TXT files + states simulation requirement
2. `GenerateOntologyTool` processes files via `FileParser` + `TextProcessor`
3. LLM generates an ontology (entity types, relationships)
4. Project created and saved; ontology stored in project metadata

### Step 2 — Graph Build (async)
1. `BuildGraphTool.start()` creates a background task, returns `task_id`
2. Background thread runs `EntityExtractor` → `GraphBuilder`
3. Entities/relationships extracted via LLM, stored in KuzuDB
4. Task progress polled by frontend; graph_id attached to session on completion

### Step 3 — Simulation Preparation (async)
1. `PrepareSimulationTool.start()` creates background task
2. `SimulationManager.prepare_simulation()` runs:
   - Phase 1: `EntityReader` reads KuzuDB → filters to simulation-relevant entities
   - Phase 2: `OasisProfileGenerator` builds agent persona profiles (LLM, parallel)
   - Phase 3: `SimulationConfigGenerator` uses LLM to generate platform parameters
3. Outputs: `reddit_profiles.json`, `twitter_profiles.csv`, `simulation_config.json`

### Step 4 — Simulation Run
1. `RunSimulationTool.start()` spawns background thread
2. `SimulationRunner` launches OASIS scripts as subprocesses (`scripts/run_*.py`)
3. IPC via JSON files in `uploads/simulations/{id}/ipc_responses/`
4. Status polled via `simulation_ipc.py` command/response pattern

### Step 5 — Report Generation (async)
1. `GenerateReportTool.start()` creates background task
2. `ReportAgent` runs multi-tool LLM loop:
   - Tools include `graph_tools.py` (KuzuDB queries) and simulation data access
   - Generates outline, then sections, then stitches full report
3. Report persisted section-by-section; frontend polls task for progress

---

## Session / State Management

- `WorkbenchSession` is the orchestration facade — it composes all tools and holds the session state
- `SessionManager` persists sessions to disk, enabling browser reload recovery
- State advances linearly: session starts empty, IDs are `attach()`-ed as pipeline progresses
- Frontend maintains `projectId`, `simulationId`, `reportId` in URL params and component props

---

## Task / Job Management

- `TaskManager` is a process-level singleton (double-checked locking)
- All long-running operations return a `task_id` immediately
- Frontend polls `GET /api/tasks/{task_id}` until `status === "completed"` or `"failed"`
- Tasks survive Flask restarts (disk-persisted JSON)
- Cleanup method removes tasks older than 24h

---

## Simulation Architecture

OASIS simulations run as external Python subprocesses. The backend does not directly control simulation logic — it:
1. Generates all input files (profiles, config)
2. Spawns the OASIS script subprocess
3. Monitors via IPC (polling JSON response files)
4. Reads output from simulation SQLite DB and log files

Platforms: Twitter (CSV profiles) and Reddit (JSON profiles) can run in parallel via `run_parallel_simulation.py`.

---

## LLM Provider Abstraction

`Config.LLM_PROVIDER` selects from four modes:
- `""` / `"openai"` — standard OpenAI SDK
- `"anthropic"` — Anthropic Python SDK
- `"claude-cli"` — spawns `claude` CLI as subprocess
- `"codex-cli"` — forwards to `codex-proxy` sidecar (Docker)

All modes share the same interface via `utils/llm_client.py`.

# Structure — MiroFish SIPE

## Repository Root

```
mirofish/
├── backend/                    # Python Flask API server
├── frontend/                   # Vue 3 SPA
├── codex-proxy/                # Codex CLI HTTP proxy sidecar
├── static/                     # Static assets (logos, screenshots)
├── .github/workflows/          # CI/CD (Docker build + push to GHCR)
├── docker-compose.yml          # Production compose
├── docker-compose.local.yml    # Local dev compose
├── Dockerfile                  # Multi-stage build (backend + frontend)
├── .env / .env.example         # Environment configuration
└── README.md
```

---

## Backend Module Organization

```
backend/
├── run.py                      # Flask app entry point (creates app, runs Waitress)
├── pyproject.toml              # uv package manifest
├── requirements.txt            # Pip fallback dependencies
├── uv.lock                     # Locked dependency tree
│
├── scripts/                    # Standalone execution scripts
│   ├── run_twitter_simulation.py   # Run Twitter OASIS simulation
│   ├── run_reddit_simulation.py    # Run Reddit OASIS simulation
│   ├── run_parallel_simulation.py  # Run both platforms in parallel
│   ├── action_logger.py            # Log simulation actions
│   └── test_profile_format.py      # Manual profile format tester
│
├── app/
│   ├── __init__.py             # Flask app factory (create_app)
│   ├── config.py               # Config class (all env vars, defaults)
│   │
│   ├── api/                    # REST API blueprints
│   │   ├── graph.py            # /api/graph/* (build, status, query)
│   │   ├── simulation.py       # /api/simulation/* (create, prepare, run, status)
│   │   └── report.py           # /api/report/* (generate, status, content)
│   │
│   ├── core/                   # Session/task orchestration
│   │   ├── workbench_session.py    # WorkbenchSession (main facade)
│   │   ├── session_manager.py      # WorkbenchSessionState + SessionManager
│   │   ├── task_manager.py         # Task + TaskManager (singleton)
│   │   └── resource_loader.py      # WorkbenchResources factory
│   │
│   ├── models/                 # Data models
│   │   ├── project.py          # ProjectState dataclass
│   │   └── task.py             # (Task model also in task_manager.py)
│   │
│   ├── resources/              # Storage backends (stores)
│   │   ├── documents/
│   │   │   └── document_store.py   # File-based document storage
│   │   ├── graph/
│   │   │   └── kuzu_store.py       # KuzuDB graph storage
│   │   ├── llm/
│   │   │   └── provider.py         # LLM provider selection
│   │   ├── projects/
│   │   │   └── project_store.py    # Project CRUD (file-based)
│   │   ├── reports/
│   │   │   └── report_store.py     # Report storage
│   │   └── simulations/
│   │       └── simulation_store.py # SimulationState storage
│   │
│   ├── services/               # Business logic services
│   │   ├── entity_extractor.py         # LLM-powered entity extraction from text
│   │   ├── entity_reader.py            # Read/filter entities from graph
│   │   ├── graph_builder.py            # Build KuzuDB from extracted entities
│   │   ├── graph_db.py                 # KuzuDB query helpers
│   │   ├── graph_memory_updater.py     # Update graph from simulation results
│   │   ├── graph_storage.py            # Graph storage abstraction
│   │   ├── graph_tools.py              # LLM-callable graph query tools
│   │   ├── oasis_profile_generator.py  # Generate agent personas (parallel LLM)
│   │   ├── ontology_generator.py       # Generate ontology from documents
│   │   ├── report_agent.py             # Multi-tool LLM report generation loop
│   │   ├── simulation_config_generator.py  # LLM-generated simulation params
│   │   ├── simulation_ipc.py           # IPC command/response for OASIS subprocesses
│   │   ├── simulation_manager.py       # Simulation lifecycle management
│   │   ├── simulation_runner.py        # Subprocess launcher for OASIS scripts
│   │   └── text_processor.py           # Text chunking and preprocessing
│   │
│   ├── tools/                  # WorkbenchSession-level tool wrappers
│   │   ├── build_graph.py          # BuildGraphTool (wraps graph build as background task)
│   │   ├── generate_ontology.py    # GenerateOntologyTool
│   │   ├── generate_report.py      # GenerateReportTool
│   │   ├── prepare_simulation.py   # PrepareSimulationTool
│   │   ├── run_simulation.py       # RunSimulationTool
│   │   └── simulation_support.py   # Shared simulation helpers
│   │
│   └── utils/                  # Cross-cutting utilities
│       ├── file_parser.py      # PDF/MD/TXT text extraction
│       ├── kuzu_paging.py      # Paginated KuzuDB queries
│       ├── llm_client.py       # LLM provider routing (OpenAI/Anthropic/CLI)
│       ├── logger.py           # Rotating file + console logging setup
│       └── retry.py            # Retry decorator for LLM calls
│
└── uploads/                    # Runtime data (gitignored)
    ├── projects/{proj_id}/     # Project files, extracted text, metadata
    ├── tasks/{uuid}.json       # Persistent task state
    ├── workbench_sessions/     # Session state JSON files
    ├── simulations/{sim_id}/   # Simulation data, profiles, configs, SQLite DBs
    └── reports/{report_id}/    # Report sections, agent logs
```

---

## Frontend Organization

```
frontend/
├── index.html
├── package.json
├── vite.config.js
└── src/
    ├── main.js                 # Vue app bootstrap (createApp, router, mount)
    ├── App.vue                 # Root component (router-view wrapper)
    │
    ├── router/
    │   └── index.js            # Route definitions:
    │                           #   / → Home
    │                           #   /process/:projectId → MainView (steps 1–4)
    │                           #   /simulation/:simulationId → SimulationView
    │                           #   /simulation/:simulationId/start → SimulationRunView
    │                           #   /report/:reportId → ReportView
    │                           #   /interaction/:reportId → InteractionView
    │
    ├── views/                  # Page-level components
    │   ├── Home.vue            # Landing page, project list, upload entry
    │   ├── MainView.vue        # Main wizard (wraps Step1–Step4 components)
    │   ├── SimulationView.vue  # Simulation config/preparation view
    │   ├── SimulationRunView.vue  # Live simulation monitoring
    │   ├── ReportView.vue      # Report viewer
    │   └── InteractionView.vue # Post-report interaction/Q&A
    │
    ├── components/             # Reusable step components
    │   ├── Step1GraphBuild.vue     # Graph construction UI
    │   ├── Step2EnvSetup.vue       # Simulation environment setup
    │   ├── Step3Simulation.vue     # Simulation preparation
    │   ├── Step4Report.vue         # Report generation
    │   ├── Step5Interaction.vue    # Interaction panel
    │   ├── GraphPanel.vue          # Graph visualization
    │   └── HistoryDatabase.vue     # Project/simulation history list
    │
    ├── api/                    # HTTP client modules
    │   ├── index.js            # Axios instance + base URL config
    │   ├── graph.js            # Graph API calls
    │   ├── simulation.js       # Simulation API calls
    │   └── report.js           # Report API calls
    │
    └── store/
        └── pendingUpload.js    # Pinia/Vuex store for upload state
```

---

## Data Persistence Layout

All persistent data lives under `backend/uploads/` (mapped as a Docker volume in production):

| Path | Content | Format |
|------|---------|--------|
| `uploads/projects/{proj_id}/` | Uploaded files, extracted text, project metadata | JSON + MD files |
| `uploads/tasks/{uuid}.json` | Background task state | JSON |
| `uploads/workbench_sessions/wb_{id}.json` | Session cursor state | JSON |
| `uploads/simulations/{sim_id}/` | Profiles (CSV/JSON), config, SQLite DB, action logs | Mixed |
| `uploads/reports/{report_id}/` | Outline, sections, full report, agent log | MD + JSON |
| `backend/data/kuzu_db/` | KuzuDB graph database files | KuzuDB binary |
| `backend/logs/` | Rotating daily log files | Text |

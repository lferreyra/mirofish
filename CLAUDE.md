# CLAUDE.md - MiroFish Development Guide

## Project Overview

MiroFish is a collective intelligence engine for prediction simulation ("预测万物"). It uses LLM-powered agents to simulate social media interactions (Twitter/Reddit via OASIS framework), build knowledge graphs (via Zep), and generate analytical reports.

## Tech Stack

- **Backend**: Python 3.11+, Flask, OpenAI SDK (for LLM), Zep Cloud (graph memory), CAMEL-OASIS (social simulation)
- **Frontend**: Vue 3, Vite 7, Vue Router 4, D3.js (graph visualization), Axios
- **Package Management**: `uv` (Python), `npm` (Node.js)
- **Deployment**: Docker, GitHub Container Registry (GHCR)
- **License**: AGPL-3.0

## Repository Structure

```
MiroFish/
├── backend/                    # Flask API server (port 5001)
│   ├── app/
│   │   ├── __init__.py         # Flask app factory (create_app)
│   │   ├── config.py           # Config class, reads from root .env
│   │   ├── api/                # Blueprint routes
│   │   │   ├── graph.py        # /api/graph/* endpoints
│   │   │   ├── simulation.py   # /api/simulation/* endpoints
│   │   │   └── report.py       # /api/report/* endpoints
│   │   ├── services/           # Core business logic
│   │   │   ├── graph_builder.py
│   │   │   ├── ontology_generator.py
│   │   │   ├── report_agent.py
│   │   │   ├── simulation_manager.py
│   │   │   ├── simulation_runner.py
│   │   │   ├── simulation_config_generator.py
│   │   │   ├── simulation_ipc.py
│   │   │   ├── text_processor.py
│   │   │   ├── oasis_profile_generator.py
│   │   │   ├── zep_tools.py
│   │   │   ├── zep_graph_memory_updater.py
│   │   │   └── zep_entity_reader.py
│   │   ├── models/             # Data models (task.py, project.py)
│   │   └── utils/              # Helpers (llm_client, file_parser, logger, retry, zep_paging)
│   ├── scripts/                # Standalone simulation scripts
│   ├── run.py                  # Backend entry point
│   ├── pyproject.toml          # Python dependencies (uv)
│   └── uv.lock
├── frontend/                   # Vue 3 SPA (port 3000)
│   ├── src/
│   │   ├── views/              # Page-level components (Home, MainView, SimulationView, etc.)
│   │   ├── components/         # Step components (Step1-5, GraphPanel, HistoryDatabase)
│   │   ├── api/                # API client modules (graph, simulation, report)
│   │   ├── store/              # State (pendingUpload)
│   │   ├── router/index.js     # Vue Router config
│   │   └── main.js             # App entry
│   ├── vite.config.js          # Vite config, proxies /api to backend
│   └── package.json
├── static/image/               # Static images for README
├── .env.example                # Environment variable template
├── docker-compose.yml          # Docker deployment config
├── Dockerfile                  # Multi-stage build (Python + Node)
└── package.json                # Root: orchestrates frontend + backend via concurrently
```

## Development Setup

### Prerequisites
- Node.js >= 18
- Python >= 3.11
- `uv` (Python package manager, https://docs.astral.sh/uv/)

### Install Dependencies
```bash
# Install all dependencies (Node root + frontend + Python backend)
npm run setup:all

# Or individually:
npm run setup          # Root + frontend Node deps
npm run setup:backend  # Python deps via uv
```

### Environment Configuration
Copy `.env.example` to `.env` at the project root and fill in:
- `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL_NAME` — Required. Any OpenAI-compatible LLM API.
- `ZEP_API_KEY` — Required. Zep Cloud for graph memory.
- `LLM_BOOST_*` — Optional. Accelerated LLM for specific tasks.

### Run Development Servers
```bash
npm run dev        # Starts both backend (port 5001) and frontend (port 3000) concurrently
npm run backend    # Backend only: cd backend && uv run python run.py
npm run frontend   # Frontend only: cd frontend && npm run dev
```

### Build
```bash
npm run build      # Builds frontend via vite build
```

## Architecture & Key Patterns

### API Structure
The backend uses Flask blueprints with three route groups:
- `/api/graph/*` — Knowledge graph operations (build, query nodes/edges)
- `/api/simulation/*` — OASIS social simulation management
- `/api/report/*` — AI-generated analytical report pipeline

### Workflow Pipeline (5 Steps)
The app follows a multi-step workflow exposed in the frontend:
1. **Graph Build** (`Step1GraphBuild`) — Upload documents, build knowledge graph
2. **Env Setup** (`Step2EnvSetup`) — Configure simulation parameters
3. **Simulation** (`Step3Simulation`) — Run OASIS social media simulation
4. **Report** (`Step4Report`) — Generate AI analysis report
5. **Interaction** (`Step5Interaction`) — Interactive Q&A with results

### LLM Integration
- Uses OpenAI SDK format for all LLM calls (`backend/app/utils/llm_client.py`)
- Supports any OpenAI-compatible API (Qwen, GLM, etc.)
- Config via environment variables, validated at startup

### External Services
- **Zep Cloud**: Graph memory storage and retrieval for knowledge graphs
- **CAMEL-OASIS**: Social media simulation framework (Twitter/Reddit platforms)

## Testing

```bash
cd backend && uv run pytest    # Run Python tests
```

Test dependencies: `pytest`, `pytest-asyncio` (in dev dependency group).

## CI/CD

- **Docker Image Build** (`.github/workflows/docker-image.yml`): Triggered on tag push or manual dispatch. Builds and pushes to GHCR with multi-arch support.

## Code Conventions

- **Language**: Code comments and log messages are primarily in Chinese (Simplified). User-facing strings support both Chinese and English.
- **Python style**: Standard Python conventions. No linter config enforced in CI.
- **Frontend**: Vue 3 Composition/Options API, single-file components (.vue), Vite for bundling.
- **API format**: JSON with `ensure_ascii=False` (Chinese characters rendered directly, not escaped).
- **Configuration**: All config flows through `backend/app/config.py` which reads from the root `.env` file.
- **Error handling**: Backend uses custom retry utilities (`backend/app/utils/retry.py`).

## Ports

| Service  | Port |
|----------|------|
| Frontend | 3000 |
| Backend  | 5001 |

## Docker Deployment

```bash
# Using docker-compose with pre-built image
cp .env.example .env  # Configure your API keys
docker compose up -d

# Or build locally
docker build -t mirofish .
docker run -p 3000:3000 -p 5001:5001 --env-file .env mirofish
```

## Important Notes for AI Assistants

- Always read the relevant source file before making changes.
- The `.env` file contains secrets — never commit it. Use `.env.example` as reference.
- The backend validates config at startup (`Config.validate()`). Both `LLM_API_KEY` and `ZEP_API_KEY` are required.
- Frontend proxies `/api` requests to the backend via Vite dev server config.
- Uploaded files go to `backend/uploads/` (gitignored, persisted via Docker volume).
- Logs go to `backend/logs/` (gitignored).

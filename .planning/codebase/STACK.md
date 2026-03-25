# Technology Stack

**Analysis Date:** 2026-03-24

## Languages

**Primary:**
- Python 3.11+ — Backend server, simulation engine, all business logic
- JavaScript (ES Modules) — Frontend SPA

**Secondary:**
- Cypher (KuzuDB query language) — Graph database queries in `backend/app/services/graph_storage.py`

## Runtime

**Environment:**
- Python 3.11 (minimum required, pinned in `backend/pyproject.toml`: `requires-python = ">=3.11"`)
- Node.js 20 (used in `Dockerfile` frontend build stage: `FROM node:20-bookworm-slim`)

**Package Manager:**
- Python: `uv` 0.9.26 — used in `Dockerfile` for fast dependency installs (`uv pip install --system`)
- Node: `npm` — standard npm with lockfile at `frontend/package-lock.json`
- Lockfile: `backend/uv.lock` (present), `frontend/package-lock.json` (present)

## Frameworks

**Backend Core:**
- Flask 3.0+ — HTTP server and REST API (`backend/pyproject.toml`, used in `backend/app/__init__.py`)
- Flask-CORS 6.0+ — Cross-origin request handling for the `/api/*` prefix

**Backend WSGI Server:**
- Waitress 3.0+ — Production WSGI server; used in `backend/run.py` when `FLASK_DEBUG=false`
  - Falls back to Flask dev server if waitress is not installed
  - Thread count configurable via `WAITRESS_THREADS` env var (default: 8)

**codex-proxy Sidecar:**
- FastAPI — OpenAI-compatible HTTP proxy wrapping the Codex CLI (`codex-proxy/main.py`)
- Uvicorn — ASGI server for the codex-proxy container (`codex-proxy/Dockerfile`)

**Frontend:**
- Vue 3.5 — Component framework (`frontend/package.json`)
- Vue Router 4.6 — Client-side routing (`frontend/src/router/index.js`)
- Vite 7.2 — Dev server and build tool (`frontend/vite.config.js`)

## Key Dependencies

**LLM SDKs:**
- `openai>=1.0.0` — OpenAI API + any OpenAI-compatible endpoint (OpenRouter, codex-proxy, etc.)
- `anthropic>=0.40.0` — Anthropic Claude API

**Graph Database:**
- `kuzu>=0.8.0` — Embedded local graph database; no external service required. Stores knowledge graphs per-project in `backend/data/kuzu_db/`. Fallback to JSON file storage available.

**Social Simulation:**
- `camel-oasis==0.2.5` — OASIS social media simulation framework (Twitter + Reddit simulation)
- `camel-ai==0.2.78` — CAMEL agent framework; dependency of camel-oasis; pinned exact versions

**File Processing:**
- `PyMuPDF>=1.24.0` — PDF text extraction (`backend/app/utils/file_parser.py`)
- `charset-normalizer>=3.0.0` + `chardet>=5.0.0` — Encoding detection for non-UTF-8 text files

**Data Validation:**
- `pydantic>=2.0.0` — Model validation; used in `codex-proxy/main.py` request models

**Frontend:**
- `axios 1.13` — HTTP client for API calls (`frontend/src/api/index.js`)
- `d3 7.9` — Graph visualization (`frontend/src/components/GraphPanel.vue`)

**Utilities:**
- `python-dotenv>=1.0.0` — `.env` file loading in `backend/app/config.py`

**Testing (dev):**
- `pytest>=8.0.0`
- `pytest-asyncio>=0.23.0`

## Build / Dev Tools

**Backend build system:**
- Hatchling — build backend specified in `backend/pyproject.toml` `[build-system]`

**Frontend build:**
- `@vitejs/plugin-vue 6.0.1` — Vue SFC compilation plugin for Vite
- Production build output: `frontend/dist/` (served by Flask in production)
- Dev proxy: Vite dev server on port 3000 proxies `/api` to Flask on port 5001

**Multi-stage Docker build (`Dockerfile`):**
1. Stage 1: `node:20-bookworm-slim` — builds frontend SPA via `npm ci && npm run build`
2. Stage 2: `python:3.11-slim` — installs Python deps via `uv`, copies built frontend dist
3. Final image serves both API (port 5001) and static frontend from one container

## Configuration

**Environment:**
- All runtime config loaded from `.env` via `python-dotenv` in `backend/app/config.py`
- Key vars: `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL_NAME`, `GRAPH_BACKEND`, `KUZU_DB_PATH`, `FLASK_DEBUG`, `FLASK_PORT`, `CORS_ORIGINS`
- See `.env.example` at project root for all supported variables

**Build:**
- `backend/pyproject.toml` — Python project metadata, dependency list, Hatchling config
- `backend/requirements.txt` — flat requirements file (mirrors pyproject.toml deps, used by Docker)
- `frontend/vite.config.js` — Vite config; `VITE_API_BASE_URL` env var sets API base in production builds

## Platform Requirements

**Development:**
- Python 3.11+
- Node.js 20+ (for frontend dev)
- `uv` for Python package management
- Optional: Docker Desktop for containerized workflow

**Production:**
- Docker + Docker Compose
- Traefik reverse proxy (see `docker-compose.yml`) for TLS termination at `synth.scty.org`
- Linux host with `/home/deploy/` directory structure (CLI tool mounts)
- GitHub Container Registry (ghcr.io) for image distribution

---

*Stack analysis: 2026-03-24*

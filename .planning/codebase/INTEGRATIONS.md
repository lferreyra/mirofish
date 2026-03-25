# External Integrations

**Analysis Date:** 2026-03-24

## LLM Providers

The backend uses a single unified `LLMClient` in `backend/app/utils/llm_client.py` that abstracts over four provider modes. The active mode is selected by the `LLM_PROVIDER` env var.

### Provider Modes

**`openai` (default / auto-detected):**
- SDK: `openai>=1.0.0`
- Auth env var: `LLM_API_KEY`
- Endpoint: `LLM_BASE_URL` (defaults to `https://api.openai.com/v1`)
- Model: `LLM_MODEL_NAME` (defaults to `gpt-4o-mini`)
- Covers: OpenAI directly, or any OpenAI-compatible provider (OpenRouter, local servers, etc.)

**`anthropic`:**
- SDK: `anthropic>=0.40.0`
- Auth env var: `LLM_API_KEY`
- Model: `LLM_MODEL_NAME` (example from `.env.example`: `claude-sonnet-4-20250514`)
- System messages are extracted and passed as the `system` parameter; JSON mode is injected as a prompt instruction

**`claude-cli`:**
- No SDK; invokes `claude -p --output-format json <prompt>` as a subprocess
- Uses the host-mounted Claude CLI binary (`/home/deploy/.local/share/claude/...`)
- Auth: via host-side Claude subscription credentials mounted at `/home/deploy/.claude`
- Timeout: 120s per call
- Used when running in Docker production to avoid API key management

**`codex-cli`:**
- No SDK; invokes `codex exec --skip-git-repo-check <prompt>` as a subprocess
- Used in two ways:
  1. Directly from `LLMClient._chat_codex_cli()` when `LLM_PROVIDER=codex-cli`
  2. Via the `codex-proxy` sidecar container (described below) when `LLM_PROVIDER=openai` with `LLM_BASE_URL=http://codex-proxy:11435/v1`

**Auto-detection logic** (when `LLM_PROVIDER` is blank): inspects `LLM_MODEL_NAME` and `LLM_BASE_URL` for `claude`/`anthropic` keywords; defaults to `openai`.

**Optional boost LLM** (for accelerated tasks):
- Vars: `LLM_BOOST_API_KEY`, `LLM_BOOST_BASE_URL`, `LLM_BOOST_MODEL_NAME`
- Used by services that support a separate faster model for high-volume calls

---

## codex-proxy Sidecar Service

**Purpose:** Wraps the Codex CLI as an OpenAI-compatible HTTP API so the main backend can call it over HTTP using the standard `openai` SDK path.

**Location:** `codex-proxy/main.py`, `codex-proxy/Dockerfile`

**Pattern:**
- FastAPI app exposing `POST /v1/chat/completions` and `GET /v1/models`
- Receives OpenAI-format `ChatRequest`, builds a text prompt, calls `codex exec` as an async subprocess, parses the output, returns OpenAI-format response
- Health check at `GET /health`
- Port: 11435
- Concurrency controlled by `asyncio.Semaphore(CODEX_PROXY_WORKERS)` (default 4)

**Docker Compose wiring** (`docker-compose.yml`):
```
mirofish container → LLM_BASE_URL=http://codex-proxy:11435/v1 → codex-proxy container → codex CLI binary
```
The main container depends on `codex-proxy` with a health check condition. The Codex CLI binary and its credentials are bind-mounted read-only from the host.

---

## Data Storage

### Graph Database — KuzuDB (primary)

**Type:** Embedded, local, file-based graph database (no external server)

**Library:** `kuzu>=0.8.0`

**Schema** (initialized in `backend/app/services/graph_storage.py`):
- Node tables: `Node`, `Episode`, `Metadata`
- Relationship table: `RELATES_TO` (Node → Node)
- FTS indexes: `node_lookup_idx`, `node_time_idx`, `episode_lookup_idx`

**File location:** `backend/data/kuzu_db/<graph_id>/graph.kuzu` (configurable via `KUZU_DB_PATH`)

**Thread safety:** Single `kuzu.Database` instance per path shared across threads via a module-level lock (`_kuzu_db_cache` in `backend/app/services/graph_storage.py`); each request gets its own `kuzu.Connection`.

**Abstraction layers:**
- `KuzuDBStorage` — low-level Cypher queries (`backend/app/services/graph_storage.py`)
- `GraphDatabase` — multi-graph facade with node/edge/episode operations (`backend/app/services/graph_db.py`)
- `KuzuGraphStore` — thin adapter used by API layer (`backend/app/resources/graph/kuzu_store.py`)

### Graph Database — JSON fallback

**Type:** Plain JSON files on disk

**Activated by:** `GRAPH_BACKEND=json` env var

**File layout per graph:** `<DATA_DIR>/<graph_id>/nodes.json`, `edges.json`, `episodes.json`, `metadata.json`

**Implementation:** `JSONStorage` class in `backend/app/services/graph_storage.py`

### Simulation Databases — SQLite (via OASIS)

**Type:** SQLite databases created by the `camel-oasis` simulation scripts

**File location:** `backend/uploads/simulations/<sim_id>/twitter_simulation.db`, `reddit_simulation.db`

**Created by:** OASIS simulation runner scripts (`backend/scripts/run_twitter_simulation.py`, `run_reddit_simulation.py`)

**Not accessed directly by Flask** — these are owned by the simulation subprocess.

### File-based Stores

All persistent application state beyond the graph is stored as JSON/CSV files under `backend/uploads/`:

| Path | Contents | Format |
|------|----------|--------|
| `uploads/projects/<proj_id>/project.json` | Project metadata | JSON |
| `uploads/projects/<proj_id>/extracted_text.txt` | Document text extracted from uploaded files | Plain text |
| `uploads/projects/<proj_id>/files/<hash>.md` | Uploaded and converted documents | Markdown |
| `uploads/simulations/<sim_id>/state.json` | Simulation lifecycle state | JSON |
| `uploads/simulations/<sim_id>/simulation_config.json` | LLM-generated simulation parameters | JSON |
| `uploads/simulations/<sim_id>/reddit_profiles.json` | OASIS agent profiles for Reddit | JSON |
| `uploads/simulations/<sim_id>/twitter_profiles.csv` | OASIS agent profiles for Twitter | CSV |
| `uploads/simulations/<sim_id>/env_status.json` | IPC liveness heartbeat | JSON |
| `uploads/simulations/<sim_id>/run_state.json` | Runner subprocess state | JSON |
| `uploads/simulations/<sim_id>/<platform>/actions.jsonl` | Per-round simulation action log | JSONL |
| `uploads/tasks/<uuid>.json` | Background task progress/results | JSON |
| `uploads/workbench_sessions/<wb_id>.json` | Workbench session state | JSON |
| `uploads/reports/<report_id>/` | Report sections, outline, agent log | Markdown/JSON/JSONL |

**Docker volume mounts:**
- `./backend/uploads:/app/backend/uploads` — persists user data across container restarts
- `./backend/data:/app/backend/data` — persists KuzuDB graph data

---

## Simulation IPC — File-Based Subprocess Communication

**Purpose:** Bi-directional communication between the Flask process and long-running OASIS simulation subprocesses.

**Implementation:** `backend/app/services/simulation_ipc.py`

**Pattern:** Command/response via filesystem polling:
1. Flask (`SimulationIPCClient`) writes a JSON command file to `<sim_dir>/ipc_commands/<uuid>.json`
2. Simulation subprocess (`SimulationIPCServer`) polls the `ipc_commands/` directory, executes the command, writes response to `<sim_dir>/ipc_responses/<uuid>.json`
3. Flask polls `ipc_responses/` with a configurable timeout (default 60s) and poll interval (default 0.5s)

**Supported command types** (`CommandType` enum):
- `INTERVIEW` — query a single agent for its response to a prompt
- `BATCH_INTERVIEW` — query multiple agents in one batch
- `CLOSE_ENV` — gracefully shut down the simulation environment

**Liveness check:** `SimulationIPCClient.check_env_alive()` reads `<sim_dir>/env_status.json`; `SimulationIPCServer` writes `{"status": "alive"}` on start and `{"status": "stopped"}` on shutdown.

**Why file-based (not sockets/queues):** Keeps the implementation portable, requires no additional infrastructure, and naturally persists command/response pairs for debugging. The simulation subprocess may be a different Python environment (conda `MiroFish` env) without Flask available.

---

## Frontend ↔ Backend Communication

**Pattern:** REST JSON API over HTTP

**Dev setup:** Vite dev server (port 3000) proxies `/api/*` to Flask on port 5001 (`frontend/vite.config.js`)

**Production:** Flask serves the built Vue SPA at `/` from `frontend/dist/`; API routes are prefixed `/api/`

**API client modules** in `frontend/src/api/`:
- `index.js` — axios instance base config
- `graph.js` — graph CRUD and entity endpoints
- `simulation.js` — simulation lifecycle and interview endpoints
- `report.js` — report generation and retrieval endpoints

**CORS:** Configured in Flask via `flask-cors` restricted to `CORS_ORIGINS` list (defaults to localhost:3000 and localhost:5001 in `backend/app/config.py`)

---

## Authentication & Identity

**Auth Provider:** None — no user authentication system is implemented.

**CORS** is the only access control mechanism in place (origin whitelist via `CORS_ORIGINS`).

**Flask `SECRET_KEY`:** Set via env var or auto-generated with `secrets.token_hex(32)` on each startup (`backend/app/config.py`). No persistent sessions are used.

---

## File Upload Processing

**Accepted formats:** PDF, Markdown (`.md`), plain text (`.txt`), `.markdown`

**Max upload size:** 50 MB (`MAX_CONTENT_LENGTH` in `backend/app/config.py`)

**PDF extraction:** `PyMuPDF` (`fitz`) — `backend/app/utils/file_parser.py`

**Encoding detection:** `charset-normalizer` + `chardet` for non-UTF-8 text files

**Storage:** Uploaded files saved to `backend/uploads/projects/<proj_id>/files/<hash>.<ext>` and extracted text to `extracted_text.txt`

---

## CI/CD & Deployment

**Container Registry:** GitHub Container Registry (`ghcr.io`)
- Image: `ghcr.io/<owner>/mirofish`
- Push triggered on git tags and manual workflow dispatch

**CI Pipeline:** `.github/workflows/docker-image.yml`
- Runs on `ubuntu-latest`
- Multi-platform build via QEMU + Docker Buildx
- No automated tests in CI pipeline

**Production reverse proxy:** Traefik
- Configured via Docker labels in `docker-compose.yml`
- Hostname: `synth.scty.org`
- Automatic TLS via Let's Encrypt (`letsencrypt` cert resolver)
- HTTP → HTTPS redirect middleware
- Backend port: 5001

**Local development:** `docker-compose.local.yml` — exposes port 5001 directly, no Traefik, no codex-proxy dependency, uses `LLM_API_KEY` from `.env` directly

---

## Environment Variables Reference

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `LLM_PROVIDER` | No | auto-detect | `openai`, `anthropic`, `claude-cli`, or `codex-cli` |
| `LLM_API_KEY` | Conditionally | — | Required unless using CLI providers |
| `LLM_BASE_URL` | No | `https://api.openai.com/v1` | API endpoint |
| `LLM_MODEL_NAME` | No | `gpt-4o-mini` | Model identifier |
| `GRAPH_BACKEND` | No | `kuzu` | `kuzu` or `json` |
| `KUZU_DB_PATH` | No | `./data/kuzu_db` | KuzuDB storage path |
| `DATA_DIR` | No | `./data/json_graphs` | JSON fallback storage path |
| `FLASK_DEBUG` | No | `false` | Enable Flask debug mode |
| `FLASK_HOST` | No | `0.0.0.0` | Bind address |
| `FLASK_PORT` | No | `5001` | Listen port |
| `CORS_ORIGINS` | No | localhost:3000, localhost:5001 | Comma-separated allowed origins |
| `SECRET_KEY` | No | auto-generated | Flask session secret |
| `WAITRESS_THREADS` | No | `8` | Production WSGI thread count |
| `OASIS_DEFAULT_MAX_ROUNDS` | No | `10` | Default simulation rounds |
| `REPORT_AGENT_MAX_TOOL_CALLS` | No | `5` | Report agent tool call limit |
| `REPORT_AGENT_MAX_REFLECTION_ROUNDS` | No | `2` | Report agent reflection limit |
| `REPORT_AGENT_TEMPERATURE` | No | `0.5` | Report agent LLM temperature |
| `CODEX_PROXY_WORKERS` | No | `4` | codex-proxy max concurrent workers |
| `CODEX_PROXY_TIMEOUT` | No | `180` | codex-proxy subprocess timeout (seconds) |
| `LLM_BOOST_API_KEY` | No | — | Optional fast/secondary LLM key |
| `LLM_BOOST_BASE_URL` | No | — | Optional fast/secondary LLM endpoint |
| `LLM_BOOST_MODEL_NAME` | No | — | Optional fast/secondary LLM model |

---

*Integration audit: 2026-03-24*

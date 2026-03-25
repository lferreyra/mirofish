# Concerns — MiroFish SIPE

## Severity Legend
- **HIGH** — likely to cause failures, data loss, or security issues in production
- **MEDIUM** — degrades reliability or maintainability; address before scaling
- **LOW** — quality/ergonomics issues; address when convenient

---

## Security

### [HIGH] No Authentication or Authorization
The Flask API has no authentication middleware. Any request to `/api/*` is accepted anonymously. All project data, simulation results, and reports are publicly accessible by anyone who can reach the backend.

**File:** `backend/app/__init__.py`, all `api/*.py` blueprints
**Fix:** Add API key or session-based auth before any public deployment.

### [HIGH] LLM_API_KEY in .env, no rotation mechanism
`LLM_API_KEY` is loaded from `.env` at startup with no validation that it's a well-formed key and no support for secrets managers (Vault, AWS SSM, etc.).

**File:** `backend/app/config.py:58`

### [MEDIUM] CORS allows localhost origins by default
Default `CORS_ORIGINS` includes `localhost:3000` and `localhost:5001`. In production, `CORS_ORIGINS` must be explicitly set — but there is no startup check that enforces this when `FLASK_DEBUG=False`.

**File:** `backend/app/config.py:20-28`

### [MEDIUM] Secret key regenerated on every restart (if not set)
`SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)` means sessions are invalidated on every restart unless `SECRET_KEY` is explicitly configured.

**File:** `backend/app/config.py:51`

---

## Performance & Scalability

### [HIGH] Blocking LLM calls in background threads
Profile generation and config generation run LLM calls in Python threads. Under the GIL, with many concurrent simulations, this can block the event loop or exhaust the thread pool.

**File:** `backend/app/services/simulation_manager.py`, `oasis_profile_generator.py`

### [HIGH] Simulation IPC is polling-based
Communication with OASIS subprocesses is via JSON file polling (write command file, poll response file). No timeout enforcement is visible — a hung subprocess will poll forever.

**File:** `backend/app/services/simulation_ipc.py`

### [MEDIUM] No upload size enforcement per project
`MAX_CONTENT_LENGTH = 50MB` is set globally, but there is no per-project quota. A single project could accumulate large extracted_text.txt files and simulation SQLite databases.

**File:** `backend/app/config.py:70`

### [MEDIUM] SimulationManager uses in-memory state cache
`SimulationManager._simulations` dict is an instance-level cache. If multiple Flask workers run (e.g. Gunicorn multi-worker), each worker has a stale cache. Waitress is single-process, so this is safe in current deployment but will break under horizontal scaling.

**File:** `backend/app/services/simulation_manager.py:137`

### [LOW] TaskManager is a process-level singleton
`TaskManager` uses a class-level `_instance` singleton. This is correct for Waitress single-process but incompatible with multi-worker deployments.

**File:** `backend/app/core/task_manager.py:87-98`

---

## Data Integrity

### [HIGH] No atomic writes for SimulationManager state
`SimulationManager._save_simulation_state()` writes directly without atomic temp-file replacement (unlike `SessionManager` and `TaskManager` which use `os.replace`). A crash mid-write corrupts state.

**File:** `backend/app/services/simulation_manager.py:145-155`

### [MEDIUM] KuzuDB has no backup or migration strategy
KuzuDB is embedded and schema-less from the application perspective. There is no migration tooling, no backup automation, and no versioning of the graph schema. A schema change requires manual data migration.

**File:** `backend/app/resources/graph/kuzu_store.py`

### [MEDIUM] Simulation SQLite databases not tracked
OASIS subprocesses create SQLite databases (`reddit_simulation.db`, `twitter_simulation.db`) in the simulation directory. These are never cleaned up and can grow unboundedly.

**Path:** `uploads/simulations/{sim_id}/`

---

## Technical Debt

### [MEDIUM] Dual simulation management paths
`SimulationManager` (`services/`) and `SimulationStore` (`resources/simulations/`) appear to overlap in responsibility. The store wraps the manager or duplicates some state logic. This creates confusion about the authoritative source of simulation state.

**Files:** `backend/app/services/simulation_manager.py`, `backend/app/resources/simulations/simulation_store.py`

### [MEDIUM] Mixed Chinese/English comments and strings
Many service files contain comments and log messages in Chinese (original authors appear Chinese). This creates a language inconsistency across the codebase.

**Files:** `simulation_manager.py`, `oasis_profile_generator.py`, others

### [MEDIUM] No test suite
See `TESTING.md`. No automated tests exist — any refactoring is done without a safety net.

### [LOW] `scripts/` not packaged — conda environment assumption
`get_run_instructions()` hardcodes `conda activate MiroFish` in the instructions string. The scripts assume a `MiroFish` conda environment exists, which is not created by the Docker build.

**File:** `backend/app/services/simulation_manager.py:536`

### [LOW] Duplicate profile save (reddit)
In `prepare_simulation()`, Reddit profiles are saved twice: once in real-time during generation (`realtime_output_path`) and once at the end after all profiles complete. The second save is redundant but harmless.

**File:** `backend/app/services/simulation_manager.py:360-366`

---

## Operational Concerns

### [MEDIUM] No health check endpoint
No `/health` or `/ping` endpoint. Docker compose has no `healthcheck` defined, so container orchestrators cannot detect a hung backend.

### [MEDIUM] Logs written to `backend/logs/` inside container
Log files are written to a path relative to the source tree. In Docker, this means logs are lost on container restart unless the logs directory is volume-mounted.

**File:** `backend/app/utils/logger.py:27`

### [LOW] No observability beyond file logs
No metrics (Prometheus), no distributed tracing. Debugging production issues requires reading raw log files.

### [LOW] CI builds on every tag push, no staging check
The CI pipeline pushes `latest` to GHCR on every tag. There is no staging deployment or smoke test before the `latest` tag is updated.

**File:** `.github/workflows/docker-image.yml`

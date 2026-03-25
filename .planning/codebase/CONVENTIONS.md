# Coding Conventions

**Analysis Date:** 2026-03-24

## Naming Patterns

**Python Files:**
- `snake_case` throughout: `graph_builder.py`, `entity_extractor.py`, `llm_client.py`
- Service files named `<noun>_<verb>er.py` or `<noun>_<noun>.py`: `report_agent.py`, `simulation_manager.py`
- Store files: `<resource>_store.py` — `project_store.py`, `report_store.py`, `simulation_store.py`
- Tool files: `<verb>_<noun>.py` — `build_graph.py`, `generate_report.py`, `run_simulation.py`
- Script files: `run_<platform>_simulation.py`, `test_<thing>.py`

**Python Classes:**
- `PascalCase`: `LLMClient`, `GraphBuilderService`, `RetryableAPIClient`, `WorkbenchSession`
- Manager classes: `ProjectManager`, `TaskManager`, `SimulationManager`, `ReportManager`
- Service classes: `GraphBuilderService`, `GraphToolsService`
- Store classes: `ProjectStore`, `ReportStore`, `SimulationStore`
- Runner classes: `RedditSimulationRunner`
- Handler classes: `IPCHandler`, `PlatformActionLogger`, `SimulationLogManager`

**Python Functions:**
- `snake_case`: `get_logger`, `setup_logger`, `retry_with_backoff`, `generate_ontology`
- Private helpers prefixed with `_`: `_get_bool_env`, `_resolve_path`, `_detect_provider`, `_clean_content`
- Flask route functions use `snake_case` matching the endpoint action: `get_project`, `list_projects`, `delete_graph`

**Python Variables:**
- `snake_case`: `graph_id`, `project_id`, `simulation_id`, `task_manager`
- Constants: `SCREAMING_SNAKE_CASE` — `LOG_DIR`, `IPC_COMMANDS_DIR`, `ENV_STATUS_FILE`
- Config attributes on the `Config` class: `SCREAMING_SNAKE_CASE` — `LLM_API_KEY`, `GRAPH_BACKEND`, `UPLOAD_FOLDER`

**JavaScript/Vue:**
- API function names: `camelCase` — `generateOntology`, `buildGraph`, `getTaskStatus`, `getProject`
- Vue component files: `PascalCase` — `Step1GraphBuild.vue`, `GraphPanel.vue`, `HistoryDatabase.vue`
- Vue view files: `PascalCase` ending in `View` or descriptive — `MainView.vue`, `SimulationRunView.vue`, `ReportView.vue`

## Code Style

**Formatting:**
- No formatter config file detected (no `.prettierrc`, `biome.json`, or `eslint.config.*` found)
- Python code follows PEP 8 conventions implicitly
- 4-space indentation in Python
- Docstrings use Google-style, triple-quoted, present tense

**Type Hints:**
- Used consistently in Python function signatures: `def setup_logger(name: str = 'mirofish', level: int = logging.DEBUG) -> logging.Logger`
- Imported from `typing`: `Optional`, `Dict`, `Any`, `List`, `Callable`, `Tuple`, `Type`
- `from __future__ import annotations` used in `config.py`

**Docstrings:**
- Module-level docstrings on every Python file explaining purpose
- Function docstrings with `Args:` and `Returns:` sections on all public functions
- Short inline comments use `#` on the line above the relevant code

## Import Organization

**Python Order (observed):**
1. Standard library (`os`, `sys`, `json`, `logging`, `threading`, `datetime`)
2. Third-party (`flask`, `openai`, `dotenv`, `pydantic`)
3. Internal relative imports (`from ..config import Config`, `from ..utils.logger import get_logger`)

**Relative Import Pattern:**
- All internal imports use relative paths: `from ..utils.logger import get_logger`
- Logger is always imported as: `logger = get_logger('mirofish.<module_name>')`
- Logger names follow dot-notation hierarchy: `mirofish`, `mirofish.api`, `mirofish.api.report`, `mirofish.retry`, `mirofish.llm_client`

**JavaScript/Vue:**
- Named exports from `./index` for the axios service: `import service, { requestWithRetry } from './index'`
- API modules grouped by domain: `src/api/graph.js`, `src/api/report.js`, `src/api/simulation.js`

## Error Handling

**Flask API Pattern:**
Every endpoint wraps its body in `try/except` with differentiated HTTP status codes:

```python
try:
    # happy path
    return jsonify({"success": True, "data": result})

except ValueError as e:
    return jsonify({"success": False, "error": str(e)}), 400

except FileNotFoundError as e:
    return jsonify({"success": False, "error": str(e)}), 404

except Exception as e:
    logger.error(f"Failed to <action>: {str(e)}")
    return jsonify({"success": False, "error": str(e)}), 500
```

- `ValueError` → 400 Bad Request
- `FileNotFoundError` → 404 Not Found
- Generic `Exception` → 500 Internal Server Error (always logged with `logger.error`)
- Successful responses always include `"success": True` and a `"data"` key
- Error responses always include `"success": False` and an `"error"` key

**Retry Pattern:**
- `@retry_with_backoff(max_retries=3)` decorator for synchronous functions (`backend/app/utils/retry.py`)
- `@retry_with_backoff_async(max_retries=3)` for async functions
- `RetryableAPIClient.call_with_retry()` for imperative retry
- Default: 3 retries, 1s initial delay, exponential backoff factor of 2.0, jitter enabled, max 30s delay
- On every retry attempt: `logger.warning(f"Function {func.__name__} attempt {attempt + 1} failed...")`
- After exhausting retries: `logger.error(f"Function {func.__name__} still failed after {max_retries} retries...")`

**LLM Client Error Handling:**
- `subprocess.TimeoutExpired` → raises `RuntimeError("... timed out after Xs")`
- `json.JSONDecodeError` on LLM response → raises `ValueError(f"Invalid JSON returned by LLM: ...")`
- Non-zero subprocess return code → raises `RuntimeError("... failed: <stderr>")`

**Script Error Handling:**
- Simulation scripts catch `KeyboardInterrupt` and `asyncio.CancelledError` separately
- IPC commands that fail: `self.send_response(command_id, "failed", error=error_msg)` — never silently swallow

## Logging

**Framework:** Python `logging` module, wrapped by `backend/app/utils/logger.py`

**Setup:**
- Single `setup_logger(name, level)` factory creates named loggers
- Two handlers per logger: `RotatingFileHandler` (DEBUG level, detailed format) + `StreamHandler(stdout)` (INFO level, simple format)
- File logs: daily rotation at `backend/logs/YYYY-MM-DD.log`, max 10MB, 5 backups, UTF-8
- Console logs: `[HH:MM:SS] LEVEL: message`
- File logs: `[YYYY-MM-DD HH:MM:SS] LEVEL [name.funcName:lineno] message`
- `logger.propagate = False` prevents duplicate output to root logger

**Usage Pattern:**
```python
# At module top — always
from ..utils.logger import get_logger
logger = get_logger('mirofish.<module_name>')

# Levels used:
logger.info("=== Starting ontology generation ===")        # section boundaries
logger.warning(f"Function {name} attempt {n} failed: {e}")  # retries, degraded state
logger.error(f"Failed to <action>: {str(e)}")               # caught exceptions in endpoints
logger.debug(...)                                            # file only, not console
```

**Module Logger Names (hierarchical):**
- `mirofish` — default / root app logger
- `mirofish.api` — graph API routes
- `mirofish.api.report` — report API routes
- `mirofish.retry` — retry utility
- `mirofish.llm_client` — LLM client

**Simulation Script Logging:**
- Uses Python `logging` directly (not the app logger)
- Per-simulation `simulation.log` in the simulation directory
- OASIS internal loggers redirected to named log files in `log/` subdirectory: `social.agent.log`, `social.twitter.log`, etc.
- Action events written as JSONL to `twitter/actions.jsonl` and `reddit/actions.jsonl`

## API Response Patterns

**Standard success envelope:**
```json
{"success": true, "data": <payload>}
```

**Standard error envelope:**
```json
{"success": false, "error": "<message string>"}
```

**List endpoints add `count`:**
```json
{"success": true, "data": [...], "count": 10}
```

**Existence checks add domain flags:**
```json
{"success": true, "data": {...}, "has_report": true}
```

**Task/progress payloads include `status`, `progress` (0-100), `message`:**
```json
{"success": true, "data": {"task_id": "...", "status": "processing", "progress": 45, "message": "..."}}
```

**HTTP Status Codes:**
- 200 — all success responses (no 201 for creates)
- 400 — missing required fields, `ValueError`
- 404 — resource not found, `FileNotFoundError`
- 500 — unhandled exceptions

**Frontend axios interceptor** (`frontend/src/api/index.js`) treats any response where `res.success === false` as a rejected Promise, so callers `.catch()` errors uniformly without inspecting the status code.

## Async Patterns

**Backend (Flask, not FastAPI):**
- Flask is used synchronously for HTTP endpoints — no `async def` route handlers
- Background task execution uses Python `threading.Thread` (see `report.py` which imports `threading`)
- Long-running jobs (graph build, report generation, simulation) are dispatched as background threads, tracked via `TaskManager` with UUIDs
- Async Python is used only in simulation scripts (`asyncio`, `await self.env.step(actions)`)

**Simulation Scripts:**
- `asyncio.run(main())` entry point
- `async def run(...)` for the main simulation loop
- `asyncio.Event` for shutdown coordination (`_shutdown_event`)
- `asyncio.wait_for(_shutdown_event.wait(), timeout=0.5)` for non-blocking command polling

**Frontend:**
- All API calls return Promises via axios
- `requestWithRetry(requestFn, maxRetries=3, delay=1000)` wraps long-running calls (ontology, graph build) with exponential backoff
- Polling pattern: frontend polls `/api/graph/task/<task_id>` and `/api/report/<report_id>/progress` to track async backend jobs

## Config/Environment Variable Patterns

**Single `Config` class** in `backend/app/config.py` — all config is class-level attributes, not instances.

**Loading order:**
1. `.env` at project root loaded via `python-dotenv` with `override=True`
2. Falls back to `load_dotenv()` (searches parent directories) if project root `.env` not found

**Helper functions for type coercion:**
- `_get_bool_env(name, default)` — treats `"1"`, `"true"`, `"yes"`, `"on"` as truthy
- `_resolve_path(default_path, env_name)` — returns `os.path.abspath()` of env value or default
- `_get_cors_origins()` — parses comma-separated string from `CORS_ORIGINS`

**Key environment variables:**
- `LLM_API_KEY` — required unless `LLM_PROVIDER` is `claude-cli` or `codex-cli`
- `LLM_BASE_URL` — defaults to `https://api.openai.com/v1`
- `LLM_MODEL_NAME` — defaults to `gpt-4o-mini`
- `LLM_PROVIDER` — auto-detected from model/URL if not set; can be `openai`, `anthropic`, `claude-cli`, `codex-cli`
- `GRAPH_BACKEND` — `kuzu` (default) or `json`
- `FLASK_DEBUG`, `FLASK_HOST`, `FLASK_PORT`
- `CORS_ORIGINS` — comma-separated list
- `OASIS_DEFAULT_MAX_ROUNDS` — integer, default 10
- `REPORT_AGENT_MAX_TOOL_CALLS`, `REPORT_AGENT_MAX_REFLECTION_ROUNDS`, `REPORT_AGENT_TEMPERATURE`
- `WAITRESS_THREADS` — default 8

**Validation:**
- `Config.validate()` returns a list of error strings (not exceptions)
- Called at startup in `backend/run.py`; errors are printed and process exits

## Frontend Patterns

**Vue Component Style:**
- Vue 3 with Options API (not Composition API) based on observed SFC structure
- Single File Components (`.vue`) with `<template>`, `<script>`, `<style>` blocks
- Components named `Step{N}{Action}.vue` for wizard steps: `Step1GraphBuild.vue`, `Step2EnvSetup.vue`, etc.
- Views named `<Domain>View.vue` or descriptive: `SimulationRunView.vue`, `ReportView.vue`
- Conditional rendering with `v-if`/`v-else-if`/`v-else` for phase/status display
- Dynamic class binding: `:class="{ 'active': currentPhase === 0, 'completed': currentPhase > 0 }"`

**API Call Pattern:**
- Domain API modules in `frontend/src/api/`: `graph.js`, `report.js`, `simulation.js`
- Every exported function wraps an axios call: `return service({ url, method, data })`
- Long-running calls use `requestWithRetry()` wrapper: `return requestWithRetry(() => service({...}))`
- Base URL from `VITE_API_BASE_URL` env var; all paths start with `/api/`

**State:**
- Pinia store for cross-component state: `frontend/src/store/pendingUpload.js`
- Local component state for UI phases (wizard step tracking)

## File Naming Conventions

| Layer | Pattern | Example |
|-------|---------|---------|
| Backend API routes | `<domain>.py` | `graph.py`, `report.py`, `simulation.py` |
| Backend services | `<noun>_<verb>er.py` or `<noun>_<noun>.py` | `graph_builder.py`, `report_agent.py` |
| Backend tools | `<verb>_<noun>.py` | `build_graph.py`, `generate_report.py` |
| Backend stores | `<resource>_store.py` | `project_store.py`, `report_store.py` |
| Backend models | `<entity>.py` | `project.py`, `task.py` |
| Backend utils | `<purpose>.py` | `logger.py`, `retry.py`, `llm_client.py` |
| Scripts | `run_<platform>_simulation.py` or `test_<thing>.py` | `run_reddit_simulation.py`, `test_profile_format.py` |
| Frontend API | `<domain>.js` | `graph.js`, `report.js` |
| Frontend components | `PascalCase.vue` | `GraphPanel.vue`, `Step1GraphBuild.vue` |
| Frontend views | `PascalCase.vue` | `MainView.vue`, `SimulationRunView.vue` |

---

*Convention analysis: 2026-03-24*

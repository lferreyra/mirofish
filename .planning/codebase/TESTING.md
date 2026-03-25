# Testing — MiroFish SIPE

## Summary

**No formal test suite exists.** There are no `pytest`, `unittest`, or frontend test files in this repository. The CI/CD pipeline (`.github/workflows/docker-image.yml`) performs only a Docker build and push — no test step is included.

---

## Formal Tests

| Type | Status |
|------|--------|
| Backend unit tests | None found |
| Backend integration tests | None found |
| Frontend unit tests (Vitest/Jest) | None found |
| Frontend E2E tests (Playwright/Cypress) | None found |
| API contract tests | None found |

No `tests/` directory, no `conftest.py`, no `pytest.ini` or `setup.cfg` test configuration.

---

## CI/CD Pipeline

File: `.github/workflows/docker-image.yml`

Triggers: push to any git tag, or manual `workflow_dispatch`.

Steps:
1. Checkout
2. Set up QEMU (multi-arch)
3. Set up Docker Buildx
4. Login to GHCR
5. Extract metadata (tags: `latest`, SHA, semver tag)
6. **Build and push Docker image** ← only step, no test run

**No linting, no type checking, no security scanning, no test execution** in the pipeline.

---

## Manual Debug / Validation Scripts

`backend/scripts/` contains standalone scripts used for manual testing and simulation development:

| Script | Purpose |
|--------|---------|
| `run_twitter_simulation.py` | Run a Twitter OASIS simulation from a config file |
| `run_reddit_simulation.py` | Run a Reddit OASIS simulation from a config file |
| `run_parallel_simulation.py` | Run both platforms in parallel |
| `action_logger.py` | Log and inspect simulation action streams |
| `test_profile_format.py` | Validate agent profile format before simulation run |

These scripts take a `--config <path>` argument pointing to a `simulation_config.json` file. They are the de facto validation path for simulation logic.

---

## Testing Gaps

The following are high-priority areas with no test coverage:

1. **Graph build pipeline** — entity extraction, KuzuDB write/read correctness
2. **Simulation preparation** — profile generation output format, config generation logic
3. **LLM provider fallback** — each of the 4 provider modes
4. **File-based stores** — concurrent read/write safety for projects, sessions, tasks
5. **API endpoints** — request validation, error responses, task polling behavior
6. **Report generation** — section stitching, agent tool loop termination
7. **IPC protocol** — simulation command/response JSON file pattern
8. **Retry logic** — `utils/retry.py` decorator behavior under LLM failures

---

## How to Add Tests

The project uses `uv` for dependency management (`backend/pyproject.toml`). To add a test suite:

```bash
# Activate environment
cd backend
uv run pytest  # or add pytest to pyproject.toml dev dependencies

# Suggested test structure
backend/
├── tests/
│   ├── conftest.py
│   ├── test_api/
│   ├── test_services/
│   └── test_utils/
```

Recommended immediate additions:
- `test_utils/test_retry.py` — pure logic, no external deps
- `test_utils/test_file_parser.py` — test PDF/MD parsing with fixture files
- `test_services/test_text_processor.py` — test chunking logic

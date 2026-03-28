# Phase 3: Simulation Rate Limit Control — Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Add configurable LLM throttling and automatic 429 retry to simulation runs. Delivers:
1. Inter-turn delay between agent turns (injected into simulation scripts)
2. Automatic exponential backoff retry on 429 errors for all LLM calls
3. Proactive TPM/RPM rate limiting via token bucket in the LLM client
4. Backend config endpoint to persist rate limit settings per simulation
5. Frontend settings panel in simulation setup (Step 3) with localStorage persistence

New capabilities NOT in scope: authentication, new simulation features, report format changes.

</domain>

<decisions>
## Implementation Decisions

### Config Delivery to Simulation Scripts
- **D-01:** Rate limit settings are injected into `simulation_config.json` before subprocess launch. `SimulationRunner.start_simulation()` merges a `rate_limit` section into the config file before spawning the subprocess. Scripts read settings from their existing config file — no new CLI args or env vars needed.
- **D-02:** The `rate_limit` section schema in `simulation_config.json`:
  ```json
  {
    "rate_limit": {
      "inter_turn_delay_ms": 500,
      "max_retries": 3,
      "retry_base_delay_s": 30,
      "tpm_limit": 0,
      "rpm_limit": 0
    }
  }
  ```
  `0` means unlimited for tpm_limit and rpm_limit.

### Retry and Throttle Implementation
- **D-03:** 429 retry logic lives in `backend/app/utils/llm_client.py` (the `LLMClient.chat()` method). This covers ALL LLM call sites — graph build, profile generation, simulation, report agent — not just simulation scripts.
- **D-04:** Retry uses exponential backoff: `wait = min(base_delay_s * (2 ** attempt), 300)`. Params come from `rate_limit` config or fallback defaults (base=30s, max=5min, max_retries=3).
- **D-05:** TPM/RPM enforcement also lives in `llm_client.py` via a token bucket throttle. Before each LLM call, the client checks against the configured RPM/TPM limits and sleeps if needed. `0` = no throttling.
- **D-06:** Rate limit events (429 hit, retry attempt, backoff wait) are logged with timestamp at `logger.warning` level.

### Settings UI
- **D-07:** Settings panel is an inline collapsible section inside `Step3Simulation.vue`, visible before the user starts a run. No modal, no separate view.
- **D-08:** Controls in the panel:
  - Inter-turn delay: slider (0–5000ms, step 100ms, default 500ms)
  - Max retries: number input (1–10, default 3)
  - Retry base delay: number input in seconds (default 30)
  - TPM limit: number input (0 = unlimited)
  - RPM limit: number input (0 = unlimited)
- **D-09:** Settings are persisted to `localStorage` under key `mirofish_rate_limit_settings`. Loaded on component mount, saved on any change.
- **D-10:** Settings are passed to the backend at simulation start — sent via the config endpoint before `RunSimulationTool.start()` is called.

### Backend Config Endpoint
- **D-11:** `POST /api/simulation/{id}/config` accepts a `rate_limit` object and merges it into the existing `simulation_config.json` for that simulation. `GET /api/simulation/{id}/config` returns the full config (or just the `rate_limit` section — Claude's discretion on response shape).
- **D-12:** No separate config file — everything lives in `simulation_config.json`.

### Claude's Discretion
- Token bucket implementation approach (sliding window vs fixed window) — Claude can choose the simpler option
- Whether to add a `rate_limit_settings` read on script startup (e.g., once at init vs per-call) — Claude decides
- Error message formatting for rate limit log events
- Whether GET /api/simulation/{id}/config returns the full config or just the rate_limit subsection

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs or ADRs. Requirements fully captured in decisions above.

### Key files to read before planning
- `backend/app/utils/llm_client.py` — where retry and TPM/RPM throttle will be added
- `backend/app/services/simulation_runner.py` lines 310–450 — `start_simulation()` method where config injection happens
- `backend/app/api/simulation.py` — existing config endpoints (lines ~741, ~861) and where new /config POST/GET will live
- `backend/scripts/run_twitter_simulation.py` — simulation script that reads `simulation_config.json`
- `frontend/src/views/Step3Simulation.vue` — where settings panel will be added
- `.planning/REQUIREMENTS.md` §R3 — full requirement spec

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `simulation_config.json` — already present per-simulation in `uploads/simulations/{id}/`; `start_simulation()` already reads it
- `LLMClient.chat()` in `llm_client.py` — single choke point for all LLM calls; adding retry/throttle here covers the entire system
- Existing argparse patterns in `run_twitter_simulation.py` — no new CLI args needed (config injection approach avoids this)
- `localStorage` pattern not yet established — new convention for this phase

### Established Patterns
- Config passing: `simulation_config.json` is the contract between `SimulationRunner` and simulation scripts
- Long-running background tasks return `task_id` for polling — rate limit settings don't affect this pattern
- No existing retry or backoff anywhere in the codebase
- Vue components use `ref()` + `watch()` for reactive state — same pattern for settings

### Integration Points
- `SimulationRunner.start_simulation()` (`simulation_runner.py:312`) — inject `rate_limit` into config before spawning subprocess
- `LLMClient.chat()` (`llm_client.py`) — add retry loop and token bucket check here
- `simulation.py` API blueprint — add new `POST/GET /{id}/config` routes (or extend existing config endpoints at ~line 741/861)
- `Step3Simulation.vue` — add collapsible settings section before the Run button

</code_context>

<specifics>
## Specific Ideas

- User explicitly requested TPM and RPM as user-configurable settings exposed in the UI panel (folded into scope)
- Token bucket throttle for TPM/RPM should live in `llm_client.py` alongside the retry logic — centralizes all rate management
- `0` as the sentinel for "unlimited" on TPM/RPM fields

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-simulation-rate-limit-control*
*Context gathered: 2026-03-28*

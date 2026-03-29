---
phase: 03-simulation-rate-limit-control
plan: 01
subsystem: api
tags: [rate-limiting, openai, anthropic, token-bucket, exponential-backoff, simulation]

# Dependency graph
requires:
  - phase: 01-english-localization
    provides: translated codebase with no Chinese text
  - phase: 02-brand-ui
    provides: Slater Consulting brand frontend
provides:
  - LLMClient with exponential backoff retry on 429 errors
  - Token bucket (RPM/TPM) proactive throttling in LLMClient
  - POST /api/simulation/{id}/config endpoint for persisting rate_limit settings
  - Inter-turn delay injection in all three simulation scripts
  - env.step() retry wrapper for camel-ai 429 errors in all three simulation scripts
affects: [rate-limit-ui, simulation-scripts, llm-calls]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Token bucket pattern for proactive RPM/TPM enforcement (fixed-window per-minute)"
    - "Exponential backoff retry with cap: base_delay * (2^attempt), max 300s"
    - "Per-call rate_limit_config dict passed to LLMClient.chat() and chat_json()"
    - "simulation_config.json rate_limit section as single source of truth for all throttle settings"

key-files:
  created: []
  modified:
    - backend/app/utils/llm_client.py
    - backend/app/api/simulation.py
    - backend/scripts/run_twitter_simulation.py
    - backend/scripts/run_reddit_simulation.py
    - backend/scripts/run_parallel_simulation.py

key-decisions:
  - "rate_limit_config passed per-call to LLMClient, not at construction time — allows different configs per simulation run"
  - "Token bucket uses fixed-window per-minute (not sliding window) — simpler, sufficient for OpenAI/Anthropic tier limits"
  - "Default inter_turn_delay_ms is 500ms — configurable via simulation_config.json rate_limit section"
  - "env.step() retry uses same max_retries and retry_base_delay_s as LLMClient — single config drives all layers"
  - "POST /config only writes rate_limit section — leaves all other config fields untouched via json.load/dump merge"

patterns-established:
  - "Rate limit config flow: POST /api/simulation/{id}/config -> simulation_config.json -> scripts read config.get('rate_limit', {})"
  - "All 429 retry logic checks: '429' in msg or 'rate limit' in msg or 'too many requests' in msg"

requirements-completed: [R3.1, R3.2, R3.4]

# Metrics
duration: 12min
completed: 2026-03-29
---

# Phase 3 Plan 01: Simulation Rate Limit Control — Backend Summary

**LLMClient 429 retry with exponential backoff, RPM/TPM token bucket throttle, POST /config endpoint for persisting rate_limit settings, and inter-turn delay injection across all three simulation scripts**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-29T12:02:40Z
- **Completed:** 2026-03-29T12:14:19Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- LLMClient.chat() and chat_json() accept optional `rate_limit_config`, retry on 429 with exponential backoff (base 30s, max 300s, default 3 retries), and log all rate limit events at warning level with timestamps
- _TokenBucket class enforces RPM and TPM limits proactively before each LLM call using fixed-window per-minute accounting, preventing hitting API quotas rather than recovering from them
- POST /api/simulation/{id}/config merges rate_limit section into simulation_config.json without overwriting other fields; all three simulation scripts (Twitter, Reddit, Parallel) read inter_turn_delay_ms and inject asyncio.sleep() after each env.step() call and retry env.step() on 429 errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Add retry, token bucket, and 429 handling to LLMClient** - `5c70087` (feat)
2. **Task 2: Add POST /config endpoint and inter-turn delay to simulation scripts** - `a53c8e1` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `backend/app/utils/llm_client.py` - Added _TokenBucket class, _is_rate_limit_error(), _check_token_bucket(), retry loop in chat(), rate_limit_config param in chat() and chat_json()
- `backend/app/api/simulation.py` - Added import json, POST /<id>/config route (update_simulation_config)
- `backend/scripts/run_twitter_simulation.py` - Added rate_limit_config read before loop, env.step() retry wrapper, inter-turn asyncio.sleep()
- `backend/scripts/run_reddit_simulation.py` - Added rate_limit_config read before loop, env.step() retry wrapper, inter-turn asyncio.sleep()
- `backend/scripts/run_parallel_simulation.py` - Added rate_limit_config read before both Twitter and Reddit loops, env.step() retry wrapper (x2), inter-turn asyncio.sleep() (x2)

## Decisions Made

- rate_limit_config passed per-call to LLMClient (not at construction time) — allows different simulations to use different throttle settings without re-instantiating the client
- Token bucket uses fixed-window per-minute approach — simpler than sliding window, matches how OpenAI/Anthropic define their RPM/TPM limits
- Default inter_turn_delay_ms of 500ms baked into all three scripts via `config.get("inter_turn_delay_ms", 500)` — safe default if no rate_limit section present
- No new Python dependencies added — uses stdlib threading, time, datetime only

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `run_parallel_simulation.py` has two identical simulation loops (Twitter and Reddit functions). The `replace_all=false` edit failed because both loops are literally identical. Used `replace_all=true` for the env.step() block, then inserted `rate_limit_config` variables using targeted Python line-number editing. Both loops now have full inter-turn delay and retry support.

## User Setup Required

None - no external service configuration required. Rate limit settings are configured via the POST /api/simulation/{id}/config endpoint after simulation preparation.

## Next Phase Readiness

- Rate limit backend is complete. The simulation scripts will use inter-turn delay and retry on 429 automatically once `rate_limit` is present in simulation_config.json (or use safe defaults if absent)
- Phase 3 Plan 02 (Settings UI) can now build on the POST /config endpoint to allow user-configurable throttle settings from the frontend

---
*Phase: 03-simulation-rate-limit-control*
*Completed: 2026-03-29*

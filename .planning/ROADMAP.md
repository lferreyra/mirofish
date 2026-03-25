# Roadmap — MiroFish SIPE v1

## Milestone 1 — Production-Ready for Slater Consulting

**Goal:** Make MiroFish SIPE fully usable in a professional English-speaking context with Slater Consulting branding and reliable simulation execution under LLM rate limits.

**Success:** The app runs end-to-end with zero Chinese text, looks like a Slater Consulting product, and handles OpenAI rate limits gracefully.

---

## Phase 1 — English Localization

**Goal:** Remove all Chinese text from the full stack — UI, status messages, logs, and source code.

**Scope:**
- Translate all Chinese strings in `frontend/src/**/*.vue` (labels, toasts, placeholder text, comments)
- Translate all Chinese progress/error messages in `backend/app/services/*.py` (simulation_manager, oasis_profile_generator, graph_builder, entity_extractor, etc.)
- Translate all Chinese log messages across all backend modules
- Translate all Chinese `#` comments and `"""docstrings"""` in Python files
- Translate Chinese comments in `backend/scripts/*.py`

**Plans:**
1. `plan-frontend-localization` — Audit and translate all `.vue` files
2. `plan-backend-localization` — Audit and translate all `.py` files (services, tools, utils, scripts)

**Done when:** Running a full simulation from upload to report shows zero Chinese characters anywhere in the UI, logs, or console output.

---

## Phase 2 — Slater Consulting Brand UI

**Goal:** Apply Slater Consulting's visual identity to the Vue frontend.

**Scope:**
- Replace current CSS color variables with Slater Consulting palette
- Add Geist Sans font (matching existing SaaS project conventions)
- Update app header to show Slater Consulting branding
- Ensure all components (buttons, cards, progress bars, status badges) use the new palette consistently

**Plans:**
1. `plan-brand-theming` — CSS variables, font import, color system
2. `plan-brand-components` — Header rebrand, component audit, favicon

**Done when:** App visually matches Slater Consulting dark navy/blue theme. Screenshot comparison passes against brand reference.

---

## Phase 3 — Simulation Rate Limit Control

**Goal:** Add configurable LLM throttling and automatic 429 retry to simulation runs.

**Scope:**
- Inter-turn delay injected into simulation execution loops (`scripts/run_twitter_simulation.py`, `scripts/run_reddit_simulation.py`, `scripts/run_parallel_simulation.py`)
- Exponential backoff retry on 429 errors in all LLM call sites during simulation
- Backend config endpoint for rate limit settings
- Frontend settings panel on simulation view (slider for delay, retry config)
- Settings persisted to localStorage

**Plans:**
1. `plan-rate-limit-backend` — Delay injection, 429 retry logic, config endpoint
2. `plan-rate-limit-frontend` — Settings UI panel, localStorage persistence

**Done when:** A simulation run that would normally hit rate limits completes successfully with configurable throttling. 429 errors are retried automatically with logged backoff.

---

## Phase Order

```
Phase 1 (Localization)
    → Phase 2 (Brand UI)          ← can start after Phase 1 (no dependency)
    → Phase 3 (Rate Limit Control) ← can start after Phase 1, parallel with Phase 2
```

Phases 2 and 3 are independent once Phase 1 is complete — they can be executed in parallel.

---

## Backlog (Post-v1)

- Authentication layer (Phase BACKLOG.1)
- Atomic simulation state writes (Phase BACKLOG.2)
- Basic test suite (Phase BACKLOG.3)
- Health check endpoint + Docker healthcheck (Phase BACKLOG.4)

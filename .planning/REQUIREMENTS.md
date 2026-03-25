# Requirements — MiroFish SIPE v1

## R1 — Full English Localization

### R1.1 Frontend UI Text
All text visible in the browser must be in English.
- Page titles, section headers, button labels, placeholder text
- Status badges, progress messages, error toasts
- Tooltips, helper text, confirmation dialogs
- Any hardcoded Chinese strings in `.vue` files

**Files:** `frontend/src/views/*.vue`, `frontend/src/components/*.vue`

### R1.2 Backend Status & Progress Messages
All strings sent from backend to frontend (task progress messages, error messages, API responses) must be in English.
- `progress_callback("...", N, "Chinese message")` calls in services
- Error strings in `raise ValueError(...)`, `state.error = "..."`
- Log messages visible to users (simulation.log, console_log.txt)

**Files:** `backend/app/services/*.py`, `backend/app/tools/*.py`

### R1.3 Log Files
Backend log output must be in English.
- `logger.info(...)`, `logger.error(...)`, `logger.debug(...)` calls
- Simulation subprocess log output

**Files:** `backend/app/services/*.py`, `backend/app/utils/logger.py`, `backend/scripts/*.py`

### R1.4 Source Code Comments
All comments and docstrings must be in English.
- Python `#` comments and `"""docstrings"""`
- JavaScript/Vue `//` comments and `/* blocks */`

**Files:** All `.py` and `.vue`/`.js` files in `backend/app/` and `frontend/src/`

---

## R2 — Slater Consulting Brand UI

### R2.1 Color System
Apply Slater Consulting palette via CSS custom properties in `frontend/src/style.css` (or equivalent):

| Token | Value | Use |
|-------|-------|-----|
| `--background` | `hsl(210, 57%, 11%)` | Page background |
| `--primary` | `hsl(217, 75%, 47%)` | CTAs, active states, links |
| `--accent` | `hsl(213, 75%, 60%)` | Highlights, hover states |
| `--secondary` | `hsl(213, 40%, 18%)` | Card backgrounds |
| `--foreground` | `hsl(220, 33%, 97%)` | Body text |
| `--muted-foreground` | `hsl(213, 20%, 60%)` | Secondary text |
| `--border` | `hsl(213, 30%, 22%)` | Borders, dividers |

### R2.2 Typography
- Primary font: **Geist Sans** (or Inter as fallback)
- Import via `@fontsource/geist-sans` or CDN
- Weights used: 400 (body), 500 (labels), 600 (headings), 700 (hero)

### R2.3 Header / Branding
- App header must show "Slater Consulting" name or logo
- MiroFish logo can be retained as product name ("MiroFish SIPE — Slater Consulting") or replaced
- Favicon updated to match brand

### R2.4 Component Consistency
- Buttons: use `--primary` for primary actions, `--secondary` for ghost/outline
- Cards: `--secondary` background with `--border` border
- Progress bars: `--primary` fill
- Status indicators consistent with brand palette (no red/green clashing with theme)

---

## R3 — Simulation Rate Limit Control

### R3.1 Inter-Turn Delay
- Configurable delay (ms) injected between agent turns during simulation runs
- Default: 500ms
- Range: 0ms (off) to 5000ms
- Applied to both Twitter and Reddit simulation loops

### R3.2 Automatic 429 Retry
- When a LLM call returns a 429 (rate limit) error during simulation, the system must:
  1. Catch the error without crashing the simulation
  2. Wait with exponential backoff (base: 30s, max: 5 minutes)
  3. Retry the failed call
  4. Log the rate limit event with timestamp
- Applies to all LLM provider modes (OpenAI API, Anthropic API)

### R3.3 Settings UI
- Settings panel (modal or sidebar) accessible from the simulation view
- Controls:
  - Inter-turn delay slider (0–5000ms, step 100ms)
  - Max retry attempts (1–10, default 3)
  - Retry base delay (seconds, default 30)
- Settings persisted to `localStorage` (no backend required)
- Settings applied at simulation start (passed as config to backend)

### R3.4 Backend Config Endpoint
- `POST /api/simulation/{id}/config` — accept rate limit settings
- `GET /api/simulation/{id}/config` — return current settings
- Settings stored in `simulation_config.json` alongside existing parameters

---

## Non-Functional Requirements

- **No regressions:** All existing simulation functionality must continue working after changes
- **No new dependencies:** Prefer existing packages; only add what's strictly needed
- **Docker compatible:** All changes must work inside the existing Docker build

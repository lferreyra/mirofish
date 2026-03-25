# MiroFish SIPE — Project Context

## What We're Building

MiroFish SIPE is an existing foresight workbench that converts policy/domain documents into running social simulations and analytical reports. This project initializes GSD planning for a set of targeted improvements to make the tool production-ready for internal use at Slater Consulting.

The application already works end-to-end. We are not rebuilding it — we are:
1. Replacing all Chinese-language text with English throughout the full stack
2. Reskinning the Vue frontend to match Slater Consulting brand identity
3. Adding global LLM rate-limit control to prevent hitting OpenAI/Anthropic quotas during simulation runs

## Who It's For

**Primary user:** Lucas (Slater Consulting) — using MiroFish SIPE internally to run regulatory foresight simulations for consulting engagements.

**Context:** The tool was originally built with Chinese-language conventions by its upstream authors. Lucas is adapting it for use in an English-speaking consulting context under Slater Consulting's brand.

## Existing Stack

- **Backend:** Python 3.11 + Flask 3.0, served by Waitress
- **Frontend:** Vue 3.5 + Vite 7.2 (Options API + Composition API mix)
- **Graph DB:** KuzuDB (embedded)
- **LLM:** Configurable — OpenAI SDK, Anthropic SDK, Claude CLI, or Codex CLI proxy
- **Simulation:** OASIS framework (camel-ai) running Twitter + Reddit agent simulations as subprocesses
- **Deployment:** Docker + docker-compose; CI pushes to GHCR on tags

## Slater Consulting Brand

Extracted from `VS Code/Slater Consulting SaaS/src/index.css`:

```
Background:  hsl(210, 57%, 11%)  →  Deep navy   #0D1F35
Primary:     hsl(217, 75%, 47%)  →  Bright blue  #1E67D6
Accent:      hsl(213, 75%, 60%)  →  Light blue   #4B91E8
Secondary:   hsl(213, 40%, 18%)  →  Dark slate   #192C3E
Foreground:  hsl(220, 33%, 97%)  →  Near-white   #F0F3FA
Muted text:  hsl(213, 20%, 60%)  →  Cool gray    #839BB0
Border:      hsl(213, 30%, 22%)  →  Dark border  #1F3347
Font:        Geist Sans (weights 400/500/600/700)
```

Design style: Dark navy background, bright blue CTAs, glass-morphism card effects, clean professional.

## Success Criteria (v1 Done)

- [ ] Zero Chinese characters visible anywhere in the running app (UI, status messages, toasts)
- [ ] Zero Chinese in backend log files during a full simulation run
- [ ] Zero Chinese in source code comments and docstrings
- [ ] Frontend matches Slater Consulting color palette (background, primary, accent, text)
- [ ] Slater Consulting logo/name displayed in header (replacing MiroFish branding where appropriate)
- [ ] Rate limit control: configurable delay between agent turns (default: 500ms)
- [ ] Rate limit retry: automatic exponential backoff when 429 errors hit during simulation
- [ ] Settings panel in UI to adjust rate limit delay without code changes

## Scope Boundaries

**In scope:**
- English translation of all user-facing strings (frontend + backend status messages)
- English translation of all source code comments/docstrings
- Frontend CSS/color theming
- Global rate limiter for simulation runs (delay between turns + 429 retry)
- Basic settings UI for rate control

**Out of scope for v1:**
- Functional changes to simulation logic
- Authentication/authorization
- New simulation features
- Report format changes
- Backend architecture changes

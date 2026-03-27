---
phase: 02-brand-ui
plan: 01
subsystem: frontend
tags: [css-tokens, typography, brand, theming, favicon]
dependency_graph:
  requires: []
  provides: [global-css-tokens, geist-sans-font, brand-favicon, clean-home-vue]
  affects: [frontend/src/style.css, frontend/src/main.js, frontend/index.html, frontend/public/favicon.svg, frontend/src/App.vue, frontend/src/views/Home.vue]
tech_stack:
  added: ["@fontsource/geist-sans"]
  patterns: ["CSS custom properties (design tokens)", "fontsource npm font delivery"]
key_files:
  created:
    - frontend/src/style.css
    - frontend/public/favicon.svg
  modified:
    - frontend/src/main.js
    - frontend/index.html
    - frontend/src/App.vue
    - frontend/src/views/Home.vue
    - frontend/package.json
    - frontend/package-lock.json
decisions:
  - "@fontsource/geist-sans installed for weights 400 and 600 only"
  - "style.css contains only :root token block — no * or body reset (those stay in App.vue)"
  - "Home.vue var(--font-mono) replaced with explicit JetBrains Mono stack since --font-mono local var was deleted"
  - "gradient-text fixed from hardcoded #000000 (invisible on dark) to var(--foreground)/var(--muted-foreground)"
  - "Navbar background uses var(--card) for dark elevated surface, not var(--foreground)"
metrics:
  duration: "~8 minutes"
  completed: "2026-03-27"
  tasks_completed: 2
  files_changed: 8
---

# Phase 2 Plan 01: Brand Theming — Token System Summary

**One-liner:** Slater Consulting CSS token system (13 vars) with Geist Sans font via @fontsource, dark-navy favicon SVG, and Home.vue :root conflict resolved.

---

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Create token system, install font, update entry points | 7796fc2 | style.css (new), main.js, index.html, favicon.svg (new), App.vue, package.json |
| 2 | Delete Home.vue :root block and replace orange/black/white vars | 69fb122 | Home.vue |

---

## What Was Built

### Task 1: Token System & Entry Points

- **`frontend/src/style.css`** — Created with 13 CSS custom properties forming the Slater Consulting palette: `--background`, `--foreground`, `--primary`, `--primary-foreground`, `--secondary`, `--secondary-foreground`, `--accent`, `--accent-foreground`, `--muted-foreground`, `--border`, `--card`, `--destructive`, `--destructive-foreground`. No `*` reset or `body` block — those remain in App.vue's unscoped `<style>` as intended.

- **`frontend/src/main.js`** — `import './style.css'`, `import '@fontsource/geist-sans/400.css'`, and `import '@fontsource/geist-sans/600.css'` added before `createApp`.

- **`frontend/index.html`** — Google Fonts CDN trimmed to JetBrains Mono only (Inter, Space Grotesk, Noto Sans SC removed). Title updated to `MiroFish SIPE — Slater Consulting`. Meta description updated to `MiroFish SIPE — Slater Consulting Prediction Platform`. Favicon changed from `/icon.png` to `/favicon.svg`.

- **`frontend/public/favicon.svg`** — Programmatic SVG: dark navy rounded square (`hsl(210, 57%, 11%)`), "SC" text in Geist Sans 600 near-white (`hsl(220, 33%, 97%)`).

- **`frontend/src/App.vue`** — Global `<style>` updated: `font-family` changed to `'Geist Sans', 'Inter', system-ui, sans-serif`, `color` to `var(--foreground)`, `background-color` to `var(--background)`. Scrollbar track uses `var(--border)`, thumb uses `var(--muted-foreground)`, thumb hover uses `var(--accent)`.

### Task 2: Home.vue :root Conflict Resolution

- Deleted the entire `:root {}` block from Home.vue `<style scoped>` (defined `--black`, `--white`, `--orange`, `--border`, `--font-mono`, `--font-sans`, `--font-cn` — all conflicted with global tokens)
- `var(--orange)` replaced: primary elements → `var(--primary)`, hover states → `var(--accent)`
- `var(--black)` → `var(--foreground)` (all instances)
- `var(--white)` → `var(--background)` (all instances)
- `var(--gray-text)` → `var(--muted-foreground)`
- `var(--font-mono)` replaced with explicit `'JetBrains Mono', monospace` stack
- Navbar background: `var(--foreground)` was incorrect (near-white on dark background = inverted). Fixed to `var(--card)` (deepest navy).
- gradient-text: was `#000000 → #444444` (invisible on dark navy). Fixed to `var(--foreground) → var(--muted-foreground)`.

---

## Verification

All acceptance criteria met:

- `frontend/src/style.css` contains all 13 CSS custom property tokens
- `frontend/src/main.js` imports style.css before createApp, imports fontsource weights 400 and 600
- `frontend/package.json` contains `@fontsource/geist-sans` in dependencies
- `frontend/index.html` does NOT contain Inter, Space Grotesk, or Noto Sans SC CDN links
- `frontend/index.html` DOES contain JetBrains Mono CDN link
- `frontend/index.html` title reads `MiroFish SIPE — Slater Consulting`
- `frontend/index.html` favicon points to `/favicon.svg`
- `frontend/public/favicon.svg` exists with SC text on dark navy
- `frontend/src/App.vue` uses `var(--foreground)`, `var(--background)`, `var(--border)`, `var(--muted-foreground)`, `var(--accent)` for all color values
- `frontend/src/views/Home.vue` contains no `:root {}` block, no `--orange`, no `--black`, no `--white:`, no `#FF4500`
- `MiroFish_logo_left.jpeg` preserved in Home.vue hero section
- `npm run build` exits 0

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed navbar background token assignment**
- **Found during:** Task 2
- **Issue:** Replacing `var(--black)` globally with `var(--foreground)` would set the navbar background to near-white (`hsl(220, 33%, 97%)`), making it light-colored. The navbar needs a dark surface.
- **Fix:** Navbar background set to `var(--card)` (`hsl(213, 50%, 14%)` — deepest navy), text color stays `var(--foreground)`.
- **Files modified:** `frontend/src/views/Home.vue`
- **Commit:** 69fb122

**2. [Rule 1 - Bug] Fixed gradient-text invisible on dark background**
- **Found during:** Task 2
- **Issue:** `.gradient-text` used `linear-gradient(90deg, #000000 0%, #444444 100%)` — pure black gradient would be invisible on dark navy `--background`.
- **Fix:** Replaced with `linear-gradient(90deg, var(--foreground) 0%, var(--muted-foreground) 100%)` for legible text on dark background.
- **Files modified:** `frontend/src/views/Home.vue`
- **Commit:** 69fb122

**3. [Rule 1 - Bug] Replaced var(--font-mono) references with explicit font stack**
- **Found during:** Task 2
- **Issue:** After deleting the `:root` block, `var(--font-mono)` references in Home.vue would resolve to nothing (custom property undefined).
- **Fix:** All `var(--font-mono)` occurrences replaced with `'JetBrains Mono', monospace` explicit stack.
- **Files modified:** `frontend/src/views/Home.vue`
- **Commit:** 69fb122

---

## Known Stubs

None. All token references are wired to the new `style.css` definitions. No placeholder values remain in files created or modified by this plan.

---

## Self-Check: PASSED

- `frontend/src/style.css` — FOUND
- `frontend/public/favicon.svg` — FOUND
- Commit 7796fc2 — FOUND
- Commit 69fb122 — FOUND
- `npm run build` — exits 0 (679 modules, built in 1.71s)

# Phase 2: Slater Consulting Brand UI - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Reskin the Vue 3 frontend with Slater Consulting's visual identity. Deliverables: CSS custom property token system, Geist Sans font, updated header branding. Pure CSS/visual change — no functional logic modified, no simulation behavior touched.

</domain>

<decisions>
## Implementation Decisions

### Logo & Hero Image
- **D-01:** Keep `assets/logo/MiroFish_logo_left.jpeg` as-is in Home.vue hero section. Do not remove or replace.

### Hero Copy Scope
- **D-02:** Branding update applies to nav-brand text only. All hero taglines, descriptions, and body copy in Home.vue are left unchanged (not in Phase 2 scope).

### Color Token System
- **D-03:** All tokens defined in REQUIREMENTS.md R2.1 apply as-is. Full token set (including extended tokens `--card`, `--primary-foreground`, `--secondary-foreground`, `--accent-foreground`, `--destructive`, `--destructive-foreground`) documented in UI-SPEC.md Token Definitions section. Tokens live in a new `frontend/src/style.css` file.
- **D-04:** Green success indicators replaced with `--accent` (blue). No green remains post-Phase 2 (per R2.4 "no red/green clashing with theme").
- **D-05:** Home.vue `:root {}` block deleted entirely (it conflicts with global token names). All `var(--orange)` usages replaced with `var(--primary)` or `var(--accent)`.

### Typography
- **D-06:** Font delivery via `@fontsource/geist-sans` npm package (not CDN). Install: `cd frontend && npm install @fontsource/geist-sans`. Import weights 400 and 600 only.
- **D-07:** JetBrains Mono retained for monospace elements (logs, step numbers, simulation IDs, code blocks). Not replaced.
- **D-08:** Remove Google Fonts CDN links for Inter, Space Grotesk, and Noto Sans SC from `frontend/index.html`. Keep JetBrains Mono CDN link.

### Header Branding
- **D-09:** All 5 `.brand`/`.nav-brand` text instances updated to "Slater Consulting". Files: `views/Home.vue`, `views/MainView.vue`, `views/SimulationView.vue`, `views/SimulationRunView.vue`, `views/ReportView.vue`.
- **D-10:** `<title>` → `MiroFish SIPE — Slater Consulting`. `<meta name="description">` → `MiroFish SIPE — Slater Consulting Prediction Platform`.
- **D-11:** Favicon replaced with `frontend/public/favicon.svg` — programmatic text SVG ("SC" on dark navy `hsl(210, 57%, 11%)`). No brand asset exists.

### D3 Graph Colors
- **D-12:** D3 10-color palette array in `GraphPanel.vue` replaced with dark-theme-aware palette. Do NOT use CSS vars for D3 inline attributes — replace values directly in the JS array. Full old→new palette mapping in UI-SPEC.md D3 section.

### Implementation Order
- **D-13:** Execute in two waves: Wave 1 = token system (style.css, main.js, index.html, App.vue, Home.vue :root deletion). Wave 2 = component audit (all 13 .vue files per UI-SPEC component inventory).

### Claude's Discretion
- Exact scrollbar color values in App.vue (apply `--border` for track, `--muted-foreground` for thumb — consistent with theme)
- Whether to add `--card` usage to any component not explicitly listed in the UI-SPEC inventory
- Minor spacing adjustments if tokens expose layout issues during audit

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design Contract (primary source)
- `.planning/phases/02-brand-ui/02-UI-SPEC.md` — Complete visual contract: all token definitions, color substitution map (old hex → new token), component inventory with priority, D3 palette replacement, font loading instructions, favicon SVG code, implementation wave order, copywriting contract

### Technical Research
- `.planning/phases/02-brand-ui/02-RESEARCH.md` — Codebase analysis: why CSS vars don't cascade into scoped blocks, font delivery comparison, per-component hardcoded color audit

### Requirements
- `.planning/REQUIREMENTS.md` §R2.1–R2.4 — Color tokens table, typography spec, branding requirements, component consistency rules

### Brand Source
- `../VS Code/Slater Consulting SaaS/src/index.css` — Original brand token source (Tailwind HSL channels — NOT the format to use here; UI-SPEC has already translated to CSS hsl() syntax)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `App.vue` global `<style>` (unscoped): already the right place for `:root` vars and `#app` base styles — extend, don't replace
- `frontend/src/main.js`: already the import entry point — add fontsource + style.css imports here

### Established Patterns
- All Vue components use `<style scoped>` — CSS vars cascade into scoped blocks when defined on `:root`, so the token-first approach works
- No CSS preprocessor, no utility framework — plain CSS only
- Home.vue has a conflicting `:root {}` block in its scoped styles (defines `--border`, `--orange`) — must be deleted before global tokens are added

### Integration Points
- `frontend/index.html`: font CDN links live here (remove Inter/Space Grotesk/Noto Sans SC, keep JetBrains Mono)
- `frontend/public/`: favicon assets served from here — create `favicon.svg` here
- `GraphPanel.vue`: D3 colors are in JS strings, not CSS — requires targeted JS edits, not CSS changes

</code_context>

<deferred>
## Deferred Ideas

- Hero copy update (taglines, description text in Home.vue) — explicitly out of scope for Phase 2; copy is left as-is
- Slater Consulting logo image asset — no asset exists; favicon.svg covers branding need for now
- Animation/transition polish on theme elements — post-v1 backlog

</deferred>

---

*Phase: 02-brand-ui*
*Context gathered: 2026-03-27*

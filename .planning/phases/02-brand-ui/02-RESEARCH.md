# Phase 2: Slater Consulting Brand UI - Research

**Researched:** 2026-03-26
**Domain:** Vue 3 CSS theming, font loading, component styling
**Confidence:** HIGH (findings from direct codebase inspection, no external API needed)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| R2.1 | Apply Slater Consulting color palette via CSS custom properties | Current system: hardcoded hex values in scoped `<style>` blocks, no CSS vars exist — requires establishing the token system from scratch in `App.vue` global `<style>` |
| R2.2 | Add Geist Sans font (weights 400/500/600/700) | Current fonts loaded via Google Fonts CDN in `index.html`; same pattern works for Geist Sans CDN — OR install `@fontsource/geist-sans` (reference project uses @fontsource) |
| R2.3 | Update app header to show Slater Consulting branding | Header `.brand` div is duplicated across 4 view files; all read `MIROFISH` as plain text — single-point change pattern is to update each `.brand` text node and `<title>` in `index.html` |
| R2.4 | Buttons/cards/progress bars/badges use new palette consistently | Components use hardcoded hex (#FF5722, #000, #FFF, #FAFAFA, etc.) with no inheritance path — needs targeted per-component style edits after CSS vars are defined |
</phase_requirements>

---

## Summary

The MiroFish frontend has NO existing CSS custom property system. Styling is done entirely with hardcoded hex/rgba values spread across scoped `<style>` blocks in each `.vue` file. There is no `style.css` or `main.css` — the only global styles are in `App.vue`'s unscoped `<style>` block and in `Home.vue`'s `:root {}` block (which is scoped to the component, not truly global).

The current design language is a white/black/orange scheme (orange: `#FF5722` or `#FF4500`) inherited from MiroFish's original open-source branding. Slater Consulting's palette replaces this with a dark navy/blue theme (`--background: hsl(210, 57%, 11%)` through to `--border: hsl(213, 30%, 22%)`).

The reference design system (`Slater Consulting SaaS/src/index.css`) uses Tailwind utility classes with shadcn-style HSL custom properties. MiroFish uses plain CSS — no Tailwind, no component library. The migration must translate the same token values into standard CSS `hsl()` syntax rather than Tailwind-style space-separated HSL channels.

**Primary recommendation:** Establish CSS custom properties once in `App.vue`'s global `<style>` block, then audit each component file individually for hardcoded colors that won't inherit from those vars.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Vue 3 | 3.5.24 | Component framework | Already in project |
| Vite | 7.2.4 | Build tool | Already in project |
| Vanilla CSS (scoped) | — | All styling | No CSS preprocessor, no utility framework |

### Font Delivery Options
| Option | Method | Tradeoff |
|--------|--------|----------|
| Google Fonts CDN | `<link>` in `index.html` | Already used for Inter/JetBrains Mono; Geist Sans is available on Google Fonts as of 2024 |
| `@fontsource/geist-sans` | `npm install @fontsource/geist-sans` + import in main.js | Self-hosted, no CDN dependency; matches reference project convention |

**Recommendation:** Use `@fontsource/geist-sans` to match the Slater Consulting SaaS project convention and avoid CDN dependency in Docker deployments.

**Installation (if @fontsource chosen):**
```bash
cd frontend && npm install @fontsource/geist-sans
```

**Import in `frontend/src/main.js`:**
```js
import '@fontsource/geist-sans/400.css'
import '@fontsource/geist-sans/500.css'
import '@fontsource/geist-sans/600.css'
import '@fontsource/geist-sans/700.css'
```

---

## Architecture Patterns

### Current Color System: None (Hardcoded Everywhere)

There is no `frontend/src/style.css` or `frontend/src/assets/main.css`. The CSS structure is:

```
frontend/
├── index.html              — Google Fonts CDN links; favicon link; <title>
├── src/
│   ├── main.js             — No style imports
│   ├── App.vue             — Global unscoped <style> (reset, #app font/color, scrollbar)
│   ├── views/
│   │   ├── Home.vue        — Has :root {} block with --black/--white/--orange vars (SCOPED to component)
│   │   ├── MainView.vue    — Scoped styles, hardcoded hex, font-family declarations
│   │   ├── SimulationView.vue — Scoped styles, hardcoded hex
│   │   ├── SimulationRunView.vue — Scoped styles, hardcoded hex
│   │   └── ReportView.vue  — Scoped styles, hardcoded hex
│   └── components/
│       ├── Step1GraphBuild.vue — Scoped styles, hardcoded hex
│       ├── Step2EnvSetup.vue   — Scoped styles, hardcoded hex
│       ├── Step3Simulation.vue — Scoped styles, hardcoded hex
│       ├── Step4Report.vue     — Scoped styles, hardcoded hex + local CSS vars
│       ├── Step5Interaction.vue — (not inspected — same pattern assumed)
│       ├── GraphPanel.vue      — D3 inline color assignments in JS
│       └── HistoryDatabase.vue — (not inspected)
```

**Key finding:** `Home.vue` defines `:root { --black: #000000; --white: #FFFFFF; --orange: #FF4500; ... }` inside a `<style scoped>` block. In Vue scoped styles, `:root` selectors DO apply globally (CSS custom properties are inherited), but the practice is accidental — not intentional global theming.

### Where to Establish the Token System

**Option A (Recommended):** Add `:root {}` CSS variable block to `App.vue`'s existing unscoped `<style>` block. This is the single guaranteed-global location in the project.

```css
/* In App.vue <style> (not scoped) */
:root {
  --background: hsl(210, 57%, 11%);
  --foreground: hsl(220, 33%, 97%);
  --primary: hsl(217, 75%, 47%);
  --secondary: hsl(213, 40%, 18%);
  --accent: hsl(213, 75%, 60%);
  --muted-foreground: hsl(213, 20%, 60%);
  --border: hsl(213, 30%, 22%);
}
```

**Option B:** Create `frontend/src/style.css`, import it in `main.js`. This matches best practices and `REQUIREMENTS.md` wording (`"in frontend/src/style.css (or equivalent)"`).

**Recommendation:** Option B — create `frontend/src/style.css` as the authoritative token file, import in `main.js`. Also update `App.vue` global styles to use `var(--background)` and `var(--foreground)` for `#app`.

### Header Structure

The `.brand` div with text "MIROFISH" is duplicated across FOUR view files:
- `frontend/src/views/MainView.vue` (line 6)
- `frontend/src/views/SimulationView.vue` (line 6)
- `frontend/src/views/SimulationRunView.vue` (line 6)
- `frontend/src/views/ReportView.vue` (line 6)

All four use identical `<div class="brand">MIROFISH</div>` markup. There is no shared header component. The planner must update all four locations.

Additionally:
- `Home.vue` has `<div class="nav-brand">MIROFISH</div>` (different class name, separate navbar)
- `index.html` has `<title>MiroFish - Predict Anything</title>`
- `index.html` has `<meta name="description" content="MiroFish - Swarm Intelligence Prediction Engine" />`

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Font self-hosting | Manual @font-face + woff2 downloads | `@fontsource/geist-sans` npm package | Handles all font files, weights, and CSS automatically |
| Dark theme toggle | Custom theme switching system | Not needed — single dark theme only | Phase scope is replace-not-toggle |
| Color utility functions | Custom HSL helpers | Native CSS `hsl()` function | CSS natively handles HSL; no runtime computation needed |

---

## Common Pitfalls

### Pitfall 1: CSS Vars Won't Override Scoped Hardcoded Values
**What goes wrong:** You define `--primary` in `:root`, but component buttons still show `#000000` because the scoped `background: #000` in `.action-btn` takes specificity precedence over any inherited var.
**Why it happens:** CSS custom properties only help when components are already written to USE them (`background: var(--primary)`). Defining the vars does not retroactively replace hardcoded values.
**How to avoid:** After defining the token system, do a targeted audit of every component's `<style scoped>` block and replace hardcoded color values with `var(--token-name)`.
**Warning signs:** After adding `:root` vars, visually nothing changes — this is expected and correct; it means the component audit hasn't been done yet.

### Pitfall 2: Home.vue `:root` Vars Will Be Overridden or Conflict
**What goes wrong:** `Home.vue` defines `--black`, `--white`, `--orange`, `--border`, `--font-mono`, `--font-sans` in its scoped `:root`. The `--border` name conflicts with the Slater Consulting `--border` token.
**Why it happens:** Vue scoped styles emit `:root` blocks without data-v scoping, making them truly global — the last loaded stylesheet wins.
**How to avoid:** Remove or replace the `:root` block in `Home.vue`'s `<style scoped>` during the component audit. Replace all `var(--orange)` references in `Home.vue` with `var(--primary)` or `var(--accent)`.

### Pitfall 3: D3 Graph Colors Are in JavaScript, Not CSS
**What goes wrong:** `GraphPanel.vue` assigns colors via D3 inline JS (e.g., `.attr('stroke', '#C0C0C0')`, `colors = ['#FF6B35', '#004E89', ...]`). These won't respond to CSS variable changes.
**Why it happens:** D3 manipulates SVG attributes directly — SVG attribute `stroke` is not a CSS property that inherits custom properties by default.
**How to avoid:** Decide scope: R2.4 says "components use new palette consistently" but the graph is a D3 visualization with a distinct aesthetic purpose. Recommend updating the D3 color palette array and key stroke colors to navy/blue values, but not going to full CSS var integration for the graph.
**Warning signs:** Graph nodes/links still show orange or white on a dark background after theming all other components.

### Pitfall 4: SVG Spinner Colors Are Hardcoded in Template HTML
**What goes wrong:** `Step4Report.vue` has inline SVG with `stroke="#E5E7EB"` and `stroke="#4B5563"` in the template HTML (not in `<style>`). These won't be caught by a CSS audit.
**Why it happens:** Inline SVG attributes bypass the CSS cascade entirely.
**How to avoid:** During component audit, grep for `stroke="#` and `fill="#` in template sections (not just `<style>` blocks).

### Pitfall 5: Font Declaration Duplication
**What goes wrong:** Multiple components redeclare `font-family: 'JetBrains Mono', monospace` or `font-family: 'Space Grotesk', ...`. After adding Geist Sans as the base body font, these inline declarations will override it for their subtrees.
**Why it happens:** Each component styles its own font explicitly.
**How to avoid:** The body font declaration in `App.vue`/`style.css` establishes the default. Per-component `font-family` declarations for monospace elements (code, logs, step numbers) should be kept — they're intentional. Only the `font-family: 'Space Grotesk'` and `font-family: 'Noto Sans SC'` declarations need to be removed or replaced.

### Pitfall 6: Step3Simulation.vue Has Its Own CSS Variable Block
**What goes wrong:** `Step4Report.vue` (the report panel) defines local CSS vars like `--wf-border`, `--wf-active-bg`, `--wf-active-border`, `--wf-active-dot`, `--wf-done-bg`, etc. These are workflow state colors that need to be updated to match the dark theme.
**Why it happens:** Component-level CSS vars were used for the workflow timeline, separate from any global system.
**How to avoid:** Update these local vars to use values from the global token set or new dark-theme appropriate values.

---

## Code Examples

### CSS Token Definition (style.css — to create)
```css
/* frontend/src/style.css */
/* Slater Consulting brand tokens */
:root {
  --background:        hsl(210, 57%, 11%);
  --foreground:        hsl(220, 33%, 97%);
  --primary:           hsl(217, 75%, 47%);
  --primary-foreground: hsl(0, 0%, 100%);
  --secondary:         hsl(213, 40%, 18%);
  --secondary-foreground: hsl(220, 33%, 97%);
  --accent:            hsl(213, 75%, 60%);
  --muted-foreground:  hsl(213, 20%, 60%);
  --border:            hsl(213, 30%, 22%);
  --card:              hsl(213, 50%, 14%);
}
```

### App.vue Global Styles Update
```css
/* App.vue <style> — update existing block */
#app {
  font-family: 'Geist Sans', 'Inter', system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
  color: var(--foreground);
  background-color: var(--background);
}
```

### Header Brand Text Update (all 4 view files + Home.vue)
```html
<!-- Before (in MainView.vue, SimulationView.vue, SimulationRunView.vue, ReportView.vue) -->
<div class="brand" @click="router.push('/')">MIROFISH</div>

<!-- After -->
<div class="brand" @click="router.push('/')">Slater Consulting</div>
```

```html
<!-- Home.vue navbar -->
<!-- Before -->
<div class="nav-brand">MIROFISH</div>
<!-- After -->
<div class="nav-brand">Slater Consulting</div>
```

### index.html Updates
```html
<!-- Update title -->
<title>MiroFish SIPE — Slater Consulting</title>

<!-- Replace Google Fonts with Geist Sans (if NOT using @fontsource) -->
<!-- Remove: Inter, Space Grotesk, Noto Sans SC imports -->
<!-- Keep: JetBrains Mono (used for code/mono elements throughout) -->
<!-- Add if CDN route: Geist Sans from Google Fonts -->
```

### Key Color Replacements Per Component

#### All components: badge.processing / active states
```css
/* Before */
.badge.processing { background: #FF5722; color: #FFF; }
.step-card.active { border-color: #FF5722; }
.status-indicator.processing .dot { background: #FF5722; }
/* After */
.badge.processing { background: var(--primary); color: var(--primary-foreground); }
.step-card.active { border-color: var(--primary); }
.status-indicator.processing .dot { background: var(--primary); }
```

#### Components: card backgrounds
```css
/* Before */
.step-card { background: #FFF; border: 1px solid #EAEAEA; }
.workbench-panel { background-color: #FAFAFA; }
/* After */
.step-card { background: var(--card); border: 1px solid var(--border); }
.workbench-panel { background-color: var(--background); }
```

#### Components: action buttons (primary CTA)
```css
/* Before */
.action-btn { background: #000; color: #FFF; }
/* After */
.action-btn { background: var(--primary); color: var(--primary-foreground); }
```

#### Home.vue: orange accent replacements
```css
/* Before */
.orange-tag { background: var(--orange); }    /* var(--orange) = #FF4500 */
.start-engine-btn:hover { background: var(--orange); }
/* After */
.orange-tag { background: var(--primary); }
.start-engine-btn:hover { background: var(--accent); }
```

---

## Complete Hardcoded Color Audit

### Files Requiring Style Changes

| File | Hardcoded Colors Found | Scope |
|------|----------------------|-------|
| `App.vue` | `color: #000000`, `background-color: #ffffff`, scrollbar `#000000/#333333/#f1f1f1` | Global `<style>` |
| `views/Home.vue` | `--orange: #FF4500`, `--black: #000`, `--white: #FFF`, `--border: #E5E5E5`, multiple component-level colors | Scoped + `:root` |
| `views/MainView.vue` | `background: #FFF`, `border: #EAEAEA`, `#FF5722` (processing dot), `#4CAF50` (completed), `#F44336` (error) | Scoped |
| `views/SimulationView.vue` | Same header/status pattern as MainView | Scoped |
| `views/SimulationRunView.vue` | Same header/status pattern as MainView | Scoped |
| `views/ReportView.vue` | Same header/status pattern as MainView | Scoped |
| `components/Step1GraphBuild.vue` | `#FAFAFA`, `#FFF`, `#EAEAEA`, `#FF5722` (active/processing/spinner), `#E8F5E9`/`#2E7D32` (success badge), `#000` (buttons/logs) | Scoped |
| `components/Step2EnvSetup.vue` | `#FF5722` (active border, spinner), `#1A936F` (completed state), `#000/#FFF` buttons | Scoped |
| `components/Step3Simulation.vue` | `#1A936F` (completed), `#000/#FFF` buttons, `#EAEAEA` borders | Scoped |
| `components/Step4Report.vue` | Local `--wf-*` vars using `#1F2937`, `#10B981`, `#E5E7EB`; SVG inline strokes; tool color strings ('purple', 'blue', etc.) | Scoped + local vars |
| `components/GraphPanel.vue` | D3 JS color array `['#FF6B35', '#004E89', ...]`, SVG stroke attributes | JS inline |

### Files NOT Requiring Style Changes
| File | Reason |
|------|--------|
| `components/HistoryDatabase.vue` | Not inspected yet — plan should include an audit pass |
| `components/Step5Interaction.vue` | Not inspected yet — plan should include an audit pass |
| All `views/*.vue` router/script logic | No visual impact |

---

## Environment Availability

Step 2.6: No external tool dependencies for this phase. All changes are CSS/HTML/JS edits to existing files. The only new dependency would be `@fontsource/geist-sans` (npm package — available on npm registry).

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js / npm | @fontsource install | Already in project | 20 | Google Fonts CDN |
| @fontsource/geist-sans | R2.2 font | Not yet installed | Latest | Google Fonts CDN for Geist Sans |

**Note on Google Fonts CDN for Geist Sans:** Geist Sans is available on Google Fonts (added 2024). CDN route avoids adding an npm dependency but introduces a network dependency in Docker builds. Either approach works — `@fontsource` is preferred per Slater Consulting SaaS convention.

---

## Validation Architecture

No automated test suite exists for this project (Phase BACKLOG.3). Visual testing is manual:

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Command | Notes |
|--------|----------|-----------|---------|-------|
| R2.1 | CSS custom properties define Slater palette | Manual visual + grep | `grep -r "var(--primary)" frontend/src/` | Check vars are used |
| R2.2 | Geist Sans renders in browser | Manual visual | Dev server inspection | Check computed font in browser devtools |
| R2.3 | Header shows "Slater Consulting" text | Manual visual | Open http://localhost:5173 | Verify all 5 header locations |
| R2.4 | Components consistent with brand | Manual visual screenshot | Full app walkthrough | Check all 5 workflow steps |

### Sampling Approach
- After each wave: `npm run dev` in `frontend/` and visually verify the changed components
- Phase gate: Walkthrough all 5 workflow steps, screenshot comparison against brand reference

---

## Open Questions

1. **Favicon update (R2.3 sub-item)**
   - What we know: `index.html` links `/icon.png` — file exists at `frontend/public/icon.png`
   - What's unclear: Whether to replace with a text-based SVG favicon or keep the existing MiroFish icon
   - Recommendation: Planner should default to keeping `icon.png` unless a Slater Consulting favicon asset is explicitly provided. R2.3 says "favicon updated to match brand" — if no brand favicon exists, use a dark navy solid square or defer.

2. **Green success badges (#E8F5E9 / #2E7D32 and #10B981)**
   - What we know: Step1GraphBuild and Step4Report use green for "Completed" states. Green is semantically appropriate for success but clashes with the navy theme.
   - What's unclear: Whether to replace with a blue-toned success badge or keep green as a functional indicator
   - Recommendation: R2.4 says "no red/green clashing with theme" — replace with `--accent` (the lighter blue `hsl(213, 75%, 60%)`) for completed states, which fits the palette.

3. **D3 graph color palette**
   - What we know: `GraphPanel.vue` uses a 10-color palette for entity type nodes — these are deliberately distinct colors for visual differentiation of node types.
   - What's unclear: Whether R2.4 applies to the D3 graph (which has a different design requirement — legibility of distinct types — than UI chrome elements)
   - Recommendation: Update the D3 color palette to a dark-theme-aware set (e.g., blues, purples, teals that work on a dark background), but do not attempt to CSS-var-ify D3 inline attributes.

4. **`Step5Interaction.vue` and `HistoryDatabase.vue`**
   - Not inspected — planner should include these in the component audit wave.

---

## Sources

### Primary (HIGH confidence)
- Direct file inspection: `frontend/src/App.vue` — confirmed no CSS vars, hardcoded `#000000`/`#FFFFFF`
- Direct file inspection: `frontend/src/views/Home.vue` — confirmed `:root` block with `--orange: #FF4500`
- Direct file inspection: `frontend/src/views/MainView.vue` — confirmed 4-view header duplication pattern
- Direct file inspection: `frontend/src/components/Step1GraphBuild.vue` — confirmed `#FF5722` orange accent usage
- Direct file inspection: `frontend/index.html` — confirmed Google Fonts CDN, no Geist Sans, `icon.png` favicon
- Direct file inspection: `frontend/package.json` — confirmed no @fontsource dependency present
- Direct file inspection: `Slater Consulting SaaS/src/index.css` — confirmed exact token values and @fontsource usage

### Secondary (MEDIUM confidence)
- Vue 3 scoped styles behavior with `:root` — standard Vue behavior (CSS custom properties defined in `:root` inside scoped blocks are globally accessible since `:root` cannot be scoped)

---

## Metadata

**Confidence breakdown:**
- Current color system: HIGH — inspected all key files directly
- Token values: HIGH — copied verbatim from reference `index.css`
- Header locations: HIGH — confirmed in all view files
- Component color inventory: HIGH for inspected files; MEDIUM for Step5Interaction.vue and HistoryDatabase.vue (not inspected)
- Font loading: HIGH — confirmed package.json has no @fontsource, index.html uses Google Fonts CDN

**Research date:** 2026-03-26
**Valid until:** 2026-04-26 (stable codebase, no fast-moving dependencies)

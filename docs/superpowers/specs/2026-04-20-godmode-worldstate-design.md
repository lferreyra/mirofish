# God Mode + World State — Minimal v1 Design Specification

**Date:** 2026-04-20
**Builds on:** `2026-03-26-narrative-layer-design.md` (sections 5–6)
**Target:** Author-controlled story intervention + world grounding
**Scope:** 3 God Mode actions + 3 World State features, file-based only

---

## 1. Problem

The Narrative Layer generates prose from OASIS simulation output, but the author has no way to intervene mid-story or ground scenes in a coherent world. This is a creative platform, not a passive spectator tool — authors need levers.

**v1 goal:** Ship the three highest-leverage intervention levers and the three highest-leverage world grounding primitives, without modifying the OASIS simulation engine.

---

## 2. Scope

### In scope
**God Mode interventions (3):**
1. **Inject world event** — append a user-described event to the world event log; subsequent prose generations reference it
2. **Modify character emotional state** — directly set emotion values in `characters.json`
3. **Kill character** — mark a character as `status: "dead"`; filtered from future translations

**World State (3):**
1. **Locations** — named places with descriptions; characters can have a current `location`
2. **World rules** — list of background rules / constraints (genre, laws, era)
3. **Event log** — chronological record of world-level events, populated automatically by God Mode event injections

### Explicitly out of scope (deferred to v2+)
- Agent-side event propagation (the OASIS simulation doesn't "see" injected events — only the prose layer does)
- World rule changes mid-simulation via OASIS prompt injection
- Factions, resources, timeline branching
- Force action, resurrect character, time skip

### Why file-based only
The existing OASIS subprocess has no `INJECT_CONTEXT` IPC command. Adding one requires touching the OASIS runner scripts, which introduces simulation coupling we don't need for creative storytelling. v1 God Mode is a **story-layer intervention system** — it shapes what the author reads, not what agents do. The author injects an earthquake; the next prose paragraph starts "A tremor ran through the city…" The agents keep posting about whatever they were already posting about. This is a feature, not a bug: it means authors can introduce "unreliable narrator" events that exist only in the prose.

---

## 3. Architecture

### 3.1 New files

**Backend services:**
| File | Responsibility |
|---|---|
| `backend/app/services/narrative/world_state.py` | CRUD for world_state.json (locations, rules, event log) |
| `backend/app/services/narrative/god_mode.py` | 3 intervention handlers; writes to world_state and characters |
| `backend/tests/test_world_state.py` | Unit tests for world CRUD |
| `backend/tests/test_god_mode.py` | Unit tests for interventions |

**Backend API (modifies existing):**
| File | Change |
|---|---|
| `backend/app/api/narrative.py` | +6 endpoints (3 world, 3 god mode) |

**Backend translator (modifies existing):**
| File | Change |
|---|---|
| `backend/app/services/narrative/narrative_translator.py` | Extend prompt to surface world rules, recent events, character locations; filter dead characters |

**Frontend:**
| File | Responsibility |
|---|---|
| `frontend/src/api/narrative.js` | +6 named exports for new endpoints |
| `frontend/src/views/WorldBuilderView.vue` | Locations + rules + event log UI |
| `frontend/src/views/GodModeView.vue` | 3 action forms |
| `frontend/src/router/index.js` | +2 routes |

### 3.2 Data model

New file per simulation: `uploads/simulations/{sim_id}/narrative/world_state.json`

```json
{
  "sim_id": "sim_abc123",
  "rules": [
    "The kingdom is in civil war",
    "Magic is feared but not forbidden",
    "Winter will arrive in 10 rounds"
  ],
  "locations": {
    "iron_tower": {
      "id": "iron_tower",
      "name": "The Iron Tower",
      "description": "A brutal spire of black stone at the city's heart."
    },
    "market": {
      "id": "market",
      "name": "The Old Market",
      "description": "Narrow stalls under fraying canvas. Always crowded."
    }
  },
  "event_log": [
    {
      "id": "evt_001",
      "round": 3,
      "type": "god_mode_injection",
      "description": "A stranger arrived at the market, carrying a sealed letter.",
      "injected_at": "2026-04-20T14:22:00Z"
    }
  ]
}
```

**Character schema extension** (`characters.json`) — adds two optional fields:

```json
{
  "id": "1",
  "name": "Elena",
  "emotional_state": {...},
  "status": "alive",          // NEW — "alive" | "dead"
  "location": "iron_tower"    // NEW — optional, references world_state.locations
}
```

Existing characters without these fields default to `status: "alive"` and no location — backward compatible.

### 3.3 API endpoints

All under `/api/narrative/*` prefix (reusing existing `narrative_bp`).

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/world/<sim_id>` | Return full world_state.json |
| `POST` | `/world/<sim_id>/rules` | Set world rules (body: `{rules: [string]}`) |
| `POST` | `/world/<sim_id>/locations` | Upsert a location (body: `{id, name, description}`) |
| `POST` | `/godmode/<sim_id>/inject-event` | Inject a world event (body: `{description, round?}`) |
| `POST` | `/godmode/<sim_id>/modify-emotion` | Set emotion values (body: `{character_id, emotions: {anger: 0.8, ...}}`) |
| `POST` | `/godmode/<sim_id>/kill` | Mark character dead (body: `{character_id}`) |

---

## 4. God Mode handlers

### 4.1 Inject event
```python
def inject_event(sim_dir: str, description: str, round_num: int | None = None) -> dict:
    """Append a new event to world_state.event_log.

    If round_num is None, uses current round (last translated beat's round + 1,
    or 1 if no beats yet).
    """
```
- Generates unique `id = evt_{n}` where n is `len(event_log) + 1`
- Returns the event dict

### 4.2 Modify emotion
```python
def modify_emotion(sim_dir: str, character_id: str, emotions: dict[str, float]) -> dict:
    """Overwrite specified emotion values for a character.

    Clamps to [0.0, 1.0]. Only modifies emotions named in the input dict;
    unspecified emotions keep their current values.
    """
```
- Reads `characters.json`, finds character by `id`, applies overwrites
- Raises if character not found

### 4.3 Kill character
```python
def kill_character(sim_dir: str, character_id: str) -> dict:
    """Mark character as dead. Future translations ignore their actions."""
```
- Sets `status = "dead"` on the target character
- Translation pipeline filters dead characters from the characters list passed to LLM prompt, and ignores any actions with matching agent names

---

## 5. Translator prompt extension

Current prompt has substitution fields: `{tone}`, `{characters}`, `{actions}`, `{previous}`.

Add 3 new fields: `{world_rules}`, `{world_events}`, `{world_locations}`.

**New prompt sections inserted before "Events this round":**

```
World grounding:
  Rules: {world_rules}
  Recent events: {world_events}
  Known locations: {world_locations}
```

- `{world_rules}` is a bulleted list joined with `; `
- `{world_events}` is the last 3 events from `event_log`, each as `"(Round N) description"`
- `{world_locations}` is a `name — description` list, capped at 5

The prompt also gets one new instruction in the CINEMATIC DETAIL section:

```
- If a character has a known location, root the scene there.
- If a recent world event is listed, weave it in OR acknowledge its aftermath — do not ignore it.
```

### 5.1 Filtering dead characters

In `translate_round`, before building `characters` and `actions` lists:

```python
alive = {c["name"] for c in characters if c.get("status", "alive") != "dead"}
characters = [c for c in characters if c["name"] in alive]
actions = [a for a in actions if a.get("agent_name") in alive]
```

Dead characters are invisible to the LLM — no prose is generated about them unless the event log contains their death.

---

## 6. Frontend

### 6.1 GodModeView.vue

Three card-style forms, visually distinct:

```
┌──────────────────────────────────┐
│  ⚡ Inject World Event           │
│  [textarea: event description]   │
│  [input: round (optional)]       │
│  [Inject button]                 │
│  Last 3 events shown below       │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│  💭 Modify Character Emotions    │
│  [select: character dropdown]    │
│  [6 sliders: anger/fear/joy/...] │
│  [Apply button]                  │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│  ☠ Kill Character                │
│  [select: character dropdown]    │
│  [Confirm checkbox] [Kill button]│
│  Warning: removes from future    │
│  story. Cannot be undone in v1.  │
└──────────────────────────────────┘
```

Uses existing `CharacterCard.vue` for selection preview.

### 6.2 WorldBuilderView.vue

Three sections:

1. **Rules** — editable textarea, one rule per line, Save button
2. **Locations** — list of existing locations + "Add location" form
3. **Event log** — read-only scrollable list (for now; events are added only via God Mode)

### 6.3 Routes

Added to `frontend/src/router/index.js`:

```javascript
{ path: '/godmode/:simulationId', name: 'GodMode', component: GodModeView, props: true },
{ path: '/world/:simulationId', name: 'World', component: WorldBuilderView, props: true }
```

### 6.4 Navigation

A small footer added to `StoryTimelineView.vue` linking to the two new views:

```
Story | Characters | God Mode | World
```

---

## 7. Error handling

- **Missing character**: API returns 404 with `{"error": "character not found"}`
- **Missing simulation**: API returns 404 (reuses existing pattern from Task 7)
- **Invalid emotion name**: silently ignored (extra emotion keys don't break anything; they just don't affect state)
- **Inject event before translation starts**: event is stored with `round: 0` and included in the first beat's prompt

---

## 8. Testing

**Unit tests** (`tests/test_world_state.py`):
- `test_world_state_empty_on_fresh_sim`
- `test_add_location_persists`
- `test_set_rules_replaces_previous`
- `test_append_event_auto_ids`

**Unit tests** (`tests/test_god_mode.py`):
- `test_inject_event_appends_to_log`
- `test_modify_emotion_clamps_and_preserves_others`
- `test_kill_character_sets_status`
- `test_kill_character_not_found_raises`

**Integration** (extend `test_narrative_e2e.py`):
- Inject an event between round 1 and round 2, verify the event appears in the round-2 prompt context
- Kill a character between rounds, verify their actions are skipped in the next translation

---

## 9. User contribution points

Same learning-mode pattern as before — two places the author's creative judgment matters more than an LLM's guess.

### 9.1 Event injection prompt enforcement

When God Mode injects an event, the prose prompt will include it in "Recent events." The prompt currently says "weave it in OR acknowledge its aftermath — do not ignore it." User decides **how strong** this instruction should be:

- **Soft**: "consider referencing the event if it fits"
- **Medium**: current default — "weave it in OR acknowledge its aftermath"
- **Hard**: "the opening line of this passage MUST reference the most recent world event"

Marked as `EVENT_ENFORCEMENT_STRENGTH` constant in `narrative_translator.py`.

### 9.2 Location schema

Whether locations need fields beyond `name + description`. Options:
- **Minimal** (default): just `name + description`
- **Cinematic**: add `atmosphere` (a mood phrase like "oppressive silence, dust motes in shafts of light")
- **Temporal**: add `time_of_day` ("dusk", "midnight")
- **Full**: all of the above

Marked clearly in `world_state.py` as scaffolded default, with a TODO comment pointing to user contribution.

---

## 10. Non-goals

- Mid-simulation OASIS prompt injection (deferred to v2)
- Resurrection, time skip, forced action
- Faction system, resource system
- Location transitions (characters moving between locations during a round) — v1 locations are static per-character
- Bulk intervention (applying to multiple characters at once)
- Undo / history — God Mode actions are one-way in v1

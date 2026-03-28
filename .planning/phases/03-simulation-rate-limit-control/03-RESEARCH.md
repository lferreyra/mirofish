# Phase 3: Simulation Rate Limit Control — Research

**Researched:** 2026-03-28
**Domain:** Python async retry/throttle, Flask REST endpoints, Vue 3 collapsible UI, localStorage persistence
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Rate limit settings are injected into `simulation_config.json` before subprocess launch. `SimulationRunner.start_simulation()` merges a `rate_limit` section into the config file before spawning the subprocess. Scripts read settings from their existing config file — no new CLI args or env vars needed.
- **D-02:** `rate_limit` schema in `simulation_config.json`:
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
  `0` means unlimited for `tpm_limit` and `rpm_limit`.
- **D-03:** 429 retry logic lives in `backend/app/utils/llm_client.py` (`LLMClient.chat()` method). Covers ALL LLM call sites.
- **D-04:** Exponential backoff: `wait = min(base_delay_s * (2 ** attempt), 300)`. Fallback defaults: base=30s, max=5min, max_retries=3.
- **D-05:** TPM/RPM enforcement via token bucket in `llm_client.py`. Before each LLM call, client checks limits and sleeps if needed. `0` = no throttling.
- **D-06:** Rate limit events logged at `logger.warning` level with timestamp.
- **D-07:** Settings panel is an inline collapsible section inside `Step3Simulation.vue`, visible before a run starts. No modal.
- **D-08:** Controls: inter-turn delay slider (0–5000ms, step 100ms, default 500ms), max retries (1–10, default 3), retry base delay (seconds, default 30), TPM limit (0=unlimited), RPM limit (0=unlimited).
- **D-09:** Settings persisted to `localStorage` under key `mirofish_rate_limit_settings`. Loaded on mount, saved on any change.
- **D-10:** Settings passed to backend at simulation start — sent via config endpoint before `RunSimulationTool.start()` is called.
- **D-11:** `POST /api/simulation/{id}/config` accepts `rate_limit` object and merges into `simulation_config.json`. `GET /api/simulation/{id}/config` returns full config or rate_limit subsection (Claude's discretion on response shape).
- **D-12:** No separate config file — everything lives in `simulation_config.json`.

### Claude's Discretion

- Token bucket implementation approach (sliding window vs fixed window) — Claude can choose the simpler option.
- Whether to add a `rate_limit_settings` read on script startup (e.g., once at init vs per-call) — Claude decides.
- Error message formatting for rate limit log events.
- Whether `GET /api/simulation/{id}/config` returns the full config or just the `rate_limit` subsection.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| R3.1 | Configurable inter-turn delay (0–5000ms) injected between agent turns in all simulation loops | Read config from `rate_limit.inter_turn_delay_ms`; `asyncio.sleep(delay_ms / 1000)` after each `env.step()` call in the 3 scripts |
| R3.2 | Automatic 429 retry with exponential backoff in `LLMClient.chat()` | Wrap `_chat_openai` / `_chat_anthropic` dispatch in retry loop; catch `openai.RateLimitError` / `anthropic.RateLimitError` |
| R3.3 | Settings UI panel (collapsible, pre-run) in `Step3Simulation.vue` with localStorage persistence | `ref()` + `watch()` + `localStorage.setItem()` on change; POST to `/api/simulation/{id}/config` before `startSimulation()` |
| R3.4 | Backend `POST/GET /api/simulation/{id}/config` endpoints | New Flask routes in `simulation.py`; merge `rate_limit` object into `simulation_config.json` |
</phase_requirements>

---

## Summary

Phase 3 adds configurable LLM throttling to simulation runs. The work spans four distinct layers: (1) a centralized retry + token-bucket throttle added to `LLMClient.chat()`, (2) an inter-turn `asyncio.sleep` injected into the three simulation loop scripts after each `env.step()` call, (3) two new Flask routes that read/write the `rate_limit` section of `simulation_config.json`, and (4) a collapsible settings panel added pre-run in `Step3Simulation.vue` with localStorage persistence.

The codebase is well-structured for these changes. `LLMClient.chat()` is a single choke point that dispatches to `_chat_openai`, `_chat_anthropic`, `_chat_claude_cli`, and `_chat_codex_cli`. The retry wrapper belongs at the `chat()` dispatch level so all four providers are covered. The three simulation scripts all share an identical `for round_num in range(total_rounds):` loop pattern — the inter-turn delay drops into the same location in each. The `simulation_config.json` contract between `SimulationRunner` and the scripts already exists; the `rate_limit` section simply becomes a new key in that JSON.

**Primary recommendation:** Implement in this order: (1) backend config endpoint (unblocks frontend), (2) LLMClient retry + token bucket, (3) inter-turn sleep in scripts, (4) Vue settings panel. Each layer is independently testable.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `asyncio` (stdlib) | Python 3.8+ | `asyncio.sleep()` for inter-turn delay in async simulation loops | Already used — all 3 scripts are `async` |
| `time` (stdlib) | Python 3.x | `time.sleep()` for synchronous backoff in `LLMClient` (runs in Flask thread) | No dependency needed |
| `threading` (stdlib) | Python 3.x | Thread-local token bucket state in `LLMClient` | Already used in `simulation_runner.py` |
| `openai` SDK | already installed | Raises `openai.RateLimitError` (HTTP 429) | Already used in `_chat_openai` |
| `anthropic` SDK | already installed | Raises `anthropic.RateLimitError` (HTTP 429) | Already used in `_chat_anthropic` |
| Vue 3 `ref` / `watch` | already in project | Reactive settings state + localStorage sync | Established pattern in component |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `localStorage` (browser) | Web API | Persist rate limit settings client-side | Used on mount load + any change |
| Flask `jsonify` / `request` | already installed | New `/config` endpoints | Matches existing API pattern |

**No new dependencies required.** All stdlib and already-installed packages cover the full implementation.

---

## Architecture Patterns

### Recommended Project Structure

No new files or directories needed. All changes are edits to existing files:

```
backend/
├── app/
│   ├── utils/
│   │   └── llm_client.py          # ADD: retry loop + token bucket in chat()
│   ├── api/
│   │   └── simulation.py          # ADD: POST/GET /<id>/config routes
│   └── services/
│       └── simulation_runner.py   # ADD: rate_limit merge before subprocess launch
└── scripts/
    ├── run_twitter_simulation.py   # ADD: asyncio.sleep after env.step()
    ├── run_reddit_simulation.py    # ADD: asyncio.sleep after env.step()
    └── run_parallel_simulation.py  # ADD: asyncio.sleep after env.step() (2 loops)

frontend/
└── src/
    ├── components/
    │   └── Step3Simulation.vue     # ADD: collapsible settings panel + localStorage
    └── api/
        └── simulation.js           # ADD: updateSimulationConfig() helper
```

### Pattern 1: LLMClient Retry with Exponential Backoff

**What:** Wrap the provider dispatch in `LLMClient.chat()` with a retry loop that catches 429-class errors and sleeps with exponential backoff.

**When to use:** Any time an LLM provider returns HTTP 429 (rate limit) or a network-level equivalent.

**Key insight on exception types:**
- `openai` SDK raises `openai.RateLimitError` (subclass of `openai.APIStatusError`) for HTTP 429
- `anthropic` SDK raises `anthropic.RateLimitError` (subclass of `anthropic.APIStatusError`) for HTTP 429
- `claude-cli` and `codex-cli` providers run subprocesses — 429 manifests as non-zero `returncode` or error text in stderr. These should be wrapped with a plain `RuntimeError` catch and string-based detection.

**Example:**
```python
# In LLMClient.chat() — wraps the existing provider dispatch
def chat(self, messages, temperature=0.7, max_tokens=4096, response_format=None,
         rate_limit_config=None) -> str:
    cfg = rate_limit_config or {}
    max_retries = cfg.get("max_retries", 3)
    base_delay = cfg.get("retry_base_delay_s", 30)

    for attempt in range(max_retries + 1):
        try:
            self._check_token_bucket(cfg)  # proactive RPM/TPM check
            return self._dispatch_chat(messages, temperature, max_tokens, response_format)
        except Exception as e:
            if attempt >= max_retries or not self._is_rate_limit_error(e):
                raise
            wait = min(base_delay * (2 ** attempt), 300)
            logger.warning(
                f"[{datetime.now().isoformat()}] Rate limit hit (attempt {attempt+1}/{max_retries}). "
                f"Retrying in {wait}s. Error: {e}"
            )
            time.sleep(wait)
```

**`_is_rate_limit_error` detection:**
```python
def _is_rate_limit_error(self, exc) -> bool:
    # openai SDK
    try:
        from openai import RateLimitError as OpenAIRLE
        if isinstance(exc, OpenAIRLE):
            return True
    except ImportError:
        pass
    # anthropic SDK
    try:
        from anthropic import RateLimitError as AnthropicRLE
        if isinstance(exc, AnthropicRLE):
            return True
    except ImportError:
        pass
    # CLI providers — error text contains "429" or "rate limit"
    msg = str(exc).lower()
    return "429" in msg or "rate limit" in msg or "too many requests" in msg
```

### Pattern 2: Token Bucket (Fixed Window, Per-Minute)

**What:** In-memory counters for RPM and TPM that reset every 60 seconds. Before each call, increment and check. Sleep until window resets if over limit.

**Why fixed window over sliding window:** Simpler, zero external state, good enough for long-running simulation throttling. Sliding window requires deque with timestamps.

**Claude's discretion note:** This is the recommended approach.

```python
import threading, time

class _TokenBucket:
    def __init__(self):
        self._lock = threading.Lock()
        self._rpm_count = 0
        self._tpm_count = 0
        self._window_start = time.time()

    def check_and_consume(self, token_count: int, rpm_limit: int, tpm_limit: int):
        with self._lock:
            now = time.time()
            if now - self._window_start >= 60.0:
                self._rpm_count = 0
                self._tpm_count = 0
                self._window_start = now

            if rpm_limit > 0 and self._rpm_count >= rpm_limit:
                sleep_for = 60.0 - (now - self._window_start)
                return max(0.0, sleep_for)
            if tpm_limit > 0 and self._tpm_count + token_count > tpm_limit:
                sleep_for = 60.0 - (now - self._window_start)
                return max(0.0, sleep_for)

            self._rpm_count += 1
            self._tpm_count += token_count
            return 0.0
```

`LLMClient` creates one `_TokenBucket` per instance (instantiated once per simulation session). The `check_and_consume()` return value is the sleep duration — caller sleeps then retries the bucket check.

**Token count estimation:** For calls where exact token count is unknown before the call, use a conservative estimate (e.g., `max_tokens` param as a ceiling). For precise TPM enforcement, token count could come from the response usage field after the call — but that is post-hoc. Pre-call estimation is simpler and sufficient for rate limiting purposes.

### Pattern 3: Config Injection in `start_simulation()`

**What:** Read `simulation_config.json`, merge the `rate_limit` section, write it back before spawning the subprocess.

**Injection point:** Lines 340–347 in `simulation_runner.py` — config is loaded from file. Insert merge immediately after load:

```python
# After: with open(config_path, 'r', ...) as f: config = json.load(f)
# Add:
rate_limit_section = cls._pending_rate_limit.get(simulation_id, {})
if rate_limit_section:
    config["rate_limit"] = rate_limit_section
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
```

**Simpler alternative (no class-level pending dict):** The `POST /api/simulation/{id}/config` endpoint writes `rate_limit` into the JSON file directly. `start_simulation()` needs no change — it already reads the file. The frontend calls the config POST endpoint first, then calls `/start`. This is the cleanest approach and avoids any coordination state.

**Recommended:** Use the "write first, start second" approach from the frontend. No changes needed in `start_simulation()` beyond reading whatever is already in the config file.

### Pattern 4: Inter-Turn Delay in Simulation Loops

**What:** After each `await self.env.step(actions)` call, read `rate_limit.inter_turn_delay_ms` from config and sleep.

**All three injection points:**

| Script | Loop location | Code to add after `env.step()` |
|--------|--------------|-------------------------------|
| `run_twitter_simulation.py` | `run()` method, line ~654 | `await asyncio.sleep(inter_turn_delay_ms / 1000)` |
| `run_reddit_simulation.py` | `run()` method, line ~643 | `await asyncio.sleep(inter_turn_delay_ms / 1000)` |
| `run_parallel_simulation.py` | `run_twitter_simulation()` function, line ~1255 AND `run_reddit_simulation()` function, line ~1428 | Same pattern, both loops |

**Config read:** Read once in the runner `__init__` or at the top of `run()`:
```python
rate_limit_config = self.config.get("rate_limit", {})
inter_turn_delay_ms = rate_limit_config.get("inter_turn_delay_ms", 500)
inter_turn_delay_s = inter_turn_delay_ms / 1000
```
Then `await asyncio.sleep(inter_turn_delay_s)` after each `env.step()`. If delay is 0, `asyncio.sleep(0)` still yields the event loop — no special case needed.

**Parallel script caveat:** `run_parallel_simulation.py` runs Twitter and Reddit in two separate async functions (`run_twitter_simulation` and `run_reddit_simulation`). Both must receive the `rate_limit_config` dict — pass as a parameter to each function.

### Pattern 5: Backend Config Endpoint

**What:** Two new routes added to `simulation.py` at the end of the file, before the script download route.

```python
@simulation_bp.route('/<simulation_id>/config', methods=['POST'])
def update_simulation_config(simulation_id: str):
    """Merge rate_limit section into simulation_config.json."""
    data = request.get_json() or {}
    rate_limit = data.get("rate_limit")
    if not rate_limit:
        return jsonify({"success": False, "error": "rate_limit required"}), 400

    sim_dir = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id)
    config_path = os.path.join(sim_dir, "simulation_config.json")

    if not os.path.exists(config_path):
        return jsonify({"success": False, "error": "Simulation config not found"}), 404

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    config["rate_limit"] = rate_limit
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    return jsonify({"success": True, "data": {"rate_limit": rate_limit}})
```

**GET response shape (Claude's discretion):** Return the full config — reuses the `get_simulation_config` logic already present at line 860. Avoid a second code path. The existing `GET /<id>/config` at line 860 already does this. The new POST is the only truly new route needed.

**Important:** The existing `GET /api/simulation/{id}/config` at line 860 already returns the full config via `SimulationManager.get_simulation_config()`. There is no need to add a new GET route — the existing one suffices. Only the `POST /<id>/config` is new.

### Pattern 6: Vue Settings Panel (Collapsible)

**What:** An inline collapsible `<div>` inserted into the template of `Step3Simulation.vue`, visible when `phase === 0` (simulation not yet started).

**State refs needed:**
```js
const showRateLimitSettings = ref(false)
const rateLimitSettings = ref({
  inter_turn_delay_ms: 500,
  max_retries: 3,
  retry_base_delay_s: 30,
  tpm_limit: 0,
  rpm_limit: 0
})

const RATE_LIMIT_STORAGE_KEY = 'mirofish_rate_limit_settings'
```

**Load on mount:**
```js
onMounted(() => {
  const saved = localStorage.getItem(RATE_LIMIT_STORAGE_KEY)
  if (saved) {
    try {
      rateLimitSettings.value = { ...rateLimitSettings.value, ...JSON.parse(saved) }
    } catch (e) { /* ignore */ }
  }
})
```

**Save on change:**
```js
watch(rateLimitSettings, (val) => {
  localStorage.setItem(RATE_LIMIT_STORAGE_KEY, JSON.stringify(val))
}, { deep: true })
```

**Send to backend before start:**
In `doStartSimulation()`, before `const res = await startSimulation(params)`, add:
```js
await updateSimulationConfig(props.simulationId, {
  rate_limit: rateLimitSettings.value
})
```
Where `updateSimulationConfig` is the new function added to `frontend/src/api/simulation.js`.

**Placement in template:** Inside `.main-content-area`, before the existing `.timeline-header` and `.timeline-feed` blocks. Show only when `phase === 0`:
```html
<div v-if="phase === 0" class="rate-limit-settings">
  <div class="settings-toggle" @click="showRateLimitSettings = !showRateLimitSettings">
    <span>Rate Limit Settings</span>
    <span class="toggle-arrow">{{ showRateLimitSettings ? '▲' : '▼' }}</span>
  </div>
  <div v-if="showRateLimitSettings" class="settings-body">
    <!-- controls here -->
  </div>
</div>
```

### Anti-Patterns to Avoid

- **Retry in `_chat_openai` / `_chat_anthropic` separately:** The retry logic would be duplicated across 4 provider methods. Put it at the `chat()` dispatch level instead.
- **Passing `rate_limit_config` as a new required `__init__` param to `LLMClient`:** This breaks all existing instantiation sites. Use an optional method parameter or a `configure_rate_limit()` method called after instantiation.
- **Reading config file on every LLM call inside scripts:** Scripts load config once at startup. Pass the `rate_limit` dict as a parameter through the call chain instead of re-reading the file.
- **Adding `asyncio.sleep` BEFORE `env.step()` instead of after:** The delay is between turns, not before the first turn.
- **Using a class-level shared `_TokenBucket` for all `LLMClient` instances:** Simulation scripts and the Flask API process are separate OS processes — no shared memory. A per-instance bucket is correct.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Detecting 429 from OpenAI | String-parsing response bodies | `openai.RateLimitError` exception class | SDK already raises typed exception; string parsing breaks on SDK updates |
| Detecting 429 from Anthropic | String-parsing response bodies | `anthropic.RateLimitError` exception class | Same as above |
| Persistent settings storage | Custom backend storage for UI prefs | `localStorage` | Already decided in D-09; zero backend overhead |
| Token counting before call | Full tokenizer integration | Conservative `max_tokens` ceiling | Exact pre-call tokenization requires a tokenizer import and is overkill for rate limiting |

---

## Common Pitfalls

### Pitfall 1: `LLMClient` Instantiation Sites Not Receiving Rate Limit Config

**What goes wrong:** `LLMClient.chat()` gains an optional `rate_limit_config` parameter, but callers in simulation scripts pass no such argument, so retry/throttle never activates.

**Why it happens:** The scripts instantiate `LLMClient` (or use it indirectly via camel-ai/OASIS). The `rate_limit_config` must flow from the config file to the `LLMClient` call site.

**How to avoid:** In `run_twitter_simulation.py` and `run_reddit_simulation.py`, the OASIS `LLMAction()` triggers LLM calls via camel-ai, NOT via `mirofish`'s `LLMClient`. The `LLMClient` in `llm_client.py` is used by the Flask backend services (graph build, profile generation, report agent) — NOT by the OASIS simulation scripts.

**Critical implication:** The inter-turn delay (`asyncio.sleep` after `env.step()`) is the primary rate control mechanism available inside the simulation scripts. The `LLMClient` retry/throttle protects the Flask API layer, but the OASIS scripts use camel-ai's own HTTP client. If retry is needed in OASIS, it must be handled differently (see Open Questions).

**Warning signs:** If you add retry logic to `LLMClient.chat()` but the simulation still crashes on 429, it means the 429 is coming from inside OASIS/camel-ai, not `LLMClient`.

### Pitfall 2: Writing JSON Mid-Run

**What goes wrong:** If `POST /api/simulation/{id}/config` is called while a simulation is running and has the config file open, writes can corrupt the JSON.

**Why it happens:** `simulation_config.json` is opened at start by the subprocess; the Flask API writes concurrently.

**How to avoid:** The config endpoint is only called pre-run (D-10 states settings are sent at simulation start). The UI should disable the config POST button once phase becomes 1. Enforce this in the Vue component with a `v-if="phase === 0"` guard on the settings panel.

### Pitfall 3: `asyncio.sleep` in Synchronous Context

**What goes wrong:** If the delay is mistakenly inserted into synchronous code (e.g., `_TokenBucket.check_and_consume`), `asyncio.sleep` cannot be awaited in that context.

**Why it happens:** `LLMClient` runs in Flask's synchronous request thread. Simulation scripts run in an async event loop.

**How to avoid:** Use `time.sleep()` in `LLMClient` (synchronous Flask context). Use `await asyncio.sleep()` in simulation scripts (async context). Never mix them.

### Pitfall 4: `run_parallel_simulation.py` Has Two Separate Loops

**What goes wrong:** Developer adds inter-turn delay to only one platform loop, missing the other.

**Why it happens:** `run_parallel_simulation.py` has two separate async functions: `run_twitter_simulation()` (loop at line ~1229) and `run_reddit_simulation()` (loop at line ~1428). Both must receive and apply the delay.

**How to avoid:** In the research, both loop locations are documented. The plan should call out both explicitly.

### Pitfall 5: Route Conflict with Existing `GET /<id>/config`

**What goes wrong:** Adding `POST /<id>/config` conflicts with the existing `GET /<id>/config` if Flask routing is set up incorrectly.

**Why it happens:** Flask can register the same URL pattern for multiple methods on the same route handler or on separate functions.

**How to avoid:** Use `methods=['POST']` only on the new route. The existing GET handler at line 860 remains unchanged. Flask route matching is method-specific — both can coexist at the same URL.

---

## Code Examples

### Correct Import for Typed 429 Exceptions
```python
# In llm_client.py — safe import guards (packages may not always be installed)
try:
    from openai import RateLimitError as _OpenAIRateLimitError
except ImportError:
    _OpenAIRateLimitError = None

try:
    from anthropic import RateLimitError as _AnthropicRateLimitError
except ImportError:
    _AnthropicRateLimitError = None
```

### Minimal asyncio.sleep Injection (Twitter script — same pattern for Reddit)
```python
# In run_twitter_simulation.py, TwitterSimulationRunner.run()
# Read once before the loop:
rate_limit_config = self.config.get("rate_limit", {})
inter_turn_delay_s = rate_limit_config.get("inter_turn_delay_ms", 500) / 1000.0

# Inside for loop, after existing env.step():
await self.env.step(actions)
if inter_turn_delay_s > 0:
    await asyncio.sleep(inter_turn_delay_s)
```

### localStorage Settings Load/Save (Vue 3)
```js
const RATE_LIMIT_STORAGE_KEY = 'mirofish_rate_limit_settings'

onMounted(() => {
  const saved = localStorage.getItem(RATE_LIMIT_STORAGE_KEY)
  if (saved) {
    try {
      Object.assign(rateLimitSettings.value, JSON.parse(saved))
    } catch (_) {}
  }
})

watch(rateLimitSettings, (val) => {
  localStorage.setItem(RATE_LIMIT_STORAGE_KEY, JSON.stringify(val))
}, { deep: true })
```

### New API Function in simulation.js
```js
/**
 * Update simulation rate limit config
 * @param {string} simulationId
 * @param {Object} data - { rate_limit: { inter_turn_delay_ms, max_retries, ... } }
 */
export const updateSimulationConfig = (simulationId, data) => {
  return service.post(`/api/simulation/${simulationId}/config`, data)
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No retry anywhere in codebase | Explicit retry with typed exception catch | Phase 3 | Simulation no longer crashes on transient rate limit |
| No inter-turn delay | Configurable `asyncio.sleep` between turns | Phase 3 | Reduces API request rate proportionally |
| No TPM/RPM enforcement | Fixed-window token bucket in `LLMClient` | Phase 3 | Proactive throttle before errors occur |

---

## Open Questions

1. **Do OASIS/camel-ai's own HTTP calls (inside `env.step()`) raise 429 errors that crash the simulation?**
   - What we know: The simulation scripts call `await self.env.step(actions)` which internally calls camel-ai's `LLMAction`. This goes through camel-ai's HTTP client, NOT `mirofish`'s `LLMClient`. If camel-ai raises a 429 inside `env.step()`, it will bubble up to the simulation loop.
   - What's unclear: Whether camel-ai's SDK has its own retry logic, and what exception type it raises on 429.
   - Recommendation: Wrap the `await self.env.step(actions)` call with a try/except in each simulation loop that catches generic `Exception`, checks for "429" or "rate limit" in the error message, and performs `await asyncio.sleep(retry_base_delay_s)` before re-running the step. This is a belt-and-suspenders approach that handles camel-ai 429s without modifying camel-ai's internals. Decide in planning whether to include this in scope or treat it as a follow-up.

2. **Token count estimation for TPM bucket**
   - What we know: `LLMClient.chat()` accepts `max_tokens` as a parameter. Actual token usage depends on input prompt length.
   - What's unclear: Whether TPM precision is important enough to require post-call adjustment.
   - Recommendation: Use `max_tokens` as a conservative ceiling for the pre-call TPM check. This overestimates TPM usage, causing slightly more conservative throttling — acceptable for this use case.

---

## Environment Availability

Step 2.6: SKIPPED — Phase is purely code/config changes. All required libraries (`openai`, `anthropic`, `asyncio`, `time`, `threading`) are already present in the project's Python environment and browser runtime.

---

## Sources

### Primary (HIGH confidence)
- Direct source code inspection: `backend/app/utils/llm_client.py` — confirmed single dispatch point, 4 provider methods, no existing retry
- Direct source code inspection: `backend/scripts/run_twitter_simulation.py` — confirmed async loop structure, `await self.env.step(actions)` at line ~654, config read pattern
- Direct source code inspection: `backend/scripts/run_reddit_simulation.py` — confirmed identical loop pattern
- Direct source code inspection: `backend/scripts/run_parallel_simulation.py` — confirmed two separate async functions with loops at ~1229 and ~1428
- Direct source code inspection: `backend/app/api/simulation.py` — confirmed existing GET /config at line 860, no existing POST /config, confirmed `start_simulation` route at line 1049
- Direct source code inspection: `frontend/src/components/Step3Simulation.vue` — confirmed `phase === 0` pre-run state, `doStartSimulation()` flow, Vue 3 Composition API patterns in use
- Direct source code inspection: `frontend/src/api/simulation.js` — confirmed `requestWithRetry` wrapper, no existing `updateSimulationConfig`
- Direct source code inspection: `backend/app/services/simulation_runner.py` lines 340–456 — confirmed config load at line 345 and subprocess spawn at line 437

### Secondary (MEDIUM confidence)
- openai Python SDK: `openai.RateLimitError` is documented as the typed exception for HTTP 429. Verified from project's existing import pattern in `llm_client.py` (`from openai import OpenAI`).
- anthropic Python SDK: `anthropic.RateLimitError` is the equivalent for Anthropic. Verified from existing import in `llm_client.py`.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are already in the project; no new installs needed
- Architecture: HIGH — based on direct code inspection of all 8 key files
- Pitfalls: HIGH for pitfalls 1–5 (directly verified from code); MEDIUM for Open Question 1 (camel-ai internals not inspected)

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable codebase, no fast-moving external dependencies)

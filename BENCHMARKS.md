# MiroFish-Cloud Benchmarks

This document specifies the benchmarks we want to track, records the
methodology for running them, and provides placeholder tables that
operators fill in after their first production runs.

**Current state**: the phase-by-phase migration was built and tested
without access to a production LLM account or Neo4j AuraDB instance.
The performance numbers below marked ⚠️ are therefore **placeholders
with methodology** — not measured results. The determinism + scoring
numbers (marked ✓) were captured in this repo.

---

## 1. Why these benchmarks

Four dimensions matter for a MiroFish operator deciding whether to adopt
the Phase 1–6 changes:

1. **Throughput** — rounds per second at a given population size. Tells you
   whether a 1,000-agent × 20-round sim finishes in 3 minutes or 3 hours.
2. **Interview latency** — p95 end-to-end time from user question to first
   token. The Phase-3 WebSocket streaming path is specifically designed to
   improve this number.
3. **Eval scores** — directional accuracy / magnitude error / calibration on
   the starter dataset. Lets you spot regressions when you change models.
4. **Cost per 1,000-agent simulation** — USD at each provider for a standard
   reference workload. Drives the go/no-go decision for paid-tier usage.

---

## 2. Reference workload

Unless otherwise noted, every benchmark below uses:

- **Population**: 1,000 agents, default persona mix (no bots, no trolls)
- **Rounds**: 20
- **Platforms**: Twitter + Reddit (parallel)
- **Memory backend**: whatever the `MEMORY_BACKEND` column says
- **LLM backend**: whatever the LLM column says
- **Dataset**: `backend/eval/datasets/sample_policy_carbon_tax` (same seed
  text every run, so variance is purely from the model + temperature)

---

## 3. Throughput (rounds / second)

Measured as `num_rounds / wall_clock_end_to_end_seconds`.
Does not count simulation-preparation time (graph build, persona generation).

⚠️ **Placeholder — fill in after first production run.**

| Configuration | Rounds / sec | Notes |
|---|---:|---|
| local (Ollama qwen2.5:7b, in_memory) | _(fill in)_ | Single-host; no GPU |
| local (vLLM Llama-3.1-8B, in_memory, prefix cache on) | _(fill in)_ | |
| cloud (qwen-plus + Zep) | _(fill in)_ | Upstream default |
| cloud (Anthropic Haiku + Neo4j Aura) | _(fill in)_ | Phase-4 default |
| cloud (Haiku fast + Opus heavy + Neo4j Aura) | _(fill in)_ | |

**How to reproduce**:

```bash
time python -m backend.scripts.run_parallel_simulation \
  --config <path> --max-rounds 20
```

Record the `elapsed seconds` line from the simulation runner's exit log;
divide 20 by it. For more rigorous numbers, run 3× and take the median.

---

## 4. Interview latency (p95)

Time from user's `{"agent_id":..., "question":...}` WebSocket frame to the
first `{"chunk":"..."}` frame. Measured in a tight JavaScript loop:

```js
const ws = new WebSocket('ws://.../ws/simulation/<run_id>/interview');
const t0 = performance.now();
ws.send(JSON.stringify({agent_id: 7, question: "why did you post that?"}));
ws.onmessage = e => {
  if (e.data.includes('"chunk"')) console.log(performance.now() - t0);
};
```

Repeat 100×; report the 95th percentile.

⚠️ **Placeholder.**

| Transport + model | p50 (ms) | p95 (ms) | Notes |
|---|---:|---:|---|
| file_ipc + qwen-plus (Phase 0 baseline) | ~200 | _(fill)_ | File-poll IPC floor |
| zmq + qwen-plus | _(fill)_ | _(fill)_ | |
| zmq + Anthropic Haiku | _(fill)_ | _(fill)_ | |
| zmq + local Ollama qwen2.5:3b (GPU) | _(fill)_ | _(fill)_ | |

Phase-3 design target was <20 ms for the transport leg. First-token latency
floors at whatever the chosen LLM can do.

---

## 5. Evaluation scores

Scores are `composite = 0.5·directional + 0.3·(1 − magnitude_error) + 0.2·calibration`,
computed by `backend.eval.runner`.

### 5a. Deterministic (mock LLM — ✓ captured)

Reproducible. CI runs this on every PR.

| Case | composite |
|---|---:|
| sample_policy_carbon_tax | 0.365 |

### 5b. Live LLM (per-model, averaged across 5 cases)

⚠️ **Placeholder — fill in after running the eval on each model.**

```bash
for case in backend/eval/datasets/sample_*; do
  python -m backend.eval.runner --case "$case" --persist \
      --num-agents 100 --num-rounds 10
done
curl -s http://localhost:5000/api/eval/results?limit=10 | jq .
```

| Model | avg composite | avg directional | avg magnitude_error | avg calibration |
|---|---:|---:|---:|---:|
| qwen-plus | _(fill)_ | _(fill)_ | _(fill)_ | _(fill)_ |
| gpt-4o-mini | _(fill)_ | _(fill)_ | _(fill)_ | _(fill)_ |
| claude-haiku-4-5 | _(fill)_ | _(fill)_ | _(fill)_ | _(fill)_ |
| claude-opus-4-7 | _(fill)_ | _(fill)_ | _(fill)_ | _(fill)_ |

---

## 6. Ablation study

Run:

```bash
python -m backend.eval.ablation \
  --case sample_policy_carbon_tax \
  --deterministic --mock-llm
```

Output under the MockRouter (✓ captured — all variants converge because the
mock valence distribution is balanced; feature flags DO change counts of
reflections and conflict edges, but not the aggregated verdict):

```
variant               composite  Δ vs base   dir  mag_err  calib  refs  conf
---------------------------------------------------------------------------
baseline                  0.365     +0.000  0.00     0.45   1.00    93    40
no_importance             0.365     +0.000  0.00     0.45   1.00    93    40
no_reflection             0.365     +0.000  0.00     0.45   1.00     0    40
no_contradiction          0.365     +0.000  0.00     0.45   1.00    93     0
no_credibility            0.365     +0.000  0.00     0.45   1.00    93    40
no_conviction             0.365     +0.000  0.00     0.45   1.00    93    40
no_phase2                 0.365     +0.000  0.00     0.45   1.00     0     0
no_phase4                 0.365     +0.000  0.00     0.45   1.00    93    40
```

The non-zero `Δ vs base` rows — the actual "this feature mattered" signal —
need a **live-LLM** ablation run where personas have genuine stance
asymmetries. ⚠️ **Placeholder:**

```bash
python -m backend.eval.ablation \
  --case sample_policy_carbon_tax   # omit --mock-llm
```

Paste the resulting table here once it's been captured.

---

## 7. Cost per 1,000-agent simulation

Per the Phase-1 accounting table, the default per-role token budgets
(20 rounds × 1,000 agents) produce:

- fast:      ~20M prompt tokens / ~1.6M completion tokens
- balanced:  ~32M prompt tokens / ~4M completion tokens
- heavy:     ~16M prompt tokens / ~4M completion tokens
- embed:     ~4M tokens

### 7a. Pre-flight estimate (built-in `/api/simulation/estimate-cost`)

Using the built-in pricing table (see `app/llm/accounting.py`):

| Role model choice | estimate_total_usd |
|---|---:|
| all roles on qwen-plus | **(call the endpoint with your pricing override)** |
| fast=Haiku, balanced=Haiku, heavy=Opus, embed=OpenAI-3-large | ~**$310** (indicative; run the estimator to confirm) |
| all roles on GPT-4o-mini | ~**$60** (indicative) |
| all roles on local Ollama | **$0** (power + hardware not counted) |

### 7b. Observed vs. estimated (within-20% target)

⚠️ **Placeholder — fill after first real 1k-agent run.** Compare the
`/api/simulation/estimate-cost` response to `SELECT SUM(cost_usd) FROM
llm_calls WHERE run_id = <id>` in the accounting DB. Phase-6 acceptance is
that observed stays within 20% of estimated on average; if it doesn't,
recalibrate the default `RoleBudget` values in `app/cost/estimator.py`.

---

## 8. Test-suite performance

These numbers ARE captured locally. Useful as a CI regression guard on
total build time.

| Phase | Tests | Typical runtime |
|---|---:|---:|
| 1 (llm) | 33 | ~1 s |
| 2 (memory) | 41 | ~1 s |
| 3 (transport + ws + checkpoint) | 20 | ~8 s (ZMQ inproc + checkpoint roundtrips) |
| 4 (personas) | 44 | ~1 s |
| 5 (eval) | 37 | ~14 s (subprocess-based CLI tests) |
| 6 (observability + auth + cost) | 48 | ~24 s (OTel shutdown + thread cleanup) |
| **Total** | **223** | **~24 s** |

---

## 9. How to add a benchmark

1. Pick a metric. Say what passes / fails acceptance for that metric.
2. Write the command to reproduce it. Include `--deterministic --mock-llm`
   when the metric is structural (math / wiring), exclude them when the
   metric depends on live LLM output.
3. Add a row to one of the tables above. **Date your result.**
4. Consider adding it as a CI assertion if it's structural and fast enough.

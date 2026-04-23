# Migrating from upstream MiroFish to MiroFish-Cloud

This guide is for existing users of `666ghj/MiroFish` (or any fork based on
it) who want to pick up the Phase 1–6 changes. It covers what changed, how
to set `BACKEND_MODE`, how to run locally, how to run in cloud, and every
new `.env` key.

If you're starting fresh, read [`README.md`](README.md) first.

---

## TL;DR

| You were… | You'll now set… |
|---|---|
| Running against Aliyun DashScope qwen-plus + Zep Cloud | Nothing — legacy `LLM_API_KEY`/`LLM_BASE_URL`/`LLM_MODEL_NAME` + `ZEP_API_KEY` are still honored. Everything routes through the new `ModelRouter` automatically. |
| Want to run fully local with no cloud creds | `BACKEND_MODE=local` + `MEMORY_BACKEND=in_memory` + `ollama serve` with `qwen2.5:3b`/`qwen2.5:7b`/`qwen2.5:14b`/`nomic-embed-text` pulled. |
| Want multi-provider routing (Haiku fast, Opus heavy, OpenAI embed) | Set `BACKEND_MODE=cloud` + the `LLM_ROLE_<role>_*` keys listed in [.env.example](.env.example). |
| Want to self-host memory instead of using Zep Cloud | `MEMORY_BACKEND=neo4j_local` or `neo4j_aura` + `NEO4J_URI`/`NEO4J_USER`/`NEO4J_PASSWORD`. |
| Want Prometheus / OTel / API-key auth | Install the Phase-6 deps and set `OTEL_EXPORTER_OTLP_ENDPOINT`, `ADMIN_TOKEN`, etc. |

---

## What changed, by phase

### Phase 1 — LLM backend abstraction

- New package [backend/app/llm/](backend/app/llm/) with `ModelRouter` that
  routes task **roles** (`fast`, `balanced`, `heavy`, `embed`) to different
  backends.
- Supported backends: `ollama` (local HTTP), `openai_compat` (OpenAI,
  Anthropic, Together, DeepInfra, Groq, Fireworks, Aliyun DashScope, any
  OpenAI-SDK-shaped endpoint), `vllm` (self-hosted).
- Per-call **token accounting** persisted to `backend/data/llm_calls.db`.
- Automatic **prefix-cache hints** for providers that support them
  (OpenAI `prompt_cache_key`, Anthropic `cache_control`).
- Retry with exponential backoff + per-role fallback chain.
- **The upstream `LLMClient` is now a back-compat shim over `ModelRouter`.**
  Existing callers continue to work with no changes.

### Phase 2 — Memory: pluggable backends + hierarchical reflection

- New package [backend/app/memory/](backend/app/memory/).
- `MemoryBackend` abstract interface with three concrete backends:
  `in_memory` (dict-based; tests + minimal local runs), `zep_cloud`
  (wraps the pre-existing Zep path), `neo4j_local` / `neo4j_aura`.
- **Hierarchical memory** (Stanford Generative Agents pattern):
  importance scoring, reflection scheduling (default every 5 rounds),
  contradiction detection with `conflict_edge` writes.
- Per-agent namespaces (`agent:<sim>:<id>`) and shared `public:<sim>:timeline`
  — cross-agent reads never traverse another agent's private partition.
- New endpoints `/api/agents/<id>/reflections|conflicts|retrieve`.

### Phase 3 — Transport + WebSocket + checkpointing

- New package [backend/app/transport/](backend/app/transport/) with a
  `Transport` / `ServerTransport` ABC pair.
- ZeroMQ (DEALER/ROUTER for commands, PUB/SUB for events) replaces the
  legacy file-poll IPC by default (`IPC_TRANSPORT=zmq`). The legacy path
  stays available as `IPC_TRANSPORT=file`.
- New WebSocket routes `/ws/simulation/<run_id>` (live event feed) and
  `/ws/simulation/<run_id>/interview` (token-by-token streaming reply,
  bypassing the subprocess round-trip).
- New package [backend/app/checkpoint/](backend/app/checkpoint/) with
  `.tar.zst` archive format (`.tar.gz` fallback). New endpoints
  `POST /api/simulation/<id>/checkpoint|restore` and
  `GET /api/simulation/<id>/checkpoints`.

### Phase 4 — Persona dynamics

- New package [backend/app/personas/](backend/app/personas/).
- `StructuredPersona` schema: Big Five traits + conviction + credibility
  + background + initial stance, serialized as JSON and injected verbatim
  into every agent prompt via `persona_system_block()`.
- `StanceInertia` counter — a high-conviction agent can't flip stance on
  a single persuasive post.
- `CredibilityWeighter` re-ranks retrieval by author credibility.
- New archetypes: `BOT` (fixed narrative), `TROLL` (reply-bomb). Enable
  via `BOT_POPULATION_PCT` / `TROLL_POPULATION_PCT` — nonzero values
  measurably change simulation outcomes.

### Phase 5 — Evaluation harness

- New package [backend/eval/](backend/eval/).
- CLI: `python -m backend.eval.runner --case <name> --deterministic --mock-llm`
  produces a numeric score; two runs in that mode are byte-identical.
- CLI: `python -m backend.eval.ablation --case <name> --deterministic --mock-llm`
  shows per-feature contribution to accuracy.
- GitHub Actions workflow runs the deterministic smoke case on every PR.
- New endpoint `GET /api/eval/results` for the dashboard.
- Five starter dataset cases under [backend/eval/datasets/](backend/eval/datasets/).

### Phase 6 — Deployment + observability

- New packages [backend/app/observability/](backend/app/observability/),
  [backend/app/auth/](backend/app/auth/), [backend/app/cost/](backend/app/cost/).
- Structured JSON logging via structlog (stdlib fallback) with
  contextvar-bound `run_id` / `agent_id` / `phase`.
- Prometheus `/metrics` endpoint with the full Phase-6 metric set.
- OpenTelemetry tracing — no-op when `OTEL_EXPORTER_OTLP_ENDPOINT` unset.
- API-key auth (`@require_api_key` decorator + admin endpoints under
  `/api/auth/keys`), per-key token/USD quotas with a rolling 30-day window.
- Pre-flight cost estimator: `POST /api/simulation/estimate-cost`.
- Helm chart under [deploy/helm/mirofish/](deploy/helm/mirofish/).

---

## Running in each mode

### Local mode — zero cloud creds required

Good for: development, testing the deterministic eval path, privacy-sensitive runs.

```bash
# 1. Install + run Ollama, pull the default models
ollama pull qwen2.5:3b
ollama pull qwen2.5:7b
ollama pull qwen2.5:14b
ollama pull nomic-embed-text

# 2. Point the backend at the local stack
cp .env.example .env
# edit .env:
#   BACKEND_MODE=local
#   MEMORY_BACKEND=in_memory     # or neo4j_local if you have Neo4j running
#   # (no LLM_API_KEY needed)

# 3. Run
pip install -r backend/requirements.txt
python -m backend.app  # or however the Flask app is launched in your setup
```

### Cloud mode — mix providers per role

```bash
# .env:
BACKEND_MODE=cloud

# Legacy single-endpoint keys still work as a fallback for unset roles
LLM_API_KEY=sk-...
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o-mini

# Override specific roles — e.g. Anthropic Haiku for fast, Opus for heavy,
# OpenAI for embeddings:
LLM_ROLE_FAST_BACKEND=openai_compat
LLM_ROLE_FAST_PROVIDER=anthropic
LLM_ROLE_FAST_MODEL=claude-haiku-4-5-20251001
LLM_ROLE_FAST_API_KEY=sk-ant-...
LLM_ROLE_FAST_BASE_URL=https://api.anthropic.com/v1

LLM_ROLE_HEAVY_BACKEND=openai_compat
LLM_ROLE_HEAVY_PROVIDER=anthropic
LLM_ROLE_HEAVY_MODEL=claude-opus-4-7
LLM_ROLE_HEAVY_API_KEY=sk-ant-...
LLM_ROLE_HEAVY_BASE_URL=https://api.anthropic.com/v1

LLM_ROLE_EMBED_BACKEND=openai_compat
LLM_ROLE_EMBED_PROVIDER=openai
LLM_ROLE_EMBED_MODEL=text-embedding-3-large
LLM_ROLE_EMBED_API_KEY=sk-...

# Memory can stay on Zep or move to Neo4j AuraDB
MEMORY_BACKEND=neo4j_aura
NEO4J_URI=neo4j+s://xxxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

### Self-hosted vLLM

```bash
# Launch vLLM with matching flags — the CLIENT cannot toggle these per-request
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Meta-Llama-3.1-70B-Instruct \
  --enable-prefix-caching \
  --speculative-model meta-llama/Llama-3.2-1B-Instruct \
  --num-speculative-tokens 4 \
  --port 8000

# .env
LLM_ROLE_HEAVY_BACKEND=vllm
LLM_ROLE_HEAVY_BASE_URL=http://localhost:8000/v1
LLM_ROLE_HEAVY_MODEL=meta-llama/Meta-Llama-3.1-70B-Instruct
VLLM_DRAFT_MODEL=meta-llama/Llama-3.2-1B-Instruct
VLLM_SPECULATIVE_TOKENS=4
```

---

## New `.env` keys

See [.env.example](.env.example) for the full annotated list. Summary:

| Phase | Key | Purpose |
|---|---|---|
| 1 | `BACKEND_MODE` | `local` / `cloud` / `custom` |
| 1 | `LLM_ROLE_<role>_BACKEND/PROVIDER/MODEL/API_KEY/BASE_URL/FALLBACKS` | Per-role routing |
| 1 | `LLM_MAX_RETRIES` | Retry budget per backend (default 3) |
| 1 | `LLM_CALLS_DB` | SQLite path for per-call accounting |
| 1 | `LLM_PRICING_JSON` | Override per-model pricing table |
| 1 | `OLLAMA_BASE_URL` | Local Ollama endpoint |
| 1 | `VLLM_BASE_URL` / `VLLM_DRAFT_MODEL` / `VLLM_SPECULATIVE_TOKENS` | Self-hosted vLLM |
| 2 | `MEMORY_BACKEND` | `auto` / `in_memory` / `zep_cloud` / `neo4j_local` / `neo4j_aura` |
| 2 | `NEO4J_URI/USER/PASSWORD/DATABASE` | Neo4j connection |
| 2 | `REFLECTION_EVERY_N_ROUNDS` / `REFLECTION_TOP_K_SOURCES` | Reflection scheduler |
| 2 | `MEMORY_ALPHA/BETA/GAMMA` | Retrieval scoring weights |
| 2 | `MEMORY_ENABLE_IMPORTANCE/REFLECTION/CONTRADICTION` | Feature flags |
| 3 | `IPC_TRANSPORT` | `zmq` (default) or `file` |
| 3 | `IPC_CMD_ENDPOINT` / `IPC_EVENT_ENDPOINT` | Explicit transport endpoints |
| 4 | `BOT_POPULATION_PCT` / `TROLL_POPULATION_PCT` | Adversarial archetypes |
| 4 | `MEDIA_POPULATION_PCT` / `EXPERT_POPULATION_PCT` | Institutional archetypes |
| 4 | `POPULATION_SEED` | Deterministic population mix |
| 4 | `CREDIBILITY_WEIGHT` | Retrieval re-rank strength |
| 6 | `ADMIN_TOKEN` | Gates `/api/auth/keys` endpoints |
| 6 | `ALLOW_ANONYMOUS_API` | Demo bypass for `@require_api_key` |
| 6 | `AUTH_DB_PATH` / `QUOTA_DB_PATH` | SQLite locations for keys + usage |
| 6 | `OTEL_EXPORTER_OTLP_ENDPOINT` / `OTEL_SERVICE_NAME` | OTel collector |
| 6 | `COST_BUDGET_<ROLE>_{CALLS,IN,OUT,CACHED}` | Cost-estimator overrides |

**Deprecated** — still honored but documented as legacy:
`LLM_BOOST_API_KEY`, `LLM_BOOST_BASE_URL`, `LLM_BOOST_MODEL_NAME`. These were
the upstream's optional "accelerated LLM" keys; replaced by per-role config.

---

## Breaking changes

**None on the public HTTP surface.** All existing endpoints under `/api/graph`,
`/api/simulation`, `/api/report` behave identically. The new endpoints are
additive (`/api/agents/*`, `/api/eval/*`, `/api/auth/*`, `/api/simulation/*/checkpoint`, `/metrics`, `/ws/*`).

**Python-level changes** that only matter if you've forked the backend:

1. `backend/app/__init__.py` now imports Flask lazily inside `create_app()`
   so `import app.llm.*` works in unit tests without installing Flask.
2. `LLMClient(api_key=..., base_url=..., model=...)` accepts the same
   kwargs but they're no longer sources of truth — the router resolves
   backend config. If you were reading `LLMClient().model` after construction,
   you still get the resolved model string.
3. The three duplicated `OpenAI(...)` instantiations in
   `oasis_profile_generator.py` and `simulation_config_generator.py` are gone.
   Those sites now use `LLMClient.chat_raw()` which returns an `LLMResponse`
   with token counts + finish_reason.

---

## Rollback

Each phase is a separate branch (`phase-1-llm-backend` … `phase-6-ops`)
atop `main`. To roll back to pre-migration:

```bash
git checkout main
```

`phase-4-personas` on `origin` contains every commit from phases 1–4, so
you can pin to that instead of re-running the phase-by-phase migration.

---

## License

Unchanged: **AGPL-3.0**. Same license file as upstream.

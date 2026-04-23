# MiroFish-Cloud Architecture

Phase 1–6 adds several abstraction boundaries to upstream MiroFish so the
same pipeline can run against local open-source models + self-hosted
Neo4j, or against managed Anthropic / OpenAI + Aura. This document
describes the module layout, the data flow, and the deployment topology.

---

## 1. Module layout

```
backend/
├── app/
│   ├── llm/            # Phase 1 — role-based LLM routing
│   │   ├── base.py             LLMBackend ABC, LLMResponse, BackendError, Role
│   │   ├── openai_compat.py    OpenAI / Anthropic / Groq / Together / …
│   │   ├── ollama.py           Local Ollama (HTTP only, no SDK dep)
│   │   ├── vllm.py             vLLM (subclass of openai_compat)
│   │   ├── router.py           ModelRouter: role → backend + retry + fallback
│   │   └── accounting.py       SQLite-backed per-call token / cost tracker
│   │
│   ├── memory/         # Phase 2 — pluggable memory + hierarchical reflection
│   │   ├── base.py             MemoryBackend ABC, Observation, Reflection,
│   │   │                       ConflictEdge, Namespace
│   │   ├── in_memory.py        Dict-based reference impl
│   │   ├── zep_cloud.py        Adapter around existing Zep SDK
│   │   ├── neo4j_local.py      Self-hosted Neo4j via bolt://
│   │   ├── neo4j_aura.py       Managed AuraDB subclass
│   │   ├── hierarchical.py     ImportanceScorer, ReflectionScheduler,
│   │   │                       ContradictionDetector — backend-agnostic
│   │   ├── router.py           MemoryRouter: env-driven backend selection
│   │   └── manager.py          MemoryManager: per-simulation integration
│   │
│   ├── personas/       # Phase 4 — structured personas + dynamics
│   │   ├── schema.py           StructuredPersona, BigFive, StanceVector, Archetype
│   │   ├── prompts.py          persona_system_block() — cache-friendly template
│   │   ├── generator.py        LLM-driven PersonaGenerator (fast-role)
│   │   ├── population.py       Archetype mix (bots / trolls / media / expert)
│   │   ├── inertia.py          StanceInertia — conviction-gated flip counter
│   │   └── credibility.py      CredibilityWeighter — retrieval re-rank
│   │
│   ├── transport/      # Phase 3 — pluggable IPC
│   │   ├── base.py             Transport / ServerTransport ABCs
│   │   ├── file_ipc.py         Legacy file-poll (back-compat)
│   │   ├── zmq_transport.py    ZMQ DEALER/ROUTER + PUB/SUB (default)
│   │   └── factory.py          env-driven selection
│   │
│   ├── ws/             # Phase 3 — WebSocket bridge
│   │   ├── bridge.py           EventBridge fan-out
│   │   └── streaming.py        Flask-Sock routes
│   │
│   ├── checkpoint/     # Phase 3 — simulation save/restore
│   │   ├── serializer.py       Walks namespaces, builds CheckpointData
│   │   └── archiver.py         tar.zst / tar.gz pack + unpack
│   │
│   ├── observability/  # Phase 6 — structured logging + Prometheus + OTel
│   │   ├── logging.py          structlog JSON (stdlib fallback)
│   │   ├── metrics.py          Prometheus registry + helpers
│   │   └── tracing.py          OTel OTLP/HTTP exporter
│   │
│   ├── auth/           # Phase 6 — API-key auth + quotas
│   │   ├── keys.py             ApiKeyStore (SQLite, hashed secrets)
│   │   ├── quotas.py           QuotaTracker (atomic check-and-debit)
│   │   └── middleware.py       @require_api_key
│   │
│   ├── cost/           # Phase 6 — pre-flight cost estimator
│   │   └── estimator.py        (agent × rounds × per-role budget) → USD
│   │
│   └── api/            # Flask blueprints
│       ├── graph.py, simulation.py, report.py        (upstream)
│       ├── agents.py           Phase-2: /api/agents/<id>/reflections|conflicts|retrieve
│       ├── checkpoint.py       Phase-3: /api/simulation/<id>/checkpoint|restore
│       ├── eval.py             Phase-5: /api/eval/results
│       ├── metrics.py          Phase-6: /metrics
│       ├── auth.py             Phase-6: /api/auth/*
│       └── cost.py             Phase-6: /api/simulation/estimate-cost
│
└── eval/               # Phase 5 — evaluation harness
    ├── scoring.py              directional / magnitude / calibration
    ├── verdict.py              public-timeline aggregation
    ├── determinism.py          seed pinning + monotonic clock
    ├── mocks.py                deterministic MockRouter for CI
    ├── pipeline.py             orchestrates a case end-to-end
    ├── runner.py               CLI
    ├── ablation.py             CLI — feature-flag sweep
    ├── storage.py              JSONL results store
    └── datasets/               5 starter (seed.md, question.md, truth.json) cases
```

---

## 2. Abstract backend diagrams

### LLM routing (Phase 1)

Every caller — `OntologyGenerator`, `OasisProfileGenerator`, `ReportAgent`,
`LLMClient` shim, the WebSocket streaming interview, the persona generator
— now flows through `ModelRouter`:

```
┌───────────────────────┐
│ Callers               │
│ - OntologyGenerator   │      chat(role=FAST)
│ - ProfileGenerator    │─────────────────────┐
│ - PersonaGenerator    │ chat(role=BALANCED) │
│ - ReportAgent         │─────────────────────┤
│ - ContradictionDet.   │ chat(role=FAST)     │
│ - ReflectionSched.    │─────────────────────┤
│ - LLMClient shim      │ stream_chat(BAL.)   │
│ - MemoryManager.embed │─────────────────────┤
└───────────────────────┘                     │
                                              ▼
                                 ┌──────────────────────────────┐
                                 │ ModelRouter                  │
                                 │ ├── role → backend map       │
                                 │ ├── retry w/ exp backoff     │
                                 │ ├── fallback chain           │
                                 │ └── accounting (SQLite)      │
                                 └───────┬──────────────────────┘
                                         │
                      ┌──────────────────┼──────────────────┐
                      ▼                  ▼                  ▼
             ┌────────────────┐  ┌───────────────┐  ┌─────────────┐
             │ openai_compat  │  │ ollama        │  │ vllm        │
             │ (OpenAI,       │  │ (local, no    │  │ (self-host, │
             │  Anthropic,    │  │  SDK dep)     │  │  prefix-    │
             │  Groq,         │  │               │  │  cache +    │
             │  Together,     │  │               │  │  spec. dec.)│
             │  DeepInfra,    │  │               │  │             │
             │  Fireworks,    │  │               │  │             │
             │  DashScope)    │  │               │  │             │
             └────────────────┘  └───────────────┘  └─────────────┘
```

### Memory + hierarchical reflection (Phase 2)

```
           ┌───────────────────────────────────────┐
           │            MemoryManager              │
           │  (one per simulation; Phase-4 knobs)  │
           └─────────┬──────────────┬──────────────┘
                     │              │
   record_agent_action()        retrieve_for_agent()
                     │              │
                     ▼              ▼
           ┌──────────────────────────────┐
           │      Hierarchical layer      │
           │  ┌────────────────────────┐  │
           │  │ ImportanceScorer       │  │  ← fast LLM role
           │  │ ReflectionScheduler    │  │  ← balanced LLM role
           │  │ ContradictionDetector  │  │  ← fast LLM role
           │  │ CredibilityWeighter    │  │  ← Phase-4
           │  └────────────────────────┘  │
           └──────────────┬───────────────┘
                          │
                          ▼
           ┌──────────────────────────────┐
           │       MemoryBackend          │
           │        (abstract)            │
           └──┬─────────┬────────┬────────┘
              │         │        │
              ▼         ▼        ▼
    ┌───────────┐  ┌────────┐  ┌───────────────┐
    │ in_memory │  │ zep_   │  │ neo4j_local / │
    │ (tests,   │  │ cloud  │  │ neo4j_aura    │
    │  minimal) │  │        │  │               │
    └───────────┘  └────────┘  └───────────────┘
```

### Transport (Phase 3)

```
  ┌───────────────────────┐            ┌───────────────────────┐
  │ Flask backend         │            │ Simulation subprocess │
  │                       │            │                       │
  │ ┌──────────────────┐  │  DEALER    │  ROUTER               │
  │ │ Transport        │◀─┼────────────┼─► recv_command()       │
  │ │ (client)         │  │   cmd req  │   send_response()      │
  │ │                  │  │  cmd reply │                        │
  │ │                  │  │            │                        │
  │ │                  │  │    SUB     │  PUB                   │
  │ │ subscribe_events │◀─┼────────────┼─── publish_event()     │
  │ └──────────────────┘  │   events   │                        │
  │         │             │            │                        │
  │         ▼             │            └───────────────────────┘
  │ ┌──────────────────┐  │
  │ │ EventBridge      │  │
  │ │ fan-out to       │  │
  │ │ WebSocket clients│  │
  │ └────────┬─────────┘  │
  │          ▼            │
  │     ┌────────┐        │
  │     │ ws     │ × N    │
  │     │ clients│        │
  │     └────────┘        │
  └───────────────────────┘

  Alternate (IPC_TRANSPORT=file): same shape, files under
  <simulation_dir>/ipc_{commands,responses,events}/ instead of sockets.
```

---

## 3. Request data flow

### Normal simulation round (cloud mode, bot-free population)

```
┌────────────────┐
│ OASIS agent N  │ picks next action via camel-oasis internals
└──────┬─────────┘   (uses LLMClient shim → ModelRouter, role=balanced)
       │
       ▼
┌─────────────────────────┐
│ action_logger appends   │
│ to actions.jsonl        │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ ZepGraphMemoryUpdater (adapter)     │
│ ├── legacy: batch to Zep graph.add  │
│ └── Phase-2: MemoryManager.record_  │
│     agent_action()                  │
│          │                          │
│          ▼                          │
│   ┌─────────────────────────────┐   │
│   │ ImportanceScorer (fast LLM) │   │
│   │ ContradictionDetector       │   │
│   │ (fast LLM, top-3 neighbors) │   │
│   │ MemoryBackend.write_*       │   │
│   └─────────────────────────────┘   │
└──────┬──────────────────────────────┘
       │
       │ every N rounds:
       ▼
┌─────────────────────────┐
│ ReflectionScheduler     │
│ top-K importance →      │
│ balanced LLM →          │
│ 3–5 beliefs written     │
└─────────────────────────┘

Metrics emitted at every step: llm_calls_total, llm_tokens_total,
memory_op_duration_seconds, llm_cache_hit_ratio.
```

### Streaming interview (Phase 3)

```
Browser                        Flask backend
   │                                │
   │ WS /ws/simulation/X/interview  │
   │───────────────────────────────▶│
   │                                │
   │  {"agent_id":7,"question":"…"} │
   │───────────────────────────────▶│
   │                                │──── router.stream_chat(BALANCED)
   │                                │         │
   │                                │         ▼
   │                                │    backend.stream_chat()
   │                                │         │
   │       {"chunk": "I'm"}         │◀────────┘
   │◀───────────────────────────────│  token fragments
   │       {"chunk": " a nurse"}    │
   │◀───────────────────────────────│
   │       ...                      │
   │       {"done": true}           │
   │◀───────────────────────────────│
```

Critically, the interview does **not** round-trip through the simulation
subprocess — that's how Phase-3 drops latency from ~200 ms (file poll)
to single-digit ms per token.

---

## 4. Deployment topology (Phase 6)

```
                     ┌──────────────────┐
                     │ OTel Collector   │◀──── traces (OTLP/HTTP)
                     │ Prometheus       │◀──── /metrics scrape
                     └────────┬─────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────┐
│ Kubernetes cluster                                  │
│                                                     │
│  ┌──────────────────────────┐                       │
│  │ Ingress (optional)       │                       │
│  └────────────┬─────────────┘                       │
│               │                                     │
│  ┌────────────▼─────────────┐   ┌─────────────────┐ │
│  │ backend (x N replicas)   │──▶│ redis           │ │
│  │ gunicorn → Flask         │   │ run-state cache │ │
│  │ /health /metrics /ws/*   │   └─────────────────┘ │
│  │ /api/*                   │                       │
│  └────────────┬─────────────┘                       │
│               │                                     │
│  ┌────────────▼─────────────┐   ┌─────────────────┐ │
│  │ vllm (optional, GPU)     │   │ frontend        │ │
│  │ --enable-prefix-caching  │   │ (optional)      │ │
│  │ --speculative-model ...  │   │                 │ │
│  └──────────────────────────┘   └─────────────────┘ │
└─────────────────────────────────────────────────────┘
        │
        │ external (managed)
        ▼
  ┌──────────────────────────────────┐
  │ Neo4j AuraDB (agent memory)      │
  │ Anthropic / OpenAI / vLLM        │
  │ (LLM backends per-role)          │
  │ Zep Cloud (if kept as fallback)  │
  └──────────────────────────────────┘
```

Secrets (`ADMIN_TOKEN`, `LLM_API_KEY`, `ZEP_API_KEY`, `NEO4J_PASSWORD`) are
populated into the `mirofish-secrets` Secret via external-secrets or
sealed-secrets; the Helm chart ships a placeholder Secret so
`helm install` succeeds and operators fill it out-of-band.

Prometheus discovery works via the pod annotations the chart sets
(`prometheus.io/scrape: "true"`, `path: /metrics`, `port: 5000`).

---

## 5. Notable design decisions (cross-phase)

| Decision | Rationale | Location |
|---|---|---|
| Stable prompt prefix, volatile persona block last | Prefix caching only works if the shared header is byte-identical across agents. Bumping this is a behavior change. | `app/personas/prompts.py` |
| Procedural bot/troll personas (no LLM) | Having the LLM invent bot behavior defeats the archetype. | `app/personas/population.py` |
| Bot conviction floor = 1.0 | Bots never change their mind; enforced even if the LLM suggests otherwise. | `app/personas/schema.py` |
| DEALER/ROUTER over REQ/REP | Lets the backend issue concurrent commands without REQ/REP turn-taking serializing WebSocket clients. | `app/transport/zmq_transport.py` |
| Relative cosine in Python for Neo4j | Portability across Neo4j versions; native vector index is documented as an upgrade path. | `app/memory/neo4j_local.py` |
| Stdlib fallback for every observability dep | Bare installs still boot — `/metrics` responds 200, logs are JSON-like even without structlog. | `app/observability/*` |
| MockRouter for determinism | Live LLMs can't be byte-deterministic even at temp=0 (tokenization drift). | `backend/eval/mocks.py` |
| Format-version check on checkpoints | Silent state corruption is worse than a hard fail. | `app/checkpoint/serializer.py` |

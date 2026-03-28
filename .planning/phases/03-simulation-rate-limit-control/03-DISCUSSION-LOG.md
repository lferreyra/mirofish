# Phase 3: Simulation Rate Limit Control — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-28

---

## Area 1: Config Delivery to Simulation Scripts

**Question:** How should rate limit settings reach the simulation subprocess?

| Option | Description |
|--------|-------------|
| ✅ Inject into simulation_config.json | Settings merged into config file before subprocess launch |
| CLI args on subprocess cmd | Adds --rate-limit-delay etc. to cmd array, argparse in 3 scripts |
| Environment variables | Passed via env dict, string-only, not persisted with simulation record |

**Selected:** Inject into simulation_config.json

---

## Area 2: Settings UI Placement

**Question:** Where should the rate limit settings panel live?

| Option | Description |
|--------|-------------|
| ✅ Step3Simulation.vue — inline section | Collapsible section in setup step before Run |
| Modal from SimulationRunView.vue | Gear icon opens modal during run view |
| Both — setup section + run view gear | Read-only view of active settings in run view too |

**Selected:** Step3Simulation.vue — inline collapsible section

---

## Area 3: Retry Scope

**Question:** Where should 429 automatic retry logic apply?

| Option | Description |
|--------|-------------|
| Simulation scripts only | Retry in run_*.py scripts only — matches R3.2 scope exactly |
| ✅ All LLM call sites | Retry in llm_client.py — covers graph build, profile gen, simulation, report agent |

**Selected:** All LLM call sites (llm_client.py)

*Rationale: Single implementation in the shared LLM client is more robust and eliminates duplication across 3 simulation scripts.*

---

## Area 4: Config Endpoint Design

**Question:** How should POST/GET /api/simulation/{id}/config work?

| Option | Description |
|--------|-------------|
| ✅ Merge into existing simulation_config.json | rate_limit section merged in; no new file |
| Separate rate_limit_config.json | Clean separation but adds a second file to track |
| In-memory only | Settings lost on server restart |

**Selected:** Merge into existing simulation_config.json

---

## Area 5: TPM/RPM Controls (user-initiated area)

**Background:** User requested "global TPM and RPM to send to the LLM" as a discussion area.

**Question 1:** What did you have in mind for TPM/RPM control?

| Option | Description |
|--------|-------------|
| Proactive token/request rate cap | App tracks and throttles before hitting provider limit |
| Pass to OASIS/camel-ai config | Use framework's own config for self-limiting |
| ✅ Expose as user-configurable settings in UI | TPM/RPM fields in settings panel, stored in localStorage |

**Selected:** Expose as user-configurable settings in UI

**Question 2:** Fold into Phase 3 or defer?

**Selected:** Fold into Phase 3 — same panel, same config injection path, natural fit.

**Question 3:** How should TPM/RPM limits be enforced?

| Option | Description |
|--------|-------------|
| Rate limit via inter-turn delay only | TPM/RPM stored but not actively enforced |
| Active enforcement in scripts | Token counting in simulation scripts |
| ✅ Pass to llm_client.py as a throttle | Token bucket in shared LLM client |

**Selected:** llm_client.py token bucket throttle

---

# Robotics Actuation Parse Pilot v1

Date: March 16, 2026

## Purpose

Run the first concrete source-ingestion to structural-parse workflow using a
real AleaBito-style thesis fragment:

- robotics BOM mapping
- actuation / motion as the top subsystem
- permanent magnet motors as the critical component
- neodymium processing as the more interesting listed exposure layer

## Inputs

Source bundle:

- [2026-03-16-robotics-actuation-source-bundle-v1.json](/home/d/codex/MiroFish/research/analysis/2026-03-16-robotics-actuation-source-bundle-v1.json)

Generated structural parse:

- [2026-03-16-robotics-actuation-structural-parse-v1.json](/home/d/codex/MiroFish/research/analysis/2026-03-16-robotics-actuation-structural-parse-v1.json)

## Source mix

This pilot intentionally uses mixed-quality inputs:

- `investor_post`
  - AleaBito BOM-mapping fragment
  - AleaBito neodymium-processing fragment
- `user_note`
  - the internal robotics universe seed

That is the correct shape for the current stage.
The point is not to prove the thesis from filings yet.
The point is to prove that MiroFish can preserve the structural chain implied by
the research fragments.

## What the parser recovered

The parser emitted:

- `19` entities
- `15` relationships
- `5` claims
- `21` evidence links
- `1` inference

Most importantly, it reconstructed the chain:

1. `Humanoid Robot`
2. `Actuation / Motion`
3. `Permanent Magnet Motor`
4. `Neodymium`
5. `Neodymium Processing`
6. `MP`, `NEO`, `UUUU`

That is the exact `component -> material -> processing -> equity` pattern we
want MiroFish to learn.

## Most useful output

The highest-value output is not the raw entity list.
It is the explicit `market_miss` inference:

- the market may be underweighting neodymium processing as a cleaner Western
  proxy for robotics scale-up relative to downstream robot narratives

That is the first real proof that the source-ingestion and structural-parsing
layer can produce something closer to structural information arbitrage rather
than generic notes.

## Limits

This is still a `hypothesis-seed` parse, not a final evidence-grade graph.

Current limitations:

- source quality is mixed
- claims are still mostly inferential
- no live company filings are ingested directly into this parse yet
- the parse is deterministic and hint-driven, not full automatic extraction

That is acceptable for now because the immediate goal is:

- make the structure legible
- preserve provenance
- create something the market-miss / pick layers can consume next

## Why this matters

This pilot shows that MiroFish can already own the upstream structural work:

- ingest research fragments
- preserve fragment provenance
- reconstruct the industrial chain
- emit an explicit market-miss inference
- identify candidate listed expressions

That is the core of the pivot.

## Next best move

Use the same pipeline on one evidence-heavier thesis:

- `SIVE` photonics / CPO
- or `MP` rare-earth magnet sovereignty

Then compare:

- fragment-driven exploratory parse
- evidence-backed parse

That comparison will show whether the system can move from early research
fragments into something closer to a conviction-grade structural graph.

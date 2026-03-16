# MP Magnet Sovereignty Parse Pilot v1

Date: March 16, 2026

## Purpose

Run the second concrete source-ingestion to structural-parse workflow on a
higher-quality thesis centered on `MP`.

This pilot is designed to answer a specific question:

- can the same parser that handled exploratory AleaBito-style robotics
  fragments also produce a cleaner structural graph from evidence-heavy source
  material?

## Inputs

Source bundle:

- [2026-03-16-mp-magnet-sovereignty-source-bundle-v1.json](/home/d/codex/MiroFish/research/analysis/2026-03-16-mp-magnet-sovereignty-source-bundle-v1.json)

Generated structural parse:

- [2026-03-16-mp-magnet-sovereignty-structural-parse-v1.json](/home/d/codex/MiroFish/research/analysis/2026-03-16-mp-magnet-sovereignty-structural-parse-v1.json)

## Source mix

This pilot is meaningfully different from the robotics actuation pilot.

Source quality is much stronger:

- `industry_body`
  - IEA concentration commentary
- `policy_tracker`
  - IEA heavy rare earth export-control tracker
- `government`
  - DoD magnet-manufacturing support release
- `company_release`
  - MP magnet-production release
  - MP DoD partnership release

In other words:

- robotics pilot = mostly `hypothesis_seed`
- MP pilot = mostly `evidence`

That is exactly the progression we needed to test.

## What the parser recovered

The parser emitted:

- `20` entities
- `15` relationships
- `7` claims
- `23` evidence links
- `1` inference

Most importantly, it reconstructed a tighter mine-to-magnet chain:

1. `Magnet Rare Earth Separation and Refining`
2. `Sintered NdFeB Magnet Manufacturing`
3. `Dysprosium / Terbium export-control risk`
4. `MP` live and expanding magnet exposure
5. `MP DoD Mine-to-Magnet Partnership`
6. `Shares: MP`

That is a materially sharper structural graph than the earlier exploratory
robotics parse.

## Highest-value output

The best output is the explicit `market_miss` inference:

- the market may still frame `MP` too narrowly as a mining story even though it
  is becoming a policy-backed mine-to-magnet platform tied to the most
  constrained layers

That is exactly the kind of structural information arbitrage statement we want
MiroFish to be able to produce:

- not just “MP is interesting”
- but “the market framing is stale relative to the real structural role”

## Comparison To Robotics Pilot

Robotics actuation pilot:

- stronger on exploratory universe shape
- stronger on `component -> material -> processing -> equity`
- weaker source quality
- better for early idea generation

MP pilot:

- stronger source quality
- stronger policy and strategic-capacity grounding
- stronger direct listed-expression mapping
- better for conviction-building and market-miss validation

This is the distinction we wanted MiroFish to support:

- exploratory structural graph
- then evidence-backed structural graph

## Why This Matters

This pilot is the first clear sign that MiroFish can be used for more than
organizing fragments.

It can now:

- ingest evidence-grade sources
- preserve fragment-level provenance
- reconstruct the constrained industrial layers
- connect those layers to a listed expression
- emit an explicit stale-market-framing inference

That is much closer to a usable structural information arbitrage engine.

## Next Best Move

Do one photonics / CPO parse at the same quality level, probably around `SIVE`.

Why `SIVE`:

- it is closer to the kind of hidden upstream supplier AleaBito highlights
- it will test whether the parser can preserve a more asymmetric but messier
  equity thesis
- it gives us a direct comparison between:
  - clean policy-backed industrial buildout (`MP`)
  - hidden supplier rerating candidate (`SIVE`)

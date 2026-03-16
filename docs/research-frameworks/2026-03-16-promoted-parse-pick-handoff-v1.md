# Promoted Parse Pick Handoff v1

Date: March 16, 2026

## Purpose

Connect the structural-parse graduation gate to the pick engine.

This is the first version where MiroFish can do the whole chain:

1. source bundle
2. structural parse
3. graduation decision
4. auto-generated candidate row
5. ranked pick output

## New artifacts

Manifest of parse inputs:

- [2026-03-16-promoted-parse-manifest-v1.json](/home/d/codex/MiroFish/research/analysis/2026-03-16-promoted-parse-manifest-v1.json)

Auto-generated candidate rows:

- [2026-03-16-promoted-parse-candidates-v1.json](/home/d/codex/MiroFish/research/analysis/2026-03-16-promoted-parse-candidates-v1.json)

Ranked picks:

- [2026-03-16-promoted-parse-picks-v1.json](/home/d/codex/MiroFish/research/analysis/2026-03-16-promoted-parse-picks-v1.json)

Generator:

- [generate_candidates_from_promoted_parses.py](/home/d/codex/MiroFish/scripts/generate_candidates_from_promoted_parses.py)

## Current gating behavior

Only promoted parses can auto-generate candidate rows:

- `watchlist_candidate`
- `pick_candidate`

`exploratory_only` parses are excluded by default.

That means the robotics actuation pilot does **not** flow directly into the pick
engine, which is the correct behavior.

## Current output

The first gated handoff batch produces two candidates:

1. `MP`
   - promotion status: `pick_candidate`
   - final expression after ranking: `shares`

2. `SIVE`
   - promotion status: `watchlist_candidate`
   - final expression after ranking: `shares`

This is directionally right:

- `MP` is evidence-strong enough to enter the ranked pick flow directly
- `SIVE` is promising enough to track, but still flagged by its weaker source mix

## Why this matters

Before this handoff, the structural parser and the pick engine were still
separate systems.

Now there is an explicit rule:

- only structurally-promoted parses are allowed to become auto-generated pick
  candidates

That is a real workflow constraint, not just a conceptual preference.

## Limits

This is still an early version of the handoff.

Current limitations:

- signal blocks are derived heuristically from graduation scores and parse shape
- the handoff currently prefers `shares` by default for both promoted names
- there is no direct market-data or options-chain feedback in the handoff layer

That is acceptable for now because the main goal was:

- stop unvetted parses from leaking straight into picks
- prove that promoted structural outputs can feed the ranking flow

## Next best move

Use this handoff on future parses by default, then refine the conversion logic:

- make the auto-generated signals more grounded in actual parse content
- incorporate market-data validation for `pick_candidate` names
- allow watchlist candidates like `SIVE` to auto-upgrade only after a defined
  corroboration step

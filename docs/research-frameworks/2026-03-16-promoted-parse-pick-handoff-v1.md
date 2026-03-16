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

After the market-data-aware conversion pass, the handoff no longer treats both
names the same way:

- `MP` now carries explicit local options evidence:
  - public chain snapshots
  - watchlist observations
  - resale-scenario checks
  - same-capital strike rescreen data
- `SIVE` now carries an explicit lack-of-options-evidence penalty because there
  is no usable long-dated chain data in the repo yet

That makes the expression layer much less heuristic than the original handoff.

The ranking layer is also now promotion-aware:

- raw pick score is still preserved
- but a separate ranking score incorporates promotion strength
- viable `pick_candidate` parses now sort ahead of weaker `watchlist_candidate`
  parses instead of relying on metadata only

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

- the conversion layer still relies on local research artifacts rather than live
  market-data ingestion
- `MP` and `SIVE` are not yet being evaluated against the same breadth of
  options evidence
- the handoff can now see market-data checks, but the final ranking still
  ignores promotion status beyond the candidate-row metadata

That is acceptable for now because the main goal was:

- stop unvetted parses from leaking straight into picks
- prove that promoted structural outputs can feed the ranking flow

## Next best move

Use this handoff on future parses by default, then refine the conversion logic:

- widen market-data checks beyond the small local watchlist/rescreen set
- make promotion status a cleaner ranking input instead of metadata only
- allow watchlist candidates like `SIVE` to auto-upgrade only after a defined
  corroboration step

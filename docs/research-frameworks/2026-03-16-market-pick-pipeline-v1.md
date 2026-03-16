# Market Pick Pipeline V1

Date: March 16, 2026

## Goal

This pipeline is the reset toward what actually matters:

- scan candidate bottleneck theses
- force a final expression choice
- produce ranked picks

The output is not an ontology or a memo. The output is a pick list with one of:

- `shares`
- `leaps_call`
- `reject`

## Pipeline

1. `Generate candidates`
   Start from expanding markets where bottlenecks plausibly matter:
   - AI photonics
   - HBM / packaging
   - grid equipment
   - rare earths
   - cooling

   Candidate generation can now happen in two ways:

   - manual research rows
   - auto-generated rows from promoted structural parses

   Structural parses should only auto-generate candidate rows if they have
   already cleared the graduation gate:

   - `watchlist_candidate`
   - `pick_candidate`

2. `Score structural mispricing`
   For each candidate, score:
   - hiddenness
   - recognition gap
   - catalyst clarity
   - propagation asymmetry
   - duration mismatch
   - evidence quality

   For names where hidden-supplier asymmetry matters, optionally add:
   - ecosystem centrality
   - downstream valuation gap
   - microcap rerating potential

3. `Score expression quality`
   Score both:
   - `options_fit`
   - `leaps_bias`
   - `stock_fit`

   `options_fit` answers:
   - are options sensible in principle?

   `leaps_bias` answers:
   - are long-dated calls actually attractive enough to beat the default stock choice?

   The current LEAPS-bias inputs are:
   - iv cheapness
   - surface staleness
   - pre-expiration repricing potential
   - stock-vs-call convexity advantage
   - long-dated liquidity quality

4. `Force expression choice`
   The current rules are:
   - reject if mispricing score is too low
   - choose `leaps_call` only if both:
     - options fit is strong
     - LEAPS bias is strong
   - otherwise choose `shares` if stock fit remains stronger
   - otherwise reject

5. `Rank picks`
   Rank by:
   - mispricing score
   - best expression score
   - asymmetry bonus
   - expression bonus / penalty

## Artifacts

Template:

- [market-scan-candidate-template.json](/home/d/codex/MiroFish/research/templates/market-scan-candidate-template.json)

Generator:

- [generate_market_picks.py](/home/d/codex/MiroFish/scripts/generate_market_picks.py)

Example:

```bash
python3 scripts/generate_market_picks.py \
  research/templates/market-scan-candidate-template.json \
  --output-json research/analysis/market-picks-v1.json
```

## Why This Is Closer To The Real Goal

This is designed to answer:

- what are the best current picks?
- should they be expressed in stock or LEAPS?

It is explicitly not trying to optimize for research elegance.

## Current Limitation

This pipeline still depends on human-generated candidate rows.

So today it is a:

- `ranker and picker`

not yet a:

- `full market crawler`

The next gap to close is candidate generation breadth, not more downstream
analysis infrastructure.

The new structural-parse graduation layer means breadth does not have to come
only from manual rows anymore. MiroFish can now promote parses into candidate
rows automatically when the source mix and market-miss inference are strong
enough.

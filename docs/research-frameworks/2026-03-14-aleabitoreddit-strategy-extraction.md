# Strategy Extraction: `@aleabitoreddit`

Date: March 14, 2026

## Objective

Extract the recurring research pattern behind `@aleabitoreddit`'s public theses and translate that pattern into a repeatable MiroFish workflow for discovering similar bottleneck-driven investment ideas.

This is not a credibility memo or biography. It is a strategy memo.

## Working Hypothesis

The strategy is not "predict future winners from vibes."

The strategy appears to be:

1. Start with a fast-growing system-level trend.
2. Decompose that system into a bill of materials or dependency chain.
3. Find the narrowest qualified supplier layer.
4. Identify where supply is concentrated, slow to expand, or geopolitically exposed.
5. Ask which public equities have hidden leverage to that chokepoint.
6. Build a basket or thesis around the bottleneck rather than the end-market narrative.

This is a bottleneck-first, dependency-mapping strategy.

## Evidence From Public Posts And Mirrors

The recurring motifs visible in public search/mirror results are:

- InP substrate concentration as an AI photonics chokepoint
- HBM / packaging / glass substrate / optical bottleneck mapping
- transformer and grid-equipment bottlenecks
- rare earth / strategic mineral bottlenecks
- "Bottleneck ETF" or basket-style framing rather than a single-name-only approach

Representative public traces:

- A mirrored post referencing an equal-weighted "Bottleneck ETF" basket built from a bottleneck summary:
  - https://ww.twstalker.com/ThematicTrades
- A mirrored post mapping TPU photonics flow through AXT / Sumitomo / IQE / Lumentum / Innolight:
  - https://x.com/Vivian193299/status/2026631203995136420
- Search results showing transformer bottleneck and mineral-bottleneck style reasoning:
  - https://twitter.com/i/grok/share/112Ka2iEF2O5ci6Qy7gGm0Osj
  - https://twitter.com/i/grok/share/jxEdwlPu4GK2MoxrhRAIi1m40

These are not treated as primary facts. They are evidence of a recurring style of reasoning.

## Strategy Pattern

### 1. Start from demand that is obvious

The starting point is usually a consensus secular trend:

- AI data-center buildout
- EV / grid electrification
- robotics
- defense / drones
- strategic minerals

This is important because the edge is not "AI is big." The edge is in going one or two layers deeper than where most investors stop.

### 2. Translate narrative demand into a physical chain

Instead of reasoning at the level of "AI winners," the strategy maps the actual chain:

- raw material
- substrate
- wafer / epi
- component
- module
- system
- customer

This is essentially bottom-up industrial graph analysis.

### 3. Look for qualified scarcity, not generic scarcity

The bottleneck is rarely just "a material exists in limited quantity."

It is more often:

- a material with few qualified suppliers
- a process with long lead times
- a component with difficult customer qualification
- a layer with poor substitutability
- a node exposed to export control or geography risk

That distinction is critical. Many materials are abundant in theory but constrained in qualified, usable form.

### 4. Exploit hidden equity exposure

The strategy appears to favor names where:

- the market cap is small relative to strategic importance
- the company is obscure
- the exposure is upstream and underappreciated
- the valuation has not fully repriced to the bottleneck thesis

This is why the framework naturally surfaces names like AXT instead of only hyperscalers.

### 5. Use baskets when the chain is uncertain

The public traces suggest a willingness to hold a bottleneck basket rather than force precision at the earliest stage. That is a rational response when:

- the exact choke point is not yet proven
- multiple adjacent layers may benefit
- the narrative may be right even if the first chosen stock is wrong

## Strengths Of The Strategy

### It goes deeper than most thematic investing

Most thematic work stops at:

- demand up
- leader wins

This strategy asks:

- what has to be true physically for the demand story to happen?

That is a better filter for supply-chain asymmetry.

### It is compatible with long-duration investing

This method works best where:

- demand compounds over years
- capacity takes years to add
- qualification slows substitution
- policy and geopolitics matter

That is naturally LEAPS-friendly.

### It can surface non-consensus names

If the thesis is real, the biggest upside may sit in an overlooked supplier rather than the obvious platform company.

## Weaknesses And Failure Modes

### It can overstate single-point-of-failure risk

The biggest risk in this style is rhetorical escalation:

- concentrated market -> existential bottleneck
- important input -> irreplaceable chokepoint
- likely dependence -> proven dependence

That can produce compelling threads but weak underwriting.

### It may identify the right chain and the wrong layer

A bottleneck can exist, yet the best investment return may not accrue to:

- the rawest upstream layer
- the smallest company
- the company with the most obvious narrative purity

Value capture often shifts to the qualified device or system layer.

### Capacity response can kill the thesis

A valid bottleneck can still be a bad trade if:

- capacity expands quickly
- customer sourcing improves
- margins do not flow through
- the market prices the thesis before fundamentals confirm it

### Narrative speed can exceed evidence quality

This style is strongest at idea generation and weakest when it leaps beyond public proof.

## Where This Strategy Probably Works Best

The framework works best when all or most of these are true:

- secular demand growth is clear
- physical supply is hard to expand
- qualification is slow
- substitutes are weak
- supplier count is small
- geopolitics or export controls matter
- the public equity mapping is non-obvious

Good domains:

- AI optical networking
- HBM / advanced packaging
- transformers / switchgear / grid components
- critical minerals with refining concentration
- industrial automation components with long lead times
- aerospace / defense subcomponents

Bad domains:

- markets with low physical dependency
- software-only narratives
- hyper-liquid commodity chains with many substitutes
- very short-duration trades

## MiroFish Translation

MiroFish can be adapted to imitate the useful part of this strategy.

### What MiroFish should do

Use MiroFish as a bottleneck-discovery engine:

1. ingest filings, earnings calls, technical blogs, government reports, industry research, and news
2. extract entities:
   - materials
   - suppliers
   - components
   - fabs
   - countries
   - export controls
   - customers
   - lead times
   - capacity expansions
3. build a dependency graph
4. score concentration, substitutability, lead time, and geopolitics
5. simulate scenario shocks through the graph
6. rank bottleneck candidates and exposed public equities

### Proposed ontology

Core entity types:

- Material
- Substrate
- Epiwafer
- Component
- Module
- System
- Supplier
- Customer
- Facility
- Country
- Policy / Export Control
- Capacity Expansion
- Qualification Program
- End Market
- Public Company

Core relationships:

- `supplies`
- `manufactures`
- `qualifies_for`
- `depends_on`
- `located_in`
- `restricted_by`
- `expands_capacity_for`
- `used_in`
- `sold_to`
- `competes_with`
- `substitutes_for`

### Bottleneck score

MiroFish should compute a chokepoint score from:

- supplier concentration
- lead time
- switching cost / qualification friction
- geopolitical exposure
- demand growth rate
- capital intensity to add supply
- evidence of price increases or allocation behavior

## Concrete Workflow

### Phase 1: Thesis ingestion

Input:

- one thesis seed, often from an investor post, conference note, or filing

Output:

- structured claim list
- missing-evidence list
- first-pass graph

### Phase 2: Chain reconstruction

Input:

- company filings
- product pages
- conference presentations
- government or industry reports

Output:

- supplier layer map
- concentration table
- capacity map
- geographic risk map

### Phase 3: Public equity mapping

Output:

- pure-play names
- adjacent beneficiaries
- safer second-order picks
- false-purity traps

### Phase 4: Scenario simulation

Simulate cases like:

- export restriction
- fab outage
- delayed capacity expansion
- faster demand ramp
- qualification success by a new entrant

Output:

- most likely bottleneck points
- most likely value-capture layer
- names with asymmetric upside

## Best First Research Buckets For This Approach

If the goal is to replicate the style beyond InP, the highest-potential areas are:

1. HBM and advanced packaging
2. transformer / switchgear / grid equipment
3. rare earth magnets and critical-mineral refining
4. AI optical networking beyond InP alone
5. cooling and power-delivery components inside AI infrastructure

## Recommended Rules Of Discipline

To keep the strategy useful and avoid social-media overreach:

1. Separate "claim" from "primary evidence" every time.
2. Never confuse concentrated supply with guaranteed pricing power.
3. Always identify the value-capture layer before picking a stock.
4. Track capacity expansion as aggressively as demand growth.
5. Prefer baskets early, concentration later.
6. Distinguish "important input" from "hard bottleneck."

## Conclusion

The strategy behind `@aleabitoreddit` is best understood as:

`supply-chain graph investing focused on qualified bottlenecks`

That is a real and promising framework.

MiroFish can be repurposed to do it well, because the task is fundamentally about:

- entity extraction
- graph building
- dependency mapping
- scenario simulation
- report generation

The opportunity is not to copy the account's conclusions. It is to systematize the method while tightening the evidence standard.

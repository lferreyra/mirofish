# MiroFish As A Mispricing Discovery Engine

Date: March 14, 2026

## Core Idea

MiroFish should not be framed primarily as a stock picker or a generic forecasting engine.

Its best use in this context is:

`discover hidden dependency structures that the market is likely underpricing`

That is the key abstraction.

The bottleneck thesis is not the end product. It is the upstream research process used to locate mispricings.

## Strategy In One Sentence

Find structural relationships that matter more than the market currently believes, then profit when prices adjust upward to reflect that hidden importance.

In practice, the strategy looks like:

1. uncover a hidden dependency
2. determine why it matters
3. determine why the market is not pricing it correctly
4. identify the asset or option surface most sensitive to repricing
5. wait for the recognition cycle

## Why This Fits MiroFish

MiroFish already has the right conceptual building blocks:

- document ingestion
- entity extraction
- graph construction
- relationship mapping
- scenario generation
- report output

Those are not good tools for high-frequency prediction.

They are good tools for:

- supply-chain inference
- hidden concentration mapping
- second-order consequence discovery
- identifying fragile points in a system

That is exactly the front half of a mispricing-discovery workflow.

## Reframing The Goal

The wrong framing is:

- "Use MiroFish to predict which stock goes up."

The better framing is:

- "Use MiroFish to identify where public markets are likely underestimating future strategic importance, scarcity, fragility, or variance."

This means the output is not initially a ticker.

The output is:

- a hidden dependency map
- a bottleneck score
- a regime-shift narrative
- a list of exposed public instruments

## The General Pattern

The workflow can be abstracted into five layers.

### 1. Structural Discovery

Find relationships that are real but underappreciated.

Examples:

- a tiny supplier controls qualified substrate supply
- a country dominates refining for a strategic input
- a component with long qualification cycles has only a few vendors
- a software platform is more exposed to one customer or one hardware path than consensus assumes

### 2. Importance Assessment

Estimate whether the dependency is actually consequential.

Important filters:

- size of end-market demand
- difficulty of substitution
- time required to add supply
- customer qualification friction
- policy or export-control risk
- historical evidence of shortages or allocation

### 3. Mispricing Hypothesis

Ask where the market is wrong.

Examples:

- the supplier is treated as niche despite strategic leverage
- a basket is priced as diversified despite concentrated hidden exposure
- long-dated volatility is too low given a latent regime shift
- the market underestimates the probability of supply disruption
- the market overestimates how quickly capacity can be added

### 4. Expression Mapping

Only after the mispricing is defined do you choose the instrument.

Possible expressions:

- common equity
- LEAPS calls
- call spreads
- long-dated straddles or strangles
- basket trades
- relative-value pair trades

This is downstream of MiroFish, not the main job of MiroFish itself.

### 5. Recognition Path

The thesis needs a plausible repricing path.

Typical catalysts:

- earnings and guidance
- capex announcements
- shortages or allocation behavior
- export controls
- qualification wins
- hyperscaler purchase agreements
- accidents, outages, or policy shocks

## What Types Of Mispricings This Approach Can Find

### 1. Hidden bottleneck mispricings

The market sees a big trend but misses the narrow upstream constraint.

Example shape:

- AI buildout is obvious
- optical scaling is obvious
- a niche substrate supplier is not obvious

### 2. Hidden concentration mispricings

The market thinks an asset is broad or diversified, but one factor dominates outcomes.

Example shape:

- an ETF or country index is assumed diversified
- in reality, one company or one chain drives the economics

### 3. Fragility mispricings

The market assumes resilience where the actual system is brittle.

Example shape:

- a supply chain appears global
- but qualified production sits in one geography or one process node

### 4. Variance mispricings

The market underprices future uncertainty because it has not internalized the structural dependency.

This is where long-vol or `vega expansion` expressions may become attractive.

### 5. Second-order beneficiary mispricings

The obvious narrative names are fully priced, but an adjacent enabler is not.

Example shape:

- everyone buys the system leader
- few notice the quiet component vendor with tightening supply

## What MiroFish Should Output

If adapted properly, MiroFish should produce a research artifact like this:

### Thesis Summary

- hidden dependency discovered
- why it matters
- why it may be mispriced

### Graph Summary

- supplier chain
- customer links
- geographic exposure
- capacity nodes
- policy constraints

### Bottleneck Metrics

- concentration score
- substitutability score
- lead-time score
- geopolitical-risk score
- demand acceleration score
- qualification-friction score

### Mispricing Candidates

- pure-play equity
- adjacent beneficiary
- broad asset hiding concentration
- long-vol candidate

### Catalyst Map

- what could force recognition
- what would falsify the thesis

## What MiroFish Cannot Do Well Yet

This distinction matters.

MiroFish is currently useful for:

- narrative ingestion
- entity graphing
- dependency mapping
- scenario reasoning

MiroFish is not currently built for:

- options chain ingestion
- implied-volatility surface analysis
- realized vs implied volatility comparison
- cross-asset screeners
- trade execution or portfolio construction

So the correct architecture is:

- MiroFish for idea generation and structural inference
- a separate market-data and options layer for pricing and expression

## Proposed Research Pipeline

### Stage 1: Idea Intake

Inputs:

- investor thread
- earnings-call comment
- policy update
- technical industry note
- supplier capex release

MiroFish job:

- convert the narrative into structured claims

### Stage 2: Dependency Reconstruction

MiroFish job:

- extract materials, suppliers, customers, countries, facilities, and policies
- create a graph of who depends on whom

### Stage 3: Chokepoint Analysis

MiroFish job:

- rank narrow supplier layers
- identify concentrations and weak substitutes
- identify locations where delays or restrictions would propagate broadly

### Stage 4: Mispricing Framing

MiroFish job:

- propose where the market may be underestimating strategic importance or fragility

### Stage 5: Trade Handoff

Separate system job:

- check market cap sensitivity
- pull options chains
- analyze implied vol
- compare expression alternatives
- define risk and sizing

## Good Domains For This Method

This approach should work best in domains with:

- real physical supply chains
- long qualification cycles
- geopolitical sensitivity
- few qualified vendors
- multi-year secular demand

Good candidates:

- AI photonics
- HBM and advanced packaging
- grid transformers and switchgear
- critical-mineral refining
- thermal management and cooling
- advanced substrates and specialty materials

## Bad Domains For This Method

It should work poorly in areas where:

- the dependency graph is weak
- substitution is easy
- pricing is already fully transparent
- there is little physical constraint
- the time horizon is too short

Examples:

- most purely software narratives
- high-frequency macro trades
- liquid commodity markets with many near substitutes

## Rules For Not Fooling Ourselves

If this is going to be useful, these discipline rules are mandatory.

1. Never mistake an interesting dependency for a proven bottleneck.
2. Never mistake a bottleneck for a good stock.
3. Never mistake a good stock thesis for a good options expression.
4. Always separate thesis confidence from pricing confidence.
5. Always track capacity expansion, not just scarcity.
6. Always define a falsification path.

## Concrete Repo Implications

If we want to adapt MiroFish around this strategy, the next features should be:

### 1. Thesis intake templates

Structured fields for:

- source thesis
- raw claims
- evidence links
- unresolved assertions

### 2. Bottleneck ontology

Entity types:

- Material
- Supplier
- Component
- Module
- Customer
- Facility
- Country
- Policy
- Capacity Expansion
- Public Company

### 3. Chokepoint scoring

Scores for:

- concentration
- lead time
- substitutability
- qualification friction
- geographic concentration
- policy exposure

### 4. Research memo generation

Standard outputs:

- thesis memo
- claims audit
- scenario matrix
- watchlist

### 5. Market-layer handoff

Not full trading automation yet, but at least:

- candidate ticker list
- likely expression types
- catalyst calendar

## Conclusion

The real opportunity is not to make MiroFish "predict stock prices."

It is to make MiroFish good at one narrower and more defensible job:

`finding underpriced structural dependencies before the market fully understands them`

That is the part of the strategy we can systematize.

Trade expression, options structure, and volatility analysis should remain downstream modules until the dependency-discovery layer is solid.

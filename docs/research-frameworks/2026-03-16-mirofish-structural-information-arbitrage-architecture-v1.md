# MiroFish Structural Information Arbitrage Architecture v1

Date: March 16, 2026

## Purpose

Define a concrete pivot architecture for using MiroFish as a system for
structural information arbitrage.

This document answers a narrower question than the earlier framing memos:

- not "can MiroFish help?"
- but "what should MiroFish actually own, what should it hand off, and how do
  the current repo pieces map into a real workflow?"

## Bottom Line

Yes, MiroFish can be adapted into a structural information arbitrage system.

The correct role is not:

- an options-pricing terminal
- a high-frequency predictor
- a standalone execution engine

The correct role is:

- a structural synthesis engine
- a dependency-mapping engine
- a market-miss detection engine
- an expression recommendation engine up to, but not through, final pricing

So the architecture should be:

- `MiroFish core` = structural intelligence layer
- `Market data layer` = pricing and chain evidence layer
- `Expression layer` = stock / LEAPS / long-vol choice

## Why This Fits The Real Goal

The target is not "make pretty research."
The target is:

- discover underappreciated structural facts
- organize them into a legible thesis
- identify who benefits or suffers
- select the most asymmetric listed expression

That is exactly what MiroFish is better suited for than a pure quant stack.

The hard part of these trades is often not:

- calculating Black-Scholes

It is:

- knowing what the market is failing to connect

That is the part MiroFish should own.

## Core design principle

MiroFish should be optimized for:

- `finding`
- `synthesizing`
- `ranking`
- `handing off`

not for:

- low-latency quoting
- broker execution
- live portfolio management

## Functional architecture

The system should be thought of as seven layers.

### Layer 1. Source ingestion

Inputs:

- filings
- earnings calls
- technical blogs
- industry decks
- government / policy documents
- trade news
- investor threads
- user notes and watchlists

What MiroFish owns:

- ingestion pipeline
- source metadata
- document tagging
- source quality ranking

Current repo mapping:

- research memos and case studies already approximate this manually
- research-mode project persistence can store the artifacts

Future product mode:

- research project source bucket
- source-type labels
- source confidence markers

### Layer 2. Structural parsing

Goal:

Turn raw information into a structured dependency view.

Entity types:

- system
- subsystem
- component
- material
- processing / refining layer
- supplier
- customer
- geography
- facility
- policy / export control
- public equity

What MiroFish owns:

- entity extraction
- relationship extraction
- ontology validation
- graph construction

Current repo mapping:

- finalized bottleneck ontology
- research ontology service
- case-study chain decomposition

This is already a MiroFish-native strength.

### Layer 3. Universe construction

Goal:

Construct a research universe before making picks.

This should generate:

- anchors
- asymmetric satellites
- geography proxies
- alternative exposures
- weak links in the chain

This is important because AleaBito-style thinking appears to be:

- universe first
- pick second

What MiroFish owns:

- anchor identification
- satellite identification
- chain-bucket grouping
- subsystem grouping
- geography concentration map

Current repo mapping:

- robotics universe seed
- AI / robotics / lasers scan inputs
- candidate templates

### Layer 4. Market-miss detection

Goal:

Identify what the market is not yet connecting.

This is the heart of structural information arbitrage.

Useful questions:

- what is obvious?
- what is still hidden?
- which layer is being ignored?
- which supplier is treated as niche despite strategic centrality?
- where is a downstream valuation anchor much larger than the upstream supplier?
- what event or policy change would force recognition?

What MiroFish owns:

- hiddenness scoring
- recognition-gap scoring
- asymmetry scoring
- downstream valuation-gap reasoning
- geography and policy transmission logic

Current repo mapping:

- mispricing scoring
- asymmetry-aware tuning
- pick pipeline

### Layer 5. Expression preselection

Goal:

Narrow the possible listed expression without pretending to do final pricing.

Possible outputs:

- `shares`
- `leaps_call`
- `long_vol`
- `basket`
- `reject`
- `needs_chain_check`

What MiroFish should own:

- structural reasons for preferring stock vs options
- initial LEAPS bias
- candidate strike/expiry interest flags
- need-for-further-chain-evidence flag

What MiroFish should not own yet:

- live surface fitting
- complete options fair-value engine

Current repo mapping:

- options_fit
- stock_fit
- leaps_bias
- final expression choice

### Layer 6. Market-data handoff

Goal:

Pull in the narrow set of market data needed to validate the expression.

Inputs:

- options chain snapshots
- IV and spread data
- OI / volume
- repeated watchlist observations
- maybe analyst target dispersion later

This layer can be thin.
It only needs to answer:

- is the listed expression actually usable?
- is the long-dated optionality stale or rich?

What belongs outside core MiroFish:

- broker APIs
- chain capture tooling
- quote normalization
- scenario pricing scripts

Current repo mapping:

- public chain capture workflow
- chain normalizer
- watchlist
- resale-scenario model

This is already the right separation.

### Layer 7. Decision and tracking

Goal:

Freeze the pick and track it.

Output shape:

- thesis
- ticker
- expression
- why the market is wrong
- catalysts
- invalidations
- what would upgrade / downgrade the expression

Then track:

- stock performance
- option performance
- IV changes
- thesis milestones

What MiroFish owns:

- decision artifact
- thesis tracking
- milestone logging
- change in structural evidence

What sits outside or adjacent:

- actual trade execution
- portfolio construction
- sizing

## What MiroFish should explicitly own

The most important point in this architecture is role clarity.

MiroFish should own:

- source organization
- dependency mapping
- BOM and component decomposition
- processing/refining layer identification
- geography concentration mapping
- anchor and satellite universe construction
- hiddenness and recognition-gap scoring
- catalyst and invalidation mapping
- stock vs LEAPS preselection

These are the places where structural information arbitrage is won or lost.

## What MiroFish should explicitly not try to own

MiroFish should not try to become:

- a brokerage client
- a live pricing terminal
- a surface-calibration platform
- a full options backtester
- a position-sizing engine

Those are separate systems.

Trying to force them into MiroFish would blur the product and weaken the part
that is actually differentiated.

## Product pivot proposal

If this becomes a first-class mode in the product, the user flow should look
like this.

### Research mode flow

1. `Start project`
   - choose theme or event
   - choose domain:
     - AI
     - robotics
     - lasers
     - power
     - minerals
     - geopolitics

2. `Build universe`
   - system
   - BOM buckets
   - anchors
   - satellites

3. `Map dependencies`
   - graph
   - geography
   - qualified suppliers
   - processing layers

4. `Score market miss`
   - hiddenness
   - asymmetry
   - valuation gap
   - recognition risk

5. `Preselect expression`
   - shares
   - LEAPS
   - basket
   - reject
   - needs chain check

6. `Attach chain evidence`
   - optional but required for a true LEAPS promotion

7. `Freeze pick`
   - thesis card
   - catalysts
   - invalidations
   - tracking status

## How the current repo already supports this

The pivot is not hypothetical.
Large parts are already here.

Already present:

- research memos and framework docs
- bottleneck ontology
- research project persistence
- case studies
- mispricing scoring
- asymmetry-aware pick engine
- LEAPS bias layer
- chain capture and normalization
- watchlist and resale-scenario analysis

What is missing is primarily:

- better candidate generation breadth
- a first-class universe-construction workflow
- a cleaner UI around the research-first flow
- eventual integration with richer market-data sources

## Practical near-term roadmap

### Phase 1. Make MiroFish excellent at universe construction

Goal:

- from user notes, sources, or a thread, generate:
  - BOM buckets
  - anchors
  - satellites
  - geography map

This is the closest thing to the AleaBito-style "research list" behavior.

### Phase 2. Make market-miss detection explicit

Goal:

- force articulation of:
  - what is known
  - what is hidden
  - what is underpriced
  - what could make the thesis legible

### Phase 3. Tighten expression promotion

Goal:

- only allow `LEAPS` when:
  - options_fit is strong
  - LEAPS bias is strong
  - chain evidence is not obviously bad

This is already underway.

### Phase 4. Add event-translation mode

Goal:

- take policy / regime / export-control shocks
- map them through the graph
- rank exposures

This is necessary because the working hypothesis now shows AleaBito is not only
doing bottlenecks.

### Phase 5. Add benchmark mode

Goal:

- compare MiroFish universe / picks against AleaBito-style benchmark cases
- check:
  - universe alignment
  - anchor alignment
  - satellite alignment
  - expression alignment

## Key design insight

The right question is not:

- "Can MiroFish price options?"

The right question is:

- "Can MiroFish reliably identify structural information the market is failing
  to connect, and narrow that into a small set of expressions worth pricing?"

If the answer to that becomes yes, the system is valuable.

The pricing layer can remain thinner and external.

## Final architecture statement

MiroFish should become:

- a structural information arbitrage workbench

with four core outputs:

1. `universe`
2. `hidden dependency map`
3. `market-miss hypothesis`
4. `expression recommendation`

That is a coherent pivot.
It stays faithful to what MiroFish is good at, and it lines up with the actual
problem you are trying to solve.

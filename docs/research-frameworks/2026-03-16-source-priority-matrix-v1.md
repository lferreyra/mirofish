# Source Priority Matrix v1

Date: March 16, 2026

## Purpose

Define the highest-value source classes MiroFish should prioritize for
structural information arbitrage.

This is not just a credibility ranking.

The goal is to rank sources by their usefulness for:

- early market awareness
- causal graph formation
- bottleneck confirmation
- event transmission
- pick generation

The core selection rule is:

- authoritative enough to trust
- early enough to matter
- connected enough to propagate into many later facts
- specific enough to change a graph edge, not just a narrative

## Scoring dimensions

Each source class should be judged on five dimensions:

- `Authority`
  Can this source directly establish a fact?

- `Lead Time`
  How likely is this source to matter before consensus fully prices it?

- `Graph Centrality`
  How many downstream claims, entities, or relationships can this source alter?

- `Market Impact`
  How likely is the source to influence valuation, volatility, or expression choice?

- `Parse Utility`
  How well does the source support concrete claims, edges, and catalysts?

Scores are on a `1-5` scale.

Candidate venue backlog:

- [Source Investigation List v1](/home/d/codex/MiroFish/docs/research-frameworks/2026-03-16-source-investigation-list-v1.md)

## Source roles

Every source should be classified into one of three roles:

- `graph_forming`
  Can directly create or change structural edges.

- `graph_confirming`
  Helps validate or enrich a graph that already exists.

- `graph_suggesting`
  Useful for idea discovery, but not strong enough to anchor the graph alone.

## Matrix

| Source class | Role | Authority | Lead time | Graph centrality | Market impact | Parse utility | Priority | Why it matters |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `government_policy_enforcement` | `graph_forming` | 5 | 5 | 5 | 5 | 5 | `P0` | Directly changes who can ship, refine, export, qualify, or receive support. One notice can alter many graph edges at once. |
| `government_industrial_base_awards` | `graph_forming` | 5 | 5 | 5 | 5 | 5 | `P0` | Reveals what the state believes is strategically constrained enough to subsidize or accelerate. |
| `company_filings` | `graph_forming` | 5 | 5 | 4 | 5 | 5 | `P0` | Best source for capacity, customers, debt, dilution, risk, timeline, and concentration clues. |
| `earnings_transcripts` | `graph_forming` | 4 | 5 | 4 | 5 | 5 | `P0` | Often the first place management clarifies ramp delays, qualification progress, pricing, and customer mix. |
| `industry_bodies_and_standards` | `graph_forming` | 5 | 4 | 5 | 5 | 5 | `P0` | Defines what the whole industry admits is constrained, delayed, or changing architecturally. |
| `supplier_customer_qualification_releases` | `graph_forming` | 4 | 5 | 4 | 4 | 5 | `P0` | Converts vague ecosystem association into actual graph edges like `SUPPLIED_BY`, `QUALIFIED_BY`, or `EXPANDS_CAPACITY_FOR`. |
| `foreign_exchange_filings` | `graph_forming` | 5 | 5 | 4 | 4 | 5 | `P0` | Many hidden upstream names live outside U.S. markets; these filings can be materially ahead of U.S. market attention. |
| `technical_conference_material` | `graph_forming` | 4 | 5 | 4 | 4 | 5 | `P1` | Reveals architecture shifts, BOM changes, and process necessity before broad sell-side adoption. |
| `company_releases` | `graph_forming` | 4 | 4 | 3 | 4 | 4 | `P1` | Useful for partnerships, production readiness, expansion, and debt events, but requires corroboration when overly promotional. |
| `policy_trackers` | `graph_confirming` | 4 | 4 | 5 | 5 | 4 | `P1` | Useful aggregation layer for ongoing policy states, especially when primary notices are fragmented across agencies. |
| `trade_press_specialist` | `graph_confirming` | 3 | 4 | 4 | 4 | 4 | `P1` | Best secondary layer for fast synthesis of technical and industrial developments into usable context. |
| `market_data_snapshot` | `graph_confirming` | 4 | 4 | 3 | 5 | 4 | `P1` | Essential for expression selection: stock vs LEAPS, chain liquidity, IV behavior, and repricing path. |
| `procurement_and_capex_guidance` | `graph_forming` | 4 | 4 | 4 | 4 | 4 | `P1` | Shows who is buying, expanding, or delaying real-world deployment. Particularly valuable in grid, defense, and industrial chains. |
| `patent_filings` | `graph_confirming` | 3 | 4 | 3 | 3 | 4 | `P2` | Good for architecture direction and technical dependence; weak alone for commercialization or timing. |
| `shipping_trade_flow_data` | `graph_confirming` | 4 | 4 | 4 | 4 | 3 | `P2` | Powerful for validating physical dependence and geography concentration when reliably available. |
| `job_postings_hiring_signals` | `graph_suggesting` | 2 | 4 | 3 | 3 | 3 | `P2` | Useful for detecting hidden capacity buildouts or manufacturing focus, but not enough to anchor claims alone. |
| `analyst_note_excerpts` | `graph_confirming` | 3 | 3 | 2 | 4 | 3 | `P2` | Helps identify what the market already believes, not what reality is changing upstream. |
| `investor_posts_high_signal` | `graph_suggesting` | 2 | 5 | 3 | 3 | 2 | `P2` | Very useful for idea discovery and universe construction, but must not anchor production graph edges by itself. |
| `forum_posts_and_comments` | `graph_suggesting` | 1 | 4 | 2 | 2 | 1 | `P3` | Discovery layer only. Good for surfacing hypotheses, not for promotion into picks. |
| `generic_news_roundups` | `graph_confirming` | 2 | 2 | 2 | 3 | 2 | `P3` | Usually downstream of more important sources and rarely early enough to confer edge. |

## Highest-value classes by use case

### For bottleneck discovery

Best classes:

- `government_policy_enforcement`
- `government_industrial_base_awards`
- `industry_bodies_and_standards`
- `company_filings`
- `technical_conference_material`

Why:

- these reveal where capacity, qualification, or policy constraints actually form
- they sit close to physical and regulatory reality
- they alter many downstream graph edges

### For hidden-supplier rerating theses

Best classes:

- `supplier_customer_qualification_releases`
- `company_filings`
- `earnings_transcripts`
- `foreign_exchange_filings`
- `technical_conference_material`

Why:

- these are where ecosystem role and production readiness first become legible
- they help distinguish a real supplier from a promotional adjacency claim

### For geopolitical / event translation

Best classes:

- `government_policy_enforcement`
- `policy_trackers`
- `government_industrial_base_awards`
- `company_filings`
- `trade_press_specialist`

Why:

- they show how policy changes actually transmit into companies, materials, and geographies

### For stock-vs-LEAPS expression selection

Best classes:

- `market_data_snapshot`
- `company_filings`
- `earnings_transcripts`
- `supplier_customer_qualification_releases`
- `technical_conference_material`

Why:

- the expression layer needs both structural context and contract-level evidence
- options should only win when market-data evidence supports the structural thesis

## Ingestion cadence

Cadence should depend on the source’s role in the graph.

| Source class | Cadence | Reason |
| --- | --- | --- |
| `government_policy_enforcement` | `event-driven + weekly sweep` | Policy edges change suddenly and matter immediately. |
| `government_industrial_base_awards` | `event-driven + weekly sweep` | Award flow is sparse but high impact. |
| `company_filings` | `filing-driven + daily watchlist monitoring` | Filings are periodic, but new 8-K / foreign filings can matter intraday. |
| `earnings_transcripts` | `earnings-driven` | Management clarification usually comes in event clusters. |
| `industry_bodies_and_standards` | `monthly + event-driven` | Lower frequency, but very high graph impact when updated. |
| `supplier_customer_qualification_releases` | `daily / event-driven` | Qualification changes can alter hidden supplier edges quickly. |
| `foreign_exchange_filings` | `daily for tracked names` | Many upstream names are outside U.S. coverage. |
| `technical_conference_material` | `conference cycle + event-driven` | Concentrated around major ecosystem events. |
| `market_data_snapshot` | `daily or multi-weekly for watchlist names` | Needed for live expression quality and repricing detection. |
| `trade_press_specialist` | `daily scan` | Useful synthesis layer and early confirmation of theme spread. |

## Parsing rules by source class

The parser should not treat all classes equally.

### `government_policy_enforcement`

Parser should prioritize extracting:

- `PolicyAction`
- `Geography`
- `MaterialInput`
- `ProcessLayer`
- `AFFECTED_BY_EVENT`
- `CONSTRAINED_BY`

### `government_industrial_base_awards`

Parser should prioritize:

- `Event`
- `Facility`
- `ProcessLayer`
- `PublicCompany`
- `EXPANDS_CAPACITY_FOR`
- `AFFECTED_BY_EVENT`

### `company_filings`

Parser should prioritize:

- `PublicCompany`
- `Facility`
- `ProcessLayer`
- `MaterialInput`
- `Customer`
- `SUPPLIED_BY`
- `DEPENDS_ON`
- `CANDIDATE_EXPRESSION_FOR`

### `industry_bodies_and_standards`

Parser should prioritize:

- `System`
- `Subsystem`
- `Component`
- `MaterialInput`
- `ProcessLayer`
- `USED_IN`
- `DEPENDS_ON`

### `market_data_snapshot`

Parser should prioritize:

- `ExpressionCandidate`
- `market_signal` claims
- `REPRICES_VIA`
- `implementation viability`

This is not graph-forming in the same way as policy or filings, but it is
critical for deciding whether the structural thesis deserves stock or options.

## Practical ingestion stack

If we want maximum value with limited time, the order should be:

1. `government_policy_enforcement`
2. `government_industrial_base_awards`
3. `company_filings`
4. `earnings_transcripts`
5. `industry_bodies_and_standards`
6. `supplier_customer_qualification_releases`
7. `foreign_exchange_filings`
8. `market_data_snapshot`
9. `technical_conference_material`
10. `trade_press_specialist`

That stack gives the best mix of:

- structural truth
- early information
- graph centrality
- expression relevance

## What should not dominate the graph

These sources are useful, but should be gated hard:

- `investor_posts_high_signal`
- `forum_posts_and_comments`
- `generic_news_roundups`
- weak analyst-note fragments
- unattributed screenshots

They should mostly be used for:

- hypothesis seeding
- universe expansion
- recognition-dynamics context

They should not be enough on their own to promote a parse into the pick layer.

## Operational recommendation

MiroFish should store two source-priority values for every ingested source:

- `source_priority_tier`
  - `P0`
  - `P1`
  - `P2`
  - `P3`

- `source_role`
  - `graph_forming`
  - `graph_confirming`
  - `graph_suggesting`

That gives the downstream system a simple policy:

- `P0/P1 graph_forming` sources can create or upgrade graph edges directly
- `P1/P2 graph_confirming` sources can strengthen existing edges and claims
- `P2/P3 graph_suggesting` sources can seed research, but not promote picks alone

## Near-term implementation priority

If we want the fastest path to better picks, we should build ingestion around:

1. policy / enforcement
2. filings / transcripts
3. industrial-base awards
4. qualification releases
5. market-data snapshots

That set most directly improves:

- structural parse quality
- promotion quality
- stock-vs-LEAPS choice
- pick credibility

# Bottleneck Ontology V1

Date: March 15, 2026

## Purpose

This document finalizes the first stable ontology for MiroFish research mode.

The ontology is designed for:

- bottleneck discovery
- dependency mapping
- source-backed claims audit
- severity scoring
- value-capture scoring

It is explicitly not the same ontology as the existing social-simulation flow. That older ontology is built around actors and social interaction. This one is built around industrial chains, physical constraints, policy, and public-market expression.

The code-level canonical definition lives in:

- [research_ontology.py](/home/d/codex/MiroFish/backend/app/services/research_ontology.py)

The canonical backend entry points are:

- `build_research_ontology_spec()`
- `build_research_graph_ontology()`
- `validate_research_ontology_spec()`

## Design Rules

1. The ontology must describe real physical or economic dependency layers.
2. It must be broad enough to work across semiconductors, infrastructure, and materials.
3. It must support source-backed claims audit, not just free-form notes.
4. It must keep `severity` and `value capture` conceptually separate.
5. It must map cleanly from the case-study artifact set already in the repo.

## Canonical Entity Types

### Theme

Top-level research narrative or bottleneck theme.

Examples:

- InP photonics
- HBM and advanced packaging
- utility-scale transformers

### MarketDriver

Demand-side or policy-side force increasing stress in the system.

Examples:

- AI data-center load growth
- electrification
- robotics adoption
- export controls

### EndMarket

The final market consuming the constrained system or component.

Examples:

- AI clusters
- defense systems
- EV drivetrain
- transmission infrastructure

### SystemLayer

A top-level deployed system or infrastructure layer.

Examples:

- AI network switch stack
- transformer installation
- liquid-cooled AI rack

### Component

Intermediate module, subsystem, or part within the chain.

Examples:

- CDU
- laser array
- HBM stack
- permanent magnet

### MaterialInput

Raw material, refined input, substrate, or specialty consumable.

Examples:

- NdPr oxide
- dysprosium
- InP substrate
- copper

### BottleneckLayer

The canonical unit of scoring.

This is the layer that gets:

- severity score
- value-capture score

Examples:

- CoWoS-class packaging
- large power transformers
- heavy rare earth supply

### PublicCompany

Listed company with relevant exposure.

Examples:

- MP
- MU
- VRT

### Facility

Physical site or manufacturing location.

Examples:

- Fort Worth magnet facility
- Singapore HBM packaging facility
- specific refinery, fab, or transformer plant

### Geography

Country or region relevant to concentration or policy risk.

Examples:

- China
- United States
- Malaysia

### PolicyAction

Export control, subsidy, industrial-policy action, or standard.

Examples:

- heavy rare earth export control
- CHIPS funding
- DOE transformer program

### CapacityExpansion

Project or investment intended to add qualified supply.

Examples:

- packaging expansion
- refinery buildout
- second magnet facility

### Claim

Structured research claim that can be supported, challenged, or left unverified.

### Source

Primary or secondary source supporting the research graph.

## Canonical Relationship Types

### `DRIVEN_BY`

Connects a theme or bottleneck layer to a demand or policy driver.

### `USED_IN`

Connects material -> component -> system -> end market.

### `DEPENDS_ON`

Captures essential dependency and propagation of constraint.

### `SUPPLIED_BY`

Connects a layer or component to the public company exposed to it.

### `LOCATED_IN`

Connects facilities, companies, or layers to strategic geographies.

### `CONSTRAINED_BY`

Captures policy constraints, qualification issues, or expansion timing.

### `EXPANDS_CAPACITY_FOR`

Connects expansion projects or facilities to the constrained layer they relieve.

### `SUPPORTS_CLAIM`

Connects a source to a claim and records whether the source is supporting, contradictory, or contextual.

### `DESCRIBES`

Connects claims to themes, bottleneck layers, companies, or policies.

### `ALTERNATIVE_TO`

Captures substitutes, competing architectures, or replacement paths.

## Backend Contract

The ontology now has two stable output surfaces:

- `build_research_ontology_spec()`
  This returns the full research contract, including:
  - `entity_types`
  - `relationship_types`
  - `edge_types`
  - `evidence_requirements`
  - `artifact_mapping`
  - `score_dimensions`
  - metadata like ontology name and version
- `build_research_graph_ontology()`
  This returns the reduced payload for the current graph builder:
  - `entity_types`
  - `edge_types`

`edge_types` is intentionally preserved as a first-class key even though the research memo refers to relationships conceptually. This keeps the ontology compatible with the existing graph-builder and graph API contracts.

## Minimum Evidence Requirements

The ontology requires minimum evidence discipline by claim class.

### Market share or concentration

- minimum: 1 strong source
- preferred source class: filing, government, industry body

### Capacity expansion or ramp

- minimum: 1 direct source
- preferred source class: company release, filing, government

### Export control or policy

- minimum: 1 policy-grounded source
- preferred source class: government, policy tracker, filing

### Demand acceleration

- minimum: 1 direct source
- preferred source class: filing, government, company release

### Bottleneck assertion

- minimum: 2 sources
- at least one should describe the constraint directly

### Value-capture assertion

- minimum: 2 sources
- should include evidence of pricing, margin leverage, listed-vehicle purity, or scarcity duration

## Artifact Mapping

The ontology is designed to map directly from the current case-study workflow.

### Thesis intake

Maps into:

- Theme
- MarketDriver
- EndMarket
- BottleneckLayer

### Claims audit

Maps into:

- Claim
- Source
- `SUPPORTS_CLAIM`
- `DESCRIBES`

### Chokepoint scores

Maps into:

- BottleneckLayer
- PublicCompany

### Case-study summary

Maps into:

- Theme
- BottleneckLayer
- PolicyAction
- CapacityExpansion

The stable artifact mapping keys are:

- `thesis-intake`
- `claims-audit`
- `chokepoint-scores`
- `case-study-summary`

## Why This Ontology Is Final Enough

This ontology is now broad enough to cover:

- semiconductors
- photonics
- packaging
- grid infrastructure
- critical minerals
- facility-scale deployment bottlenecks

It is also specific enough to support:

- backend persistence
- API design
- future prompt templates
- frontend research-mode views

The ontology should now be treated as versioned and validated, not inferred informally from case-study prose.

## Next Step

The next step is not more ontology work. It is to use this ontology to define the research project data model and API surface.

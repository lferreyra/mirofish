# Phase 1 Checklist: Bottleneck Research Foundation

Date: March 15, 2026

## Goal

Stabilize the bottleneck-research workflow before modifying the main MiroFish product flow.

Phase 1 is complete only when the research method is repeatable across multiple domains and produces outputs that are specific enough to support later product integration.

## Checklist

### 1. Research Workflow

- [x] Define the core framing: MiroFish as a mispricing-discovery engine
- [x] Define the bottleneck-first strategy model
- [x] Create thesis intake template
- [x] Create claims-audit template
- [x] Create initial chokepoint scoring module
- [ ] Refine scoring weights after more case studies
- [ ] Decide the canonical research artifact set for each case study

### 2. Case Studies

- [x] Complete InP photonics case study
- [x] Complete HBM / advanced packaging case study
- [x] Complete transformers / grid equipment case study
- [x] Complete rare earth magnets / refining case study
- [x] Complete AI cooling / thermal management case study
- [x] Compare case studies side by side to identify recurring signal patterns

### 3. Ontology

- [x] Finalize bottleneck ontology entity set
- [x] Finalize bottleneck ontology relationship set
- [x] Define minimum evidence requirements per claim type
- [x] Define how case-study data should map into graph entities and edges

Canonical ontology artifacts:

- [bottleneck-ontology-v1.md](/home/d/codex/MiroFish/docs/research-frameworks/2026-03-15-bottleneck-ontology-v1.md)
- [research_ontology.py](/home/d/codex/MiroFish/backend/app/services/research_ontology.py)

### 4. Scoring

- [ ] Review whether current weightings overemphasize concentration relative to value capture
- [x] Add value-capture-layer scoring as a separate concept from chokepoint severity
- [ ] Add confidence / evidence-quality scoring
- [ ] Add a falsifier score or uncertainty flag

### 5. Product Integration Readiness

- [ ] Decide whether research mode is a separate workflow or the new default
- [x] Define backend data model for research projects
- [x] Define API surface for thesis intake, claims audit, and scoring
- [ ] Define frontend flow for research mode
- [ ] Decide what parts of the original simulation workflow remain in scope

Canonical backend artifacts:

- [research_project.py](/home/d/codex/MiroFish/backend/app/models/research_project.py)
- [research.py](/home/d/codex/MiroFish/backend/app/api/research.py)
- [research-project-data-model-v1.md](/home/d/codex/MiroFish/docs/research-frameworks/2026-03-15-research-project-data-model-v1.md)

## Exit Criteria

Phase 1 should be considered complete when:

1. at least four diverse case studies exist
2. the scoring model has been revised at least once based on those studies
3. the ontology is stable enough to support backend/API work
4. the canonical research output format is fixed
5. product integration decisions are clear enough to begin implementation

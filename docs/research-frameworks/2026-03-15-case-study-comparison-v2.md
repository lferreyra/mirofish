# Case Study Comparison V2

Date: March 15, 2026

## Scope

This memo re-scores the five completed case studies under the revised dual-score model:

- `severity`: how structurally severe the bottleneck is
- `value capture`: how attractive the likely public-market expression appears

The rescored summary data is stored in:

- [dual-score-rescore-v1.json](/home/d/codex/MiroFish/research/analysis/2026-03-15-dual-score-rescore-v1.json)

## Top Layers By Case

| Case | Top severity layer | Severity | Top value-capture layer | Value capture |
|---|---|---:|---|---:|
| InP photonics | InP substrates | 86.0 | InP laser and external light source capacity | 75.2 |
| HBM / advanced packaging | 2.5D / CoWoS-class advanced packaging capacity | 90.8 | HBM memory stack supply | 93.0 |
| Transformers / grid equipment | Utility-scale power transformers | 88.8 | Utility-scale power transformers | 76.0 |
| Rare earth magnets / refining | Sintered NdFeB permanent magnet manufacturing | 95.6 | Heavy rare earth supply for high-performance magnets | 76.8 |
| AI cooling / thermal management | Coolant distribution and facility-side thermal chain | 80.4 | Coolant distribution and facility-side thermal chain | 79.4 |

## Main Findings

### 1. The score split changed the answer in three of five cases

This is the main proof that the model split was necessary.

Cases where the top structural bottleneck differs from the top value-capture layer:

- InP photonics:
  - severity: substrates
  - value capture: lasers / external light sources
- HBM / advanced packaging:
  - severity: CoWoS-class packaging
  - value capture: HBM memory supply
- Rare earth magnets / refining:
  - severity: finished magnet manufacturing
  - value capture: heavy rare earth supply

Cases where the same layer still wins both:

- transformers / grid equipment
- AI cooling / thermal management

### 2. The old model was over-rewarding bottleneck purity

This is now visible.

Under the single-score model, the framework naturally favored the most concentrated and technically constrained layer. That was useful for diagnosis, but it sometimes pulled attention away from the better listed-market expression.

Examples:

- InP substrates are structurally tighter than the laser layer, but the laser layer scores better on value capture.
- CoWoS packaging looks like the tighter system gate, but HBM vendors still look like the cleaner public-market beneficiary set.

### 3. Some domains still have a single best layer

The split did not create artificial disagreement everywhere.

It still leaves the same top layer in:

- utility-scale power transformers
- facility-side AI cooling and thermal-chain deployment

That is a good sign. The new model is adding discrimination, not noise.

## Cross-Case Pattern Recognition

### Pattern A: the best severity layer is often deeper in the chain

This remains true after the split:

- packaging over generic HBM narrative
- magnet manufacturing over mining
- transformer manufacturing over broad electrification
- facility thermal chain over generic cooling components

### Pattern B: the best value-capture layer is often one step closer to monetization

This is the new recurring pattern.

- InP: device layer beats raw substrate
- HBM: memory vendors beat packaging as listed vehicles
- rare earths: heavy rare earth access looks cleaner than finished magnet concentration

This suggests the workflow should explicitly expect:

`severity winner != value-capture winner`

### Pattern C: state support is a real drag on pure market value capture

The value-capture score penalizes candidates that may be strategically vital but whose economics depend heavily on policy support or may be constrained by state-directed industrial policy.

This mattered especially in:

- rare earth magnets / refining
- some upstream concentration-heavy cases

## What The Revised Model Still Lacks

The split improved the framework, but the next missing dimensions are still:

- evidence quality / confidence
- explicit falsifier or uncertainty scoring
- time-to-resolution or catalyst timing
- public-float / liquidity / options-surface relevance

## Recommended Next Step

The next high-value move is not another case study.

It is:

1. finalize the ontology around the patterns now visible across five cases
2. decide the canonical research project data model
3. begin integrating research mode into the backend

The case-study sample is now large enough to support those decisions.

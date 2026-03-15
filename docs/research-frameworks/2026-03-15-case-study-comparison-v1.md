# Case Study Comparison V1

Date: March 15, 2026

## Scope

This memo compares the first four bottleneck case studies built inside the MiroFish research workflow:

1. InP photonics
2. HBM / advanced packaging
3. transformers / grid equipment
4. rare earth magnets / refining

The goal is not to rank the themes against each other as investment ideas. The goal is to identify what the current scoring model is actually rewarding, where it is useful, and where it is still too blunt.

## Top Candidate By Case

| Case | Top-scoring candidate | Layer | Score | Main drivers |
|---|---|---|---:|---|
| InP photonics | InP substrates | substrate | 86.0 | concentration, geopolitics, qualification friction |
| HBM / advanced packaging | 2.5D / CoWoS-class advanced packaging capacity | packaging | 90.8 | concentration, qualification friction, lead time |
| Transformers / grid equipment | utility-scale power transformers | transmission | 88.8 | concentration, qualification friction, lead time |
| Rare earth magnets / refining | sintered NdFeB permanent magnet manufacturing | magnet manufacturing | 95.6 | concentration, qualification friction, geopolitics |

## What The Workflow Is Doing Well

### 1. It is finding the tightest layer, not just repeating the headline narrative

This is the strongest positive result.

- InP: the workflow did not stop at "AI optics matter" and instead pushed toward the concentrated upstream layer.
- HBM: the workflow elevated advanced packaging above the simpler "HBM shortage" story.
- Transformers: the workflow distinguished large power transformers from the broader transformer theme.
- Rare earths: the workflow pushed past mining toward magnet manufacturing and heavy rare earths.

That means the workflow is already doing something valuable:

`it is decomposing a broad narrative into tighter physical gates`

### 2. It generalizes across very different industries

The same research pattern worked on:

- semiconductors
- photonics
- grid infrastructure
- critical minerals and magnets

That suggests the method is not just overfit to AI semiconductors.

### 3. It is forcing source discipline

The claims-audit step consistently separated:

- supported claims
- unverified claims
- unsupported overreach

This is important because many public bottleneck narratives are partly right but too absolute.

## What The Workflow Is Not Doing Well Enough Yet

### 1. Chokepoint severity and value capture are still mixed together

The current score answers:

- "How severe is this bottleneck candidate?"

It does not answer:

- "How likely is this layer to capture economics in public equities?"

Those are different questions.

Examples:

- InP substrates may be a real chokepoint, but device makers may capture more economics.
- Advanced packaging may be a bottleneck, but the best listed exposure may still be complicated.
- Rare earth magnet manufacturing may be the tightest layer, but some of the diversification economics may be state-supported rather than purely market-priced.

This is the clearest next refinement need.

### 2. The model currently rewards concentration very heavily

Across all four cases, the strongest drivers are almost always:

- supplier concentration
- qualification friction
- capacity lead time or geopolitical exposure

That is directionally reasonable, but it may overweight "scarcity purity" relative to:

- customer captivity
- pricing realization
- ability of listed names to monetize the scarcity
- speed of capacity expansion

### 3. Price expression is still downstream and mostly implicit

Right now the workflow is strong at:

- structural diagnosis
- ranking bottlenecks

It is weaker at:

- mapping which public vehicles best express the thesis
- comparing common equity versus optionality
- distinguishing strategic importance from investable asymmetry

## Cross-Case Pattern Recognition

### Pattern A: the real bottleneck is usually lower in the chain than the public narrative suggests

- InP: not "AI networking" but the concentrated photonics input layer
- HBM: not just memory, but packaging integration
- Transformers: not just electrification, but utility-scale transformer lead times
- Rare earths: not mining, but magnets and heavy rare earth separation

This may be the single most useful strategy rule extracted so far.

### Pattern B: geopolitics matters most when concentration and substitution are both extreme

Geopolitical exposure was especially important in:

- InP substrates
- heavy rare earths
- NdFeB magnet manufacturing

It mattered less in HBM packaging and transformers, where lead time and qualification friction dominated more clearly.

### Pattern C: the current score favors "hard physical bottlenecks"

The workflow is strongest on:

- manufacturing capacity constraints
- physical lead times
- low substitutability
- concentrated processing or fabrication layers

That suggests the framework is currently best suited to:

- industrial and infrastructure bottlenecks
- materials and component bottlenecks

It is less ready for:

- soft concentration
- software dependency
- financial-structure mispricings without a physical chain

## Proposed Model Refinements

The next scoring iteration should split one score into two.

### Score 1: Chokepoint Severity

Keep focused on:

- supplier concentration
- qualification friction
- lead time
- substitutability
- geopolitics
- demand acceleration

### Score 2: Value Capture Potential

Add separate signals for:

- pricing power realization
- listed-vehicle purity
- margin leverage
- balance-sheet ability to expand capacity
- state-support dependence
- risk that scarcity is competed away before economics show up

That would let the workflow say:

- "this is the bottleneck"
- "this is the likely public-market beneficiary"

Those should not be forced into one number.

Update:

- This split has now been implemented in the scoring module as a severity score plus a separate value-capture score.
- The next comparison pass should re-score the existing cases under both dimensions rather than relying on the original single-score outputs.

## What This Means For Phase 1

The first four case studies are enough to justify:

1. a scoring-model revision
2. ontology finalization work
3. movement toward backend data structures for research projects

But they are not yet enough to skip one more test domain. A fifth case would make the refinement more credible, especially if it adds a different bottleneck shape.

## Recommended Next Step

The next move is:

1. re-score the existing cases under the new dual-score model
2. finalize ontology
3. begin product-mode design

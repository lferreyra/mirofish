# Case Study: InP Photonics Bottleneck

Date: March 15, 2026

## Objective

Run the first end-to-end bottleneck research workflow inside MiroFish using the InP photonics thesis as the pilot case.

This case study takes one externally sourced idea and pushes it through:

1. thesis intake
2. claims audit
3. chain reconstruction
4. chokepoint scoring
5. preliminary investment interpretation

## Thesis Seed

The starting hypothesis was that the future AI optical buildout may be constrained by concentration in the indium phosphide substrate and InP-linked photonics supply chain.

This case was selected because it has all the traits of a strong pilot:

- large secular demand driver
- physical dependency chain
- supplier concentration
- qualification friction
- visible geopolitical risk
- plausible public-equity expression

## Workflow Artifacts

- [thesis-intake.md](./thesis-intake.md)
- [claims-audit.csv](./claims-audit.csv)
- [chokepoint-scores.json](./chokepoint-scores.json)

## Chain Reconstruction

The useful dependency chain is:

1. InP substrate suppliers
2. epi / wafer processing
3. InP laser and external light-source capacity
4. optical modules and CPO integration
5. hyperscaler and AI-network demand

The central lesson is that the substrate thesis may be right without substrate suppliers being the best equity expression. A bottleneck can exist at one layer while economics accrue at another.

## Scoring Output

Three adjacent bottleneck candidates were scored:

| Candidate | Layer | Score | Band |
|---|---|---:|---|
| InP substrates | substrate | 86.0 | critical |
| InP laser and external light source capacity | device | 83.2 | critical |
| Optical module and CPO integration | module/system | 69.2 | high |

## Interpretation

### What the workflow found

- The substrate layer scores highest as a pure chokepoint because of concentration and geopolitics.
- The device layer scores almost as high, suggesting the investable bottleneck may sit at qualified laser capacity rather than raw substrate alone.
- The module/system layer still matters, but it looks less extreme as a pure scarcity point.

### What this means

The pilot supports a core MiroFish research principle:

`hidden dependency discovery is not the same thing as final trade selection`

The workflow can identify where fragility sits. A separate step still needs to answer:

- which layer captures pricing power
- which public equity has the cleanest exposure
- whether optionality is cheap or expensive

## Why This Is A Good First Case

This case validates the repo direction because it forced all the important distinctions:

- bottleneck vs value-capture layer
- thesis quality vs pricing quality
- structural importance vs trade expression
- source hypothesis vs primary-source verification

## Reuse Rules

This case-study pattern should now be reused for future themes:

1. start with one strong hypothesis
2. convert it into structured claims
3. verify claims against primary sources
4. score multiple layers of the chain, not just the most obvious one
5. only then decide whether the idea is suitable for equity, LEAPS, or long-vol expression

## Next Candidate Domains

The next best case studies for this workflow are:

- HBM and advanced packaging
- transformers and grid equipment
- rare earth magnets and refining
- AI cooling and power-delivery components

# Case Study: AI Cooling and Thermal Management

Date: March 15, 2026

## Objective

Run the fifth end-to-end bottleneck research workflow inside MiroFish using AI data-center cooling and thermal management as the pilot case.

This case study follows the same workflow as the prior pilots:

1. thesis intake
2. claims audit
3. chain reconstruction
4. chokepoint scoring
5. preliminary investment interpretation

## Thesis Seed

The starting hypothesis was that the real cooling bottleneck in AI infrastructure is not simply "data centers need more cooling." The tighter constraints likely sit in:

1. coolant distribution and facility-side thermal-chain capacity
2. direct-to-chip liquid cooling deployment and rack integration
3. chip-level thermal interfaces and cold-plate performance

This case is useful because it adds another AI-infrastructure bottleneck with a very different shape from photonics and memory:

- thermal rather than electrical or logic bottlenecks
- end-to-end systems integration problems
- service and commissioning complexity
- facility and rack-level physical constraints

## Workflow Artifacts

- [thesis-intake.md](./thesis-intake.md)
- [claims-audit.csv](./claims-audit.csv)
- [chokepoint-scores.json](./chokepoint-scores.json)

## Chain Reconstruction

The useful dependency chain is:

1. chip-level thermal interfaces and cold plates
2. direct-to-chip liquid cooling systems and rack integration
3. coolant distribution units, heat rejection, and fluid-management services
4. facility-scale thermal chain and commissioning
5. high-density AI racks and gigawatt-scale AI factories

The key lesson from this case is that liquid cooling is becoming necessary, but necessity alone does not define the bottleneck. The real gate is more likely to sit in scalable deployment, CDU capacity, and end-to-end thermal-chain execution.

## Scoring Output

Three adjacent bottleneck candidates were scored:

| Candidate | Layer | Score | Band |
|---|---|---:|---|
| Coolant distribution and facility-side thermal chain | facility / distribution | 88.8 | critical |
| Direct-to-chip liquid cooling rack integration | system / rack | 87.2 | critical |
| Chip-level thermal interfaces and cold plates | component | 69.2 | high |

## Interpretation

### What the workflow found

- Facility-side coolant distribution and thermal-chain execution scored highest because liquid cooling at AI-factory scale is increasingly a systems and commissioning problem, not just a component problem.
- Direct-to-chip liquid cooling integration also scored as a critical bottleneck due to rising rack densities, deployment complexity, and the need to retrofit or build around liquid loops.
- Chip-level thermal interfaces and cold plates matter, but currently appear more like a technical-enabler layer than the single most acute bottleneck.

### What this means

This case reinforces another MiroFish research rule:

`when a technology becomes mandatory, deployment infrastructure often becomes the bottleneck`

Liquid cooling is moving from optional performance enhancement to required infrastructure. The more investable bottleneck may therefore sit in:

- CDUs
- heat rejection systems
- fluid management and commissioning services
- end-to-end thermal-chain deployment

rather than only in chip-adjacent components.

## Why This Is A Good Fifth Case

This case matters because it shows the workflow can handle:

- systems integration bottlenecks
- service-heavy bottlenecks
- facility-side complexity

That broadens the framework beyond simple component concentration stories.

## Most Important Follow-Up Questions

- Which listed companies have the cleanest exposure to CDU and thermal-chain scale-up rather than generic data-center infrastructure?
- How fast does liquid cooling move from premium deployment to default deployment across AI buildouts?
- Does services and commissioning become a bigger value-capture layer than hardware alone?
- Which cooling layer will retain pricing power once more vendors scale capacity?

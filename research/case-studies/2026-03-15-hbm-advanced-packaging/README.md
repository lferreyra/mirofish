# Case Study: HBM and Advanced Packaging

Date: March 15, 2026

## Objective

Run the second end-to-end bottleneck research workflow inside MiroFish using HBM and advanced packaging as the pilot case.

This case study applies the same workflow used in the InP photonics study:

1. thesis intake
2. claims audit
3. chain reconstruction
4. chokepoint scoring
5. preliminary investment interpretation

## Thesis Seed

The starting hypothesis was that AI accelerator scaling may be constrained not just by HBM supply itself, but by the broader stack that enables HBM deployment at scale:

1. qualified HBM memory-stack supply
2. 2.5D / CoWoS-class advanced packaging capacity
3. advanced substrates and packaging materials

This was selected as the next pilot because it is one of the clearest AI infrastructure bottleneck themes and offers a useful contrast with the InP study. Unlike the photonics case, this one centers on a more visible supply chain with stronger existing market awareness, which makes it a good test of whether the workflow can still identify the true constraint layer.

## Workflow Artifacts

- [thesis-intake.md](./thesis-intake.md)
- [claims-audit.csv](./claims-audit.csv)
- [chokepoint-scores.json](./chokepoint-scores.json)

## Chain Reconstruction

The useful dependency chain is:

1. HBM memory vendors and qualified HBM4/HBM3E output
2. 2.5D / CoWoS-class advanced packaging capacity
3. advanced substrates and packaging materials
4. GPU / ASIC package integration
5. hyperscaler AI demand

The key lesson from this case is that "HBM is tight" is not specific enough. Public evidence supports a more precise statement:

`HBM and advanced packaging are both constrained, and the real limiting factor can shift between memory-stack supply and packaging capacity depending on the point in the ramp.`

## Scoring Output

Three adjacent bottleneck candidates were scored:

| Candidate | Layer | Score | Band |
|---|---|---:|---|
| HBM memory stack supply | memory | 88.8 | critical |
| 2.5D and CoWoS-class advanced packaging capacity | packaging | 90.8 | critical |
| Advanced substrates and packaging materials | substrate/materials | 65.2 | high |

## Interpretation

### What the workflow found

- Advanced packaging capacity scored slightly higher than memory-stack supply because public evidence points to extreme qualification friction and long lead times at the 2.5D / CoWoS layer.
- HBM memory supply also scored as a critical chokepoint due to the small set of qualified vendors and the intensity of AI demand.
- Advanced substrates and packaging materials matter, but currently look more like an enabling layer than the single most acute bottleneck.

### What this means

This case supports a stronger MiroFish research principle:

`the loudest bottleneck in market narrative is not always the most binding bottleneck in the system`

HBM is the headline. Advanced packaging may be the tighter gate.

That matters for investing because the obvious trade expression is not always the best one:

- memory vendors may capture the HBM scarcity premium
- foundry / packaging players may capture the integration bottleneck
- substrate/material names may benefit later as ecosystems scale

## Why This Is A Good Second Case

This case validates the workflow in a more crowded theme:

- the bottleneck is already broadly recognized
- there are multiple adjacent chokepoints
- capacity expansion is visibly underway
- the public-equity expression is not straightforward

That makes it a better stress test than a niche upstream idea alone.

## Reuse Rules

The same pattern from the first case study holds here:

1. convert the broad narrative into a layered chain
2. verify claims against primary sources
3. score multiple layers, not just the most obvious one
4. keep bottleneck ranking separate from trade expression

## Most Important Follow-Up Questions

- Is packaging capacity or HBM bit supply the tighter constraint over the next 12 to 24 months?
- Which public company has the cleanest economic exposure to the bottleneck layer rather than just thematic association?
- How quickly do current capacity expansions reduce tightness?
- Do advanced substrates become a first-order bottleneck as package complexity increases further?

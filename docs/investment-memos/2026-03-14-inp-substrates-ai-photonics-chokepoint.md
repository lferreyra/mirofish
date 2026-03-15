# InP Substrates As An AI/Photonics Chokepoint

Date: March 14, 2026

## Origin Of Thesis

This memo was prompted by a December 26, 2025 X thread from `@aleabitoreddit`, which argued that AXT and Sumitomo could represent a critical InP substrate chokepoint for the AI optical buildout.

That thread is treated here as the originating hypothesis, not as a primary evidence source. All material claims in this memo are intended to be evaluated against filings, company releases, or other directly attributable sources.

## Executive Summary

The core thesis is credible: indium phosphide (InP) substrates appear to be a concentrated upstream input into parts of the AI optical stack, and that concentration is relevant as hyperscaler networking shifts toward photonics. The strongest version of the thesis, however, is overstated. Public evidence supports "concentrated chokepoint risk" far better than "two companies can freeze the entire AI industry."

The most important investment implication is not simply that InP is scarce. It is that future AI optical scaling may be constrained by a narrow band of suppliers across the substrate, laser, packaging, and module layers, with geopolitical risk amplified by AXT's China manufacturing footprint. For LEAPS-style investing, this points to a chain-level research problem rather than a single-ticker conclusion.

## Thesis

AI networking is moving toward higher-bandwidth optical interconnects, including silicon photonics and co-packaged optics. InP is a key material for lasers and photonic devices used in that stack. Public filings and industry materials suggest the InP substrate market remains concentrated, with Sumitomo, AXT, and JX accounting for most of the market. If demand for AI optics ramps faster than qualified supply can expand, InP-related components could become a real bottleneck.

The durable thesis is:

`AI optical scaling rises -> dependence on InP-linked components rises -> concentrated supply and qualification constraints tighten -> selected suppliers gain pricing power and strategic importance`

## What The Public Record Supports

### 1. The InP substrate market is concentrated

AXT/Tongmei's 2022 prospectus, citing Yole, gave 2020 InP substrate shares as:

- Sumitomo Electric: 42%
- Tongmei / AXT: 36%
- JX Nippon: 13%
- Others: 10%

That is enough concentration to matter.

Source:
- https://www.sec.gov/Archives/edgar/data/1051627/000155837022011572/axti-20220801xex99d1.htm

### 2. AXT directly links InP demand to AI and data-center optical demand

AXT's March 31, 2025 10-Q states that indium phosphide substrates are used for:

- optical communications
- data center connectivity
- AI applications
- photonic integrated circuits
- silicon photonics

This matters because it ties the material directly to the AI optical buildout rather than only legacy telecom uses.

Source:
- https://www.sec.gov/Archives/edgar/data/1051627/000155837025007751/axti-20250331x10q.htm

### 3. Hyperscaler and AI networking are moving toward photonics

NVIDIA announced Spectrum-X Photonics and Quantum-X Photonics switches on March 18, 2025, positioning silicon photonics and co-packaged optics as infrastructure for scaling AI factories. NVIDIA's announcement named Coherent, Lumentum, and Sumitomo Electric in its ecosystem.

Broadcom announced third-generation co-packaged optics on May 15, 2025, pushing 200G per lane optical interconnect further into the AI stack.

Sources:
- https://investor.nvidia.com/news/press-release-details/2025/NVIDIA-Announces-Spectrum-X-Photonics-Co-Packaged-Optics-Networking-Switches-to-Scale-AI-Factories-to-Millions-of-GPUs/default.aspx
- https://investors.broadcom.com/news-releases/news-release-details/broadcom-announces-third-generation-co-packaged-optics-cpo

### 4. The geopolitical risk is real

AXT's 2024 10-K and 2025 10-Q disclose that China added InP substrates to its export-control list on February 4, 2025. AXT also states that all of its wafer substrates are manufactured in China.

That makes AXT more than a normal small-cap supplier. It creates a national-security and trade-friction dimension to the thesis.

Sources:
- https://www.sec.gov/Archives/edgar/data/1051627/000155837025003004/axti-20241231x10k.htm
- https://www.sec.gov/Archives/edgar/data/1051627/000155837025007751/axti-20250331x10q.htm

### 5. The market is already responding with capacity investment

This is where the most extreme version of the thesis weakens.

Coherent announced 6-inch InP wafer fabs in Texas and Sweden in March 2024. In September 2025 it also said the Sherman 6-inch InP fab should increase production capacity by more than 5x for InP lasers.

JX Advanced Metals announced in July 2025 that it would invest about JPY 1.5 billion to increase InP substrate capacity by about 20%, citing generative AI and hyperscale data-center optical demand.

Lumentum announced in August 2025 that it was expanding U.S. manufacturing for AI-driven co-packaged optics and identified its UHP laser for CPO as an indium phosphide product.

Sources:
- https://www.coherent.com/news/press-releases/worlds-first-6-inch-inp-scalable-wafer-fabs-paving-the-way-for-the-next-generation-of-lasers-for-ai-transceivers-and-6g-wireless-networks
- https://www.coherent.com/news/press-releases/coherent-samples-low-noise-400mw-cw-lasers.html
- https://www.jx-nmm.com/english/newsrelease/2025/07/23/upload_files/Notice_Regarding_Capital_Investment_for_Increased_Production_of_Crystal_Materials_%28Acquisition_of_Fixed_Assets%29.pdf
- https://investor.lumentum.com/financial-news-releases/news-details/2025/Lumentum-Expands-U-S--Manufacturing-for-AI-Driven-Co-Packaged-Optics/
- https://www.lumentum.com/en/products/data-center/cw-lasers/uhp-lasers-cpo

## What Is Likely Overstated

The social-media thesis becomes too aggressive in four places:

### 1. "Two companies can freeze the entire AI industry"

The evidence does not support this literally. It supports a concentrated upstream risk, not a proven binary single-point-of-failure.

### 2. The exact bottleneck layer may not be substrates

Even if substrate supply is tight, the practical choke point may instead be:

- epitaxy
- laser-device yields
- external light-source packaging
- module assembly
- qualification cycles
- co-packaged optics system integration

The profitable layer is not automatically the rawest upstream layer.

### 3. TPU-specific claims remain partly inferential

Google publicly documents optical circuit switching and high-bandwidth pod interconnect in TPUs, but the strongest "TPU v7 created unprecedented InP strain" version is not something I could verify from primary sources.

Sources:
- https://docs.cloud.google.com/tpu/docs/v5p
- https://docs.cloud.google.com/tpu/docs/tpu7x
- https://cloud.google.com/blog/products/compute/introducing-trillium-6th-gen-tpus

### 4. The market is not static

If Coherent, JX, Sumitomo, Lumentum, and others expand qualified capacity fast enough, the bottleneck may ease before it becomes economically explosive.

## Supply Chain View

The useful chain map is:

1. InP substrate suppliers
2. epi / wafer processing
3. laser and photonic device makers
4. optical module and transceiver vendors
5. network switch / CPO / silicon photonics platform providers
6. hyperscalers and AI system builders

This matters because value capture can shift by layer:

- the substrate layer may have scarcity
- the device layer may have better margins
- the module layer may have the customer relationship
- the system layer may have the headline narrative but not the best economics

## Investment Framing

### Base thesis

InP is a real strategic input into the AI optical stack, and concentration plus geopolitics make it worth tracking as a bottleneck candidate.

### Better framing than the viral post

The right question is not:

"Will AXT and Sumitomo control the fate of all AI?"

The right question is:

"As AI interconnect demand shifts toward photonics, which qualified suppliers gain pricing power, strategic leverage, or capacity advantage at the tightest layer of the chain?"

### Why this could matter for LEAPS

This is potentially a multi-year buildout theme driven by:

- hyperscaler capex
- optical bandwidth scaling
- CPO adoption
- silicon photonics adoption
- export controls
- domestic manufacturing incentives

That is structurally better for LEAPS than a short-horizon trade.

## Scenario Framework

### Bull case

- AI optical demand accelerates faster than expected
- InP-related supply stays tight through qualification delays
- non-China capacity ramps slowly
- pricing power shifts to qualified upstream/device vendors
- investors re-rate chokepoint names as strategic assets

Most likely beneficiaries:

- AXT if export risk is contained
- Sumitomo if customers prioritize scale and qualification
- JX if incremental capacity lands into a tight market
- Coherent / Lumentum if the bottleneck is monetized better at the device layer

### Base case

- InP remains strategically important
- demand grows strongly
- capacity expansions partially relieve bottlenecks
- pricing improves, but not enough to create a catastrophic global shortage
- value accrues unevenly across the stack

### Bear case

- capacity ramps faster than expected
- alternate architectures reduce dependence on the narrowest InP layers
- customer multi-sourcing improves
- optical adoption is slower than the market expects
- the thesis becomes directionally true but not especially profitable

## Watchlist

### Raw / substrate exposure

- AXT
- Sumitomo Electric
- JX Advanced Metals

### Device / laser / module exposure

- Lumentum
- Coherent
- Broadcom
- Intel

### System / demand-side exposure

- NVIDIA
- Google
- Meta
- Microsoft
- Amazon

## Key Open Questions

These determine whether the thesis is investable or just interesting:

1. How hard is it for a customer to qualify a new InP substrate supplier?
2. Is substrate availability actually the limiting step, or is it downstream device capacity?
3. How much future AI optical demand is truly InP-dependent?
4. Which layer of the chain captures the economics of tight supply?
5. How much does AXT's China exposure discount the value of its strategic role?
6. How quickly can JX, Coherent, Lumentum, and Sumitomo add real qualified output?

## Conclusion

The viral thesis is directionally right and literally overstated.

The strongest conclusion supported by public evidence is:

- InP is important to the AI optical stack
- supply is concentrated
- AXT introduces meaningful geopolitical risk
- capacity response is underway
- the real investable question is which layer of the chain captures value during tightening

That makes InP a strong candidate for a long-duration supply-chain bottleneck research program. It does not yet justify the simple claim that two companies can "freeze the global AI buildout."

## Next Steps

The highest-value follow-up work would be:

1. Build a supplier map by layer: substrate -> laser -> module -> CPO -> hyperscaler
2. Track every public capacity expansion and qualification announcement
3. Separate China-exposed capacity from non-China capacity
4. Compare market caps to bottleneck importance across the chain
5. Model bull / base / bear adoption paths for CPO and silicon photonics

# Graduation Calibration Controls v1

## Purpose

Review how the graduation system behaves across different case types:

- positive control
- boundary-case promotion
- exploratory thesis before and after corroboration
- low-volatility false-positive controls

## Cases

### Positive Control

`MP`

- [graduation](/home/d/codex/MiroFish/research/analysis/2026-03-16-mp-magnet-sovereignty-graduation-v1.json)
- status: `pick_candidate`
- weighted score: `96.1`

Interpretation:

- clean high-conviction structural bottleneck case
- strong source mix
- strong market-miss quality
- obvious expression path

### Boundary Promotion

`SIVE v1 -> v2`

- [v1 graduation](/home/d/codex/MiroFish/research/analysis/2026-03-16-sive-photonics-graduation-v1.json)
- [v2 graduation](/home/d/codex/MiroFish/research/analysis/2026-03-16-sive-photonics-graduation-v2.json)

Result:

- `watchlist_candidate -> pick_candidate`
- `84.45 -> 92.89`

Interpretation:

- promoted only after independent ecosystem corroboration
- good calibration test of whether source mix matters
- still a warning that corroboration can move borderline names quickly

### Exploratory Thesis Promotion

`robotics actuation v1 -> v2`

- [v1 graduation](/home/d/codex/MiroFish/research/analysis/2026-03-16-robotics-actuation-graduation-v1.json)
- [v2 graduation](/home/d/codex/MiroFish/research/analysis/2026-03-16-robotics-actuation-graduation-v2.json)

Result:

- `exploratory_only -> pick_candidate`
- `58.96 -> 94.86`

Interpretation:

- original failure was mostly source quality
- corroboration moved the thesis cleanly into promotion
- useful proof that the system can upgrade a real structural thesis rather than only rank static ideas

### Low-Volatility False-Positive Controls

`KO`

- [graduation](/home/d/codex/MiroFish/research/analysis/2026-03-16-ko-defensive-baseline-graduation-v1.json)
- status: `exploratory_only`
- weighted score: `64.95`
- source mix: `89.0`
- market-miss quality: `34.67`

`XLU`

- [graduation](/home/d/codex/MiroFish/research/analysis/2026-03-16-xlu-defensive-etf-baseline-graduation-v1.json)
- status: `exploratory_only`
- weighted score: `64.62`
- source mix: `92.0`
- market-miss quality: `40.5`

`AFL`

- [graduation](/home/d/codex/MiroFish/research/analysis/2026-03-16-afl-insurance-baseline-graduation-v1.json)
- status: `exploratory_only`
- weighted score: `65.01`
- source mix: `84.0`
- market-miss quality: `43.0`

Interpretation:

- strong source quality alone is not enough to promote
- low-asymmetry defensive ideas are being rejected where they should be
- the system is currently much more sensitive to market-miss and structural depth than to mere polish

## Current Read

This is a healthier calibration picture than we had before:

- `MP`: promotes as expected
- `SIVE`: borderline but promotable with independent corroboration
- `robotics`: promotable after real evidence upgrade
- `KO`, `XLU`, `AFL`: do not promote despite strong official source mix

## Remaining Risk

The remaining calibration gap is not “everything promotes.”

The remaining risk is narrower:

- a thesis with decent structure and improved source mix may still cross quickly
- especially if the market-miss inference is written too generously

So the next best calibration stress test would be:

- a medium-quality structural thesis
- with excellent source mix
- but weak economics or poor expression quality

That would test whether the system overpromotes `plausible structure` even when the practical investment case is weak.

"""
Evaluation harness. Turns a MiroFish simulation into a measurable,
reproducible experiment.

Layout:
    datasets/     (seed.md, question.md, truth.json) per case
    runner.py     CLI entry — score one case
    ablation.py   CLI entry — run the case with Phase-2/4 features toggled
    scoring.py    pure functions: directional / magnitude / calibration
    verdict.py    turn a simulation's end state into a Verdict
    pipeline.py   orchestrate MemoryManager + personas for one case
    determinism.py seed-pinning + temperature clamp helpers
    mocks.py      deterministic mock LLM router + backend for CI
    storage.py    jsonl store of past eval runs (for the dashboard)

Any change to the scoring weights, verdict extractor, or mock router
changes the reference deterministic output — bump `DETERMINISTIC_VERSION`
in `determinism.py` so the CI regression test catches drift.
"""

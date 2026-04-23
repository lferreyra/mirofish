# Evaluation Datasets

Each subdirectory is one dataset case. Files:

- `seed.md` — the document MiroFish ingests (policy announcement, product
  launch, election profile, etc.). Free-form markdown; treated as opaque
  input by the pipeline.
- `question.md` — the prediction target. Single-paragraph phrasing of what
  the simulation is being asked to forecast.
- `truth.json` — ground truth for scoring:
  ```json
  {
    "direction": "positive" | "negative" | "neutral",
    "magnitude": 0.0..1.0,      // strength of the historical signal
    "confidence": 0.0..1.0,     // how strong/clean the ground-truth evidence is
    "notes": "short pointer to source or rationale"
  }
  ```

> These cases are **starter fixtures**, not peer-reviewed historical datasets.
> They exist to exercise the eval pipeline deterministically. Replace with
> real-world cases (with citations) before publishing benchmark numbers.

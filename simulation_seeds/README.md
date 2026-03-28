# Simulation Seeds

Seed documents for MiroFish simulations. Each file provides the source material that MiroFish processes through its 5-step pipeline: graph construction → agent profile generation → simulation → report → interaction.

## How to Use

1. Start MiroFish: `npm run dev` from the project root
2. Open `http://localhost:3000`
3. Upload the seed `.md` file in Step 1 (Graph Building)
4. Set the simulation requirement from the file's **SIMULATION QUESTION** section
5. Follow the 5-step workflow

## Naming Convention

```
<topic>_<type>_sim.md
```

- `topic` — the subject being simulated (e.g. `review_insights`, `red_chamber`, `policy_name`)
- `type` — the simulation category:
  - `market` — product/business PMF and monetization
  - `opinion` — public opinion and social dynamics
  - `narrative` — story or fictional outcome prediction
  - `policy` — policy impact analysis
  - `personal` — personal/experimental scenarios

## Seeds

| File | Topic | Type | Description |
|---|---|---|---|
| `review_insights_market_sim.md` | Review Insights | market | Shopify merchant swarm simulation for PMF, adoption curves, and path to $10K MRR |

## Seed Document Structure

Each seed should contain:

1. **THE PRODUCT / SUBJECT** — detailed description of what's being simulated
2. **THE MARKET / CONTEXT** — competitive landscape, environment, background
3. **THE PERSONAS** — agent archetypes with motivations, pain points, behaviors
4. **SIMULATION QUESTION** — specific predictions to extract from the simulation
5. **SIMULATION PARAMETERS** — platform type, agent count, rounds, mid-sim variable injections

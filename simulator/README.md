# MiroFish × BMNR Simulator

**Agent-based stock simulator for BitMine (BMNR) powered by LLM swarm intelligence.**

A fork of [MiroFish](https://github.com/666ghj/MiroFish) adapted for financial market simulation. Instead of predicting outcomes with formulas, 21 AI agents with distinct personas reason collectively about BMNR's future — and predictions emerge from their interactions.

> **Not financial advice.** This is an educational simulation tool. Not affiliated with BitMine Immersion Technologies, Tom Lee, ARK Invest, or any entity mentioned. Agent personas are fictional archetypes.

---

## What It Does

| Feature | Description |
|---------|-------------|
| **Live Market Data** | Fetches BMNR price, ETH price, mNAV, holdings from bitminetracker.io on every load |
| **21 AI Agents** | ARK/Cathie, Tom Lee, short sellers, Reddit bulls, WSB degens, arb bots — each with detailed personas |
| **LLM Reasoning** | Each quarter, agents reason via LLM about the market state — not programmed formulas |
| **25 Market Stimuli** | Toggle events (ETH rally, SEC crackdown, MAVAN launch) with adjustable intensity |
| **Flywheel Math** | Real ATM issuance mechanics: NAV calc → breakeven check → share issuance → ETH/share accretion |
| **3 Scenarios** | Bear / Base / Bull with overlaid comparison charts |
| **Multi-LLM** | Pluggable providers: Anthropic, OpenAI, Google Gemini, OpenRouter, Ollama (local), or custom |
| **Formula Fallback** | Instant results via network-propagation math when LLM is unavailable |

---

## Quick Start

### Option 1: Claude.ai Artifact (zero setup)

Copy the contents of `src/App.jsx` into a Claude.ai artifact. It runs immediately — the Anthropic API is available inside artifacts with no API key.

### Option 2: Self-Host

```bash
git clone https://github.com/mikema-rgb/BMNR-Mirofish.git
cd BMNR-Mirofish
cp .env.example .env        # Edit with your API key
npm install
npm run dev                  # Opens at http://localhost:3000
```

### Option 3: Any LLM

Edit `.env` to use your preferred provider:

```env
# OpenAI
VITE_LLM_PROVIDER=openai
VITE_OPENAI_API_KEY=sk-...

# Google Gemini
VITE_LLM_PROVIDER=gemini
VITE_GEMINI_API_KEY=AIza...

# Ollama (local, free, no key)
VITE_LLM_PROVIDER=ollama
VITE_OLLAMA_BASE_URL=http://localhost:11434

# OpenRouter (100+ models)
VITE_LLM_PROVIDER=openrouter
VITE_OPENROUTER_API_KEY=sk-or-...

# Any OpenAI-compatible endpoint
VITE_LLM_PROVIDER=custom
VITE_CUSTOM_BASE_URL=https://your-endpoint.com
VITE_CUSTOM_API_KEY=your-key
```

---

## Architecture

```
BMNR-Mirofish/
├── src/
│   ├── App.jsx                 # Main component (monolith — runs standalone)
│   ├── main.jsx                # React entry point
│   ├── config/
│   │   └── index.js            # Simulation config, scenario metadata, fallback data
│   ├── data/
│   │   ├── agents.js           # 21 agent personas (the core of MiroFish)
│   │   └── stimuli.js          # 25 market event definitions
│   ├── engine/
│   │   └── prompts.js          # LLM prompt builder (fork this for other stocks)
│   └── providers/
│       └── index.js            # LLM provider abstraction (Anthropic, OpenAI, etc.)
├── .env.example                # Environment config template
├── package.json
├── vite.config.js
└── README.md
```

### How MiroFish Works (vs. Traditional Models)

| | Traditional Monte Carlo | Formula Agent Model | **MiroFish LLM Agents** |
|---|---|---|---|
| How price moves | `price × exp(drift + vol × dW)` | Sentiment formulas drive returns | LLM reasons about what agents would do |
| Agent behavior | None — just noise terms | Programmed bias + susceptibility | Natural language persona → LLM reasoning |
| Emergent effects | None | Limited network propagation | Herding, contrarianism, cascade failures |
| Stimulus response | Hardcoded impact numbers | Type-weighted sensitivity | LLM interprets event for each persona |
| Surprise factor | None — deterministic given seed | Low — formulas are predictable | High — LLM reasoning can produce unexpected cascades |

### The Simulation Loop

Each quarter:

1. **Agent Selection** — 8 core agents + 3 rotating guests are selected
2. **Prompt Construction** — Market state, stimuli, prior quarter narrative, and agent personas are assembled into a prompt
3. **LLM Call** — The prompt is sent to the configured LLM provider
4. **Response Parsing** — JSON output is extracted with markdown fence stripping and brace-counting fallback
5. **Market Update** — LLM-derived ETH price change and mNAV change are applied (clamped to ±50% per quarter)
6. **Flywheel Engine** — If mNAV > breakeven, ATM shares are issued, ETH is purchased, ETH/share updates
7. **State Propagation** — The quarter narrative feeds into the next round as context

---

## How to Extend

### Add a New Agent

Edit `src/data/agents.js`:

```javascript
{
  id: "your_agent",
  name: "Your Agent Name",
  type: "Institutional",      // or Retail, Quant, Macro, Analyst, etc.
  icon: "🎯",
  bias: 0.2,                  // -1 (bearish) to 1 (bullish) for formula fallback
  influence: 0.5,             // 0-1: how much they sway others
  susceptibility: 0.3,        // 0-1: how much they follow the herd
  memory: 0.6,                // 0-1: how much past rounds carry forward
  persona: "You are... [detailed natural language persona]. You believe... You react to..."
}
```

The persona is the most important field — write it like you're briefing a method actor.

### Add a New Stimulus

Edit `src/data/stimuli.js`:

```javascript
{
  id: "your_event",
  name: "Your Event Name",
  cat: "ETH",                  // Category for filtering
  icon: "⚡",
  impact: 0.5,                // -1 to 1 for formula fallback
  desc: "Short description"
}
```

### Add a New LLM Provider

Edit `src/providers/index.js`:

```javascript
export const YourProvider = {
  id: "your_provider",
  name: "Your Provider",
  models: ["model-1", "model-2"],
  defaultModel: "model-1",
  requiresKey: true,

  async call(messages, { model, maxTokens, apiKey } = {}) {
    // Make your API call here
    // Return { text: string, raw: any }
    const res = await fetch("https://your-api.com/v1/chat", { ... });
    const data = await res.json();
    return { text: data.output, raw: data };
  }
};

// Register it:
export const PROVIDERS = {
  ...existingProviders,
  your_provider: YourProvider,
};
```

### Fork for Another Stock

The simulator is designed to be adapted. To fork for a different stock:

1. Replace agent personas in `src/data/agents.js` with archetypes relevant to your stock
2. Replace stimuli in `src/data/stimuli.js` with events that affect your stock
3. Update `src/config/index.js` with fallback market data for your stock
4. Modify `src/engine/prompts.js` to reference your stock's specific dynamics (the flywheel mechanics are BMNR-specific — replace with whatever drives your stock's value)
5. Update the live data fetcher in `src/App.jsx` to pull from relevant data sources

---

## Acknowledgments

- **[MiroFish](https://github.com/666ghj/MiroFish)** — the original swarm intelligence engine by Shanda Group. This project adapts their agent-based simulation concept for financial markets.
- **[OASIS](https://github.com/camel-ai/oasis)** — the underlying social simulation platform that powers MiroFish.
- **[Wedge](https://wedge.so)** — the BMNR flywheel model and design system.
- **[bitminetracker.io](https://bitminetracker.io)** — live BMNR market data.

---

## Contributing

PRs welcome. The most impactful contributions:

- **Better agent personas** — if you can write a more realistic persona for any of the 21 agents, that directly improves simulation quality
- **New stimuli** — market events we haven't thought of
- **New LLM providers** — expand the provider abstraction
- **Prompt engineering** — improvements to `src/engine/prompts.js` that produce more realistic agent reasoning
- **UI improvements** — better charts, mobile responsiveness, dark mode
- **Other stocks** — fork and adapt for MSTR, COIN, or any other stock with similar dynamics

---

## License

MIT — same as MiroFish.

---

<p align="center">
  <strong>WEDGE × MIROFISH × BMNR</strong><br>
  <em>Educational only. Not financial advice.</em>
</p>

# Contributing to MiroFish BMNR

Thanks for your interest. Here's how to help.

## High-Impact Contributions

These directly improve simulation accuracy:

### Agent Personas
Edit `src/data/agents.js`. The `persona` field is a natural-language prompt sent to the LLM. The richer and more specific the persona, the better the agent reasons. Think of it like briefing a method actor — give them a backstory, investment philosophy, emotional triggers, and decision-making framework.

### Stimuli
Edit `src/data/stimuli.js`. Add market events that affect BMNR. Each stimulus needs an `id`, `name`, `cat` (category), `icon`, `impact` (-1 to 1), and `desc`.

### Prompt Engineering
Edit `src/engine/prompts.js`. This constructs the prompt sent to the LLM each round. Small changes here can dramatically change output quality. Test with multiple providers — what works for Claude may not work for GPT-4o.

### LLM Providers
Edit `src/providers/index.js`. Add new providers by implementing the `call(messages, options)` interface. Return `{ text, raw }`.

## Development Setup

```bash
git clone https://github.com/mikema-rgb/BMNR-Mirofish.git
cd BMNR-Mirofish
cp .env.example .env
npm install
npm run dev
```

## Pull Request Guidelines

- Keep PRs focused — one feature or fix per PR
- Test with at least 2 LLM providers if changing prompts
- Update README if adding new features
- Add your agent / stimulus to the appropriate data file, not to App.jsx

## Code Style

- No build tooling beyond Vite
- Functional React with hooks, no class components
- Inline styles using the `T` design token object (Wedge system)
- Keep App.jsx as a working monolith — it needs to run as a Claude artifact

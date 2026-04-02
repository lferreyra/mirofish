/**
 * Simulation Configuration
 * 
 * SIM_ROUNDS: Number of quarters to simulate (8 = 2 years)
 * SCENARIOS: Bear/Base/Bull case metadata
 * FALLBACK_DATA: Cached BMNR market data (updated when live fetch fails)
 */

export const SIM_ROUNDS = 8;

export const SCENARIOS = {
  bear: { label: "BEAR", color: "#c84b31", desc: "ETH collapses, dilution spiral, premium vanishes" },
  base: { label: "BASE", color: "#005f99", desc: "ETH $2-3K, MAVAN launches, moderate growth" },
  bull: { label: "BULL", color: "#007a3d", desc: "ETH breaks ATH, Alchemy 5% hit, staking revenue" },
};

// Last-known-good BMNR data. Updated by live fetch on load.
// Source: bitminetracker.io — update these when committing.
export const FALLBACK_DATA = {
  price: 23.37,
  ethPrice: 2314.60,
  ethBalance: 4595563,
  shares: 530621703,
  nav: 22.57,
  mNAV: 1.04,
  staked: 3040483,
  avgCost: 3753.88,
  cash: 1.2e9,
  beast: 0.2e9,
  btcVal: 196 * 85000,
  analystLo: 30,
  analystHi: 39,
  w52Lo: 3.20,
  w52Hi: 161,
  fetchedAt: null,
  isLive: false,
};

// Default LLM provider config
export const DEFAULT_PROVIDER = "anthropic";
export const DEFAULT_MODEL = "claude-sonnet-4-20250514";

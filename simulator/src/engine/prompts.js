/**
 * MiroFish Prompt Builder
 * 
 * Constructs the prompt sent to the LLM each simulation round.
 * This is the most important file for simulation accuracy —
 * the quality of the prompt directly determines the quality
 * of agent reasoning.
 * 
 * Fork this to customize for other stocks / assets.
 */

import { AGENTS, CORE_AGENT_IDS } from "../data/agents.js";
import { STIMULI } from "../data/stimuli.js";

function fN(n) {
  if (!isFinite(n)) return "—";
  if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(2) + "M";
  if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(1) + "K";
  return n.toFixed(0);
}

/**
 * Select which agents to poll this round.
 * Core agents are always included; others rotate.
 */
export function selectRoundAgents(roundNum) {
  const rotatingIds = AGENTS.filter(a => !CORE_AGENT_IDS.includes(a.id)).map(a => a.id);
  const start = ((roundNum - 1) * 3) % rotatingIds.length;
  const extras = [0, 1, 2].map(i => rotatingIds[(start + i) % rotatingIds.length]);
  const ids = [...new Set([...CORE_AGENT_IDS, ...extras])];
  return AGENTS.filter(a => ids.includes(a.id));
}

/**
 * Build the user message for a simulation round.
 */
export function buildRoundPrompt(roundNum, totalRounds, marketState, activeStimuli, prevSummary, scenarioMode) {
  const stimDesc = activeStimuli.map(s => {
    const st = STIMULI.find(x => x.id === s.id);
    return st ? `${st.name} (${(s.intensity || 1).toFixed(1)}x) — ${st.desc}` : "";
  }).filter(Boolean).join("; ");

  const roundAgents = selectRoundAgents(roundNum);
  const agentList = roundAgents.map(a =>
    `- ${a.name} [id:${a.id}] (${a.type}): ${a.persona.split(".").slice(0, 2).join(".")}.`
  ).join("\n");

  const scenarioLean = {
    bear: "bearish — things go wrong, sentiment deteriorates",
    base: "moderate — mixed signals, gradual progress",
    bull: "bullish — catalysts hit, momentum builds",
  }[scenarioMode];

  return `You are a financial market simulation engine. You MUST respond with ONLY a raw JSON object. No markdown fences, no backticks, no explanation before or after the JSON. Just the raw JSON starting with { and ending with }.

SCENARIO: ${scenarioMode.toUpperCase()} CASE | QUARTER: Q${roundNum} of ${totalRounds}

MARKET STATE:
BMNR: $${marketState.stockPrice.toFixed(2)} | ETH: $${marketState.ethPrice.toFixed(0)} | mNAV: ${marketState.mNAV.toFixed(2)}x | NAV/Shr: $${marketState.navPerShare.toFixed(2)} | ETH/Shr: ${marketState.ethPerShare.toFixed(6)} | Holdings: ${fN(marketState.ethHoldings)} ETH (${(marketState.ethHoldings / 120e6 * 100).toFixed(1)}% supply) | Breakeven: ${marketState.breakevenMNav.toFixed(2)}x | Flywheel: ${marketState.mNAV > marketState.breakevenMNav ? "ACCRETIVE" : "DILUTIVE"}

${stimDesc ? `EVENTS: ${stimDesc}` : "NO EVENTS"}
${prevSummary ? `PREV QUARTER: ${prevSummary}` : "First quarter."}

AGENTS:
${agentList}

For the ${scenarioMode.toUpperCase()} case, determine each agent's reaction. Lean ${scenarioLean}. Think about herding, contrarianism, reflexivity.

Respond with ONLY this JSON structure (no other text):
{"agents":[{"id":"agent_id","sentiment":-1.0 to 1.0,"action":"BUY or SELL or HOLD","reasoning":"1 sentence","priceTarget":30}],"ethPriceChange":0.05,"mNavChange":0.02,"quarterSummary":"2 sentences"}`;
}

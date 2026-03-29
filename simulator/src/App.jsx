import React, { useState, useMemo, useCallback, useEffect, useRef } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Area, AreaChart, ComposedChart, Bar, Cell } from "recharts";

/* ═══ DESIGN TOKENS — Wedge Day Mode ═══ */
const T = {
  bg: "#f7f8fa", bg2: "#eef0f3", white: "#ffffff",
  green: "#007a3d", greenDim: "rgba(0,122,61,0.08)", greenBorder: "rgba(0,122,61,0.18)",
  blue: "#005f99", blueDim: "rgba(0,95,153,0.08)", blueBorder: "rgba(0,95,153,0.18)",
  text: "#0a0d11", textDim: "#5a6478", textLight: "#8a94a6",
  border: "rgba(0,0,0,0.08)", borderMed: "rgba(0,0,0,0.12)",
  red: "#c84b31", redDim: "rgba(200,75,49,0.06)", redBorder: "rgba(200,75,49,0.18)",
  gold: "#b8941e", goldDim: "rgba(184,148,30,0.08)", goldBorder: "rgba(184,148,30,0.18)",
  purple: "#6b4fa0", purpleDim: "rgba(107,79,160,0.08)", purpleBorder: "rgba(107,79,160,0.18)",
  mono: "'IBM Plex Mono', monospace", sans: "'Barlow', sans-serif", cond: "'Barlow Condensed', sans-serif",
};

/* ═══ FORMATTERS ═══ */
function fmt(n, d = 2) { if (!isFinite(n)) return "—"; if (Math.abs(n) >= 1e12) return `$${(n/1e12).toFixed(d)}T`; if (Math.abs(n) >= 1e9) return `$${(n/1e9).toFixed(d)}B`; if (Math.abs(n) >= 1e6) return `$${(n/1e6).toFixed(d)}M`; if (Math.abs(n) >= 1e3) return `$${(n/1e3).toFixed(d)}K`; return `$${n.toFixed(d)}`; }
function fN(n) { if (!isFinite(n)) return "—"; if (Math.abs(n) >= 1e6) return (n/1e6).toFixed(2)+"M"; if (Math.abs(n) >= 1e3) return (n/1e3).toFixed(1)+"K"; return n.toFixed(0); }
function pct(n) { if (!isFinite(n)) return "—"; return `${n>=0?"+":""}${(n*100).toFixed(2)}%`; }
function safe(a, b) { return b === 0 ? 0 : a / b; }

/* ═══ LIVE DATA — Fallback + API Fetch ═══ */
const FALLBACK = {
  price: 23.37, ethPrice: 2314.60, ethBalance: 4595563, shares: 530621703, nav: 22.57, mNAV: 1.04,
  staked: 3040483, avgCost: 3753.88, cash: 1.2e9, beast: 0.2e9, btcVal: 196*85000,
  analystLo: 30, analystHi: 39, w52Lo: 3.20, w52Hi: 161, fetchedAt: null, isLive: false,
};
async function fetchLiveBMNR() {
  try {
    const res = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: "claude-sonnet-4-20250514", max_tokens: 1000,
        tools: [{ type: "web_search_20250305", name: "web_search" }],
        messages: [{ role: "user", content: `Search for current BMNR stock data from bitminetracker.io. Return ONLY a JSON object: {"price":<number>,"ethPrice":<number>,"ethBalance":<integer>,"shares":<integer>,"nav":<number>,"mNAV":<number>,"staked":<integer>,"avgCost":<number>,"cash":<number>,"beast":<number>,"btcVal":<number>,"analystLo":<number>,"analystHi":<number>,"w52Lo":<number>,"w52Hi":<number>}` }],
      }),
    });
    if (!res.ok) return null;
    const data = await res.json();
    const txt = (data.content||[]).filter(b=>b.type==="text").map(b=>b.text).join("\n");
    const m = txt.match(/\{[^{}]*"price"\s*:\s*[\d.]+[^{}]*\}/);
    if (!m) return null;
    let p; try { p = JSON.parse(m[0]); } catch { return null; }
    if (typeof p.price !== "number" || p.price <= 0) return null;
    return { ...FALLBACK, ...p, fetchedAt: new Date().toLocaleTimeString(), isLive: true };
  } catch { return null; }
}

/* ═══════════════════════════════════════════════════
   AGENT PERSONAS — MiroFish-style detailed personas
   Each agent has a natural-language persona that drives
   LLM reasoning (not just a numeric bias)
═══════════════════════════════════════════════════ */
const AGENTS = [
  { id: "ark", name: "ARK / Cathie Wood", type: "Institutional", icon: "🏛️", persona: "You are Cathie Wood's ARK Invest. You are a conviction buyer of disruptive technology. You see BitMine as a leveraged play on Ethereum's transformative potential. You hold millions of BMNR shares and buy dips aggressively. You believe ETH will reach $10K+ and BMNR is massively undervalued.", bias: 0.5, influence: 0.85, susceptibility: 0.15, memory: 0.7 },
  { id: "fidelity", name: "Fidelity Digital", type: "Institutional", icon: "🏦", persona: "You are a Fidelity institutional allocator. You evaluate BMNR on fundamentals: NAV discount/premium, cash flow from staking, dilution risk. You are cautiously optimistic but need to see MAVAN revenue materialize before increasing position.", bias: 0.2, influence: 0.8, susceptibility: 0.1, memory: 0.8 },
  { id: "mozayyx", name: "MOZAYYX Fund", type: "Institutional", icon: "💎", persona: "You are MOZAYYX, a crypto-focused fund with deep conviction in BitMine's Alchemy of 5% strategy. You see the ETH accumulation as a generational opportunity. You rarely sell and add on weakness.", bias: 0.4, influence: 0.7, susceptibility: 0.2, memory: 0.6 },
  { id: "short_seller", name: "Short Seller Report", type: "Institutional", icon: "🐻", persona: "You are an activist short seller. You believe BitMine is a promotion: negative earnings, massive dilution, stock price entirely dependent on ETH price. The 100x share authorization is a red flag. mNAV premium is unjustified. You publish bearish reports.", bias: -0.6, influence: 0.65, susceptibility: 0.2, memory: 0.5 },
  { id: "pension", name: "Pension Allocator", type: "Institutional", icon: "📊", persona: "You are a conservative pension fund. You are skeptical of crypto treasury companies. You need to see stable cash flows, not speculative ETH price appreciation. Dilution concerns dominate your analysis.", bias: -0.1, influence: 0.6, susceptibility: 0.25, memory: 0.9 },
  { id: "tom_lee", name: "Tom Lee (CEO)", type: "Insider", icon: "👔", persona: "You are Tom Lee, CEO of BitMine. You are the architect of the Alchemy of 5% strategy. You believe ETH is severely undervalued and BMNR will be a $100+ stock. You use ATM offerings strategically to accumulate ETH. You dismiss short-seller criticism as lacking vision.", bias: 0.7, influence: 0.9, susceptibility: 0.05, memory: 0.3 },
  { id: "analyst", name: "B. Riley Analyst", type: "Analyst", icon: "📝", persona: "You are a sell-side equity analyst covering BMNR with a price target of $30-39. You focus on mNAV, ETH/share accretion, MAVAN staking revenue potential, and dilution math. You are moderately bullish but flag execution risk.", bias: 0.3, influence: 0.7, susceptibility: 0.15, memory: 0.7 },
  { id: "ct_analyst", name: "Crypto Twitter Analyst", type: "Analyst", icon: "🧵", persona: "You are a crypto-native analyst on X/Twitter. You view BMNR as the best ETH proxy in equities. You track on-chain ETH flows, staking yields, and mNAV daily. You're bullish but aware of the dilution treadmill.", bias: 0.2, influence: 0.55, susceptibility: 0.4, memory: 0.4 },
  { id: "bear_writer", name: "Seeking Alpha Bear", type: "Analyst", icon: "✍️", persona: "You write bearish analysis on Seeking Alpha. You believe BMNR's premium to NAV is irrational, the share dilution is destroying value, and the company has no real revenue. You compare it unfavorably to simply buying ETH directly.", bias: -0.5, influence: 0.45, susceptibility: 0.3, memory: 0.6 },
  { id: "cnbc", name: "CNBC / Cramer", type: "Media", icon: "📺", persona: "You are a financial media personality. You react to price action and headlines. You swing between excitement when BMNR rallies and caution when it drops. You amplify whatever the current narrative is.", bias: 0.0, influence: 0.6, susceptibility: 0.5, memory: 0.2 },
  { id: "reddit_bull", name: "r/BMNR Bull", type: "Retail", icon: "🦍", persona: "You are a passionate BMNR retail investor on Reddit. You believe in the thesis long-term and buy every dip. You dismiss bears as shorts who 'don't get it'. You post rocket emojis and hold through drawdowns.", bias: 0.4, influence: 0.3, susceptibility: 0.6, memory: 0.3 },
  { id: "reddit_skeptic", name: "r/BMNR Skeptic", type: "Retail", icon: "🤔", persona: "You are a skeptical retail investor. You hold some BMNR but worry about dilution and the gap between stock price and NAV. You ask tough questions and demand clarity on the ATM program.", bias: -0.2, influence: 0.25, susceptibility: 0.5, memory: 0.5 },
  { id: "wsb", name: "WSB Degen", type: "Retail", icon: "🎰", persona: "You are a WallStreetBets trader. You trade BMNR options for volatility. You buy calls before catalysts and puts after euphoria. You have no long-term thesis, only momentum. You follow whatever is trending.", bias: 0.1, influence: 0.35, susceptibility: 0.8, memory: 0.1 },
  { id: "eth_maxi", name: "ETH Maximalist", type: "Retail", icon: "⟠", persona: "You are an Ethereum maximalist. You think owning BMNR is an inefficient way to get ETH exposure with added dilution risk. However, you acknowledge the leveraged upside if ETH moons. You prefer holding ETH directly.", bias: 0.0, influence: 0.4, susceptibility: 0.3, memory: 0.4 },
  { id: "value", name: "Value Investor", type: "Retail", icon: "📐", persona: "You are a Graham-style value investor. You only buy BMNR below NAV (mNAV < 1.0). You think the current premium is speculative. You would be a buyer at $15-18 (discount to NAV) but not at current levels.", bias: -0.3, influence: 0.35, susceptibility: 0.2, memory: 0.8 },
  { id: "swing", name: "Swing Trader", type: "Retail", icon: "📉", persona: "You are a pure technical trader. You only care about chart patterns, volume, and support/resistance levels. Fundamentals are irrelevant to you. You trade the falling wedge pattern and key levels around $20-22.", bias: 0.0, influence: 0.2, susceptibility: 0.7, memory: 0.15 },
  { id: "mm", name: "Market Maker", type: "Quant", icon: "🤖", persona: "You are an automated market maker. You provide liquidity and profit from the bid-ask spread. You are always delta neutral. You observe order flow imbalances to gauge short-term direction.", bias: 0.0, influence: 0.5, susceptibility: 0.0, memory: 0.0 },
  { id: "momentum", name: "Momentum Algo", type: "Quant", icon: "⚡", persona: "You are a trend-following algorithm. You buy when price is above its moving averages with increasing volume. You sell when momentum fades. You have no opinion on fundamentals, only price action.", bias: 0.0, influence: 0.4, susceptibility: 0.0, memory: 0.95 },
  { id: "arb", name: "mNAV Arb Bot", type: "Quant", icon: "🔄", persona: "You are an arbitrage algorithm that trades the mNAV premium/discount. When mNAV > 1.3, you short BMNR and buy ETH. When mNAV < 0.8, you buy BMNR and short ETH. You push mNAV toward fair value.", bias: 0.0, influence: 0.45, susceptibility: 0.0, memory: 0.0 },
  { id: "macro_bull", name: "Macro Bull", type: "Macro", icon: "🌊", persona: "You are a macro strategist who believes we're entering a liquidity-driven bull market. Fed rate cuts, weakening dollar, and crypto adoption create tailwinds for BMNR. Risk-on environments favor leveraged crypto plays.", bias: 0.2, influence: 0.5, susceptibility: 0.3, memory: 0.6 },
  { id: "macro_bear", name: "Macro Bear", type: "Macro", icon: "🏔️", persona: "You are a macro strategist warning about recession risk, sticky inflation, and higher-for-longer rates. Risk assets including crypto are vulnerable. BMNR's leverage to ETH magnifies downside in a risk-off environment.", bias: -0.3, influence: 0.5, susceptibility: 0.3, memory: 0.6 },
];

/* ═══ STIMULI CATALOG ═══ */
const STIMULI = [
  { id: "eth_5k", name: "ETH Breaks $5,000", cat: "ETH", icon: "🚀", impact: 0.7, desc: "Institutional adoption wave" },
  { id: "eth_crash", name: "ETH Crashes < $800", cat: "ETH", icon: "💀", impact: -0.8, desc: "Crypto winter 3.0" },
  { id: "eth_etf_in", name: "ETH ETF Mega-Inflows", cat: "ETH", icon: "📈", impact: 0.5, desc: "$10B+ spot ETF flows" },
  { id: "eth_etf_out", name: "ETH ETF Redemptions", cat: "ETH", icon: "📤", impact: -0.45, desc: "Institutions dump positions" },
  { id: "eth_upgrade", name: "Pectra Upgrade", cat: "ETH", icon: "⬆️", impact: 0.3, desc: "Protocol upgrade succeeds" },
  { id: "mavan", name: "MAVAN Staking Live", cat: "BitMine", icon: "⚡", impact: 0.6, desc: "$330M+ annual staking rev" },
  { id: "mavan_delay", name: "MAVAN Delayed", cat: "BitMine", icon: "⏳", impact: -0.35, desc: "Technical issues" },
  { id: "alchemy5", name: "Alchemy 5% Hit", cat: "BitMine", icon: "🧪", impact: 0.65, desc: "5% of all ETH supply" },
  { id: "beast_ipo", name: "Beast Industries IPO", cat: "BitMine", icon: "🎬", impact: 0.4, desc: "$200M stake monetized" },
  { id: "scandal", name: "Executive Scandal", cat: "BitMine", icon: "⚠️", impact: -0.6, desc: "Accounting concerns" },
  { id: "sp500", name: "Index Inclusion", cat: "BitMine", icon: "🏛️", impact: 0.45, desc: "S&P 500 / Russell add" },
  { id: "dilution", name: "100x Auth Used", cat: "Corporate", icon: "💧", impact: -0.55, desc: "Massive dilution" },
  { id: "buyback", name: "Buyback $500M", cat: "Corporate", icon: "🔄", impact: 0.35, desc: "Aggressive buyback" },
  { id: "convert", name: "Convertible $2B", cat: "Corporate", icon: "📜", impact: -0.2, desc: "Debt for ETH buys" },
  { id: "fed_cut", name: "Fed Cuts 150bps", cat: "Macro", icon: "📉", impact: 0.4, desc: "Aggressive easing" },
  { id: "recession", name: "US Recession", cat: "Macro", icon: "🏚️", impact: -0.5, desc: "Risk-off everywhere" },
  { id: "pro_crypto", name: "Pro-Crypto Law", cat: "Macro", icon: "⚖️", impact: 0.4, desc: "Regulatory clarity" },
  { id: "sec", name: "SEC Crackdown", cat: "Macro", icon: "🚫", impact: -0.6, desc: "Investment co. risk" },
  { id: "btc_150k", name: "BTC $150K", cat: "Macro", icon: "₿", impact: 0.45, desc: "BTC supercycle" },
  { id: "squeeze", name: "Short Squeeze", cat: "Technical", icon: "🔥", impact: 0.6, desc: "30%+ SI unwind" },
  { id: "ark_exit", name: "ARK Sells All", cat: "Technical", icon: "🚪", impact: -0.5, desc: "Cathie exits" },
  { id: "rival", name: "Rival Treasury", cat: "Technical", icon: "🏁", impact: -0.25, desc: "Major competitor" },
  { id: "viral", name: "Viral Social Pump", cat: "Social", icon: "📱", impact: 0.3, desc: "BMNR trends on X" },
  { id: "fud", name: "Coordinated FUD", cat: "Social", icon: "🗞️", impact: -0.35, desc: "Short-seller report" },
  { id: "openai", name: "OpenAI/Eightco Win", cat: "Social", icon: "🤖", impact: 0.35, desc: "$80M bet pays off" },
];

const SIM_ROUNDS = 8; // 8 quarterly rounds = 2 years
const SCENARIO_META = {
  bear: { label: "BEAR", color: T.red, desc: "ETH collapses, dilution spiral, premium vanishes" },
  base: { label: "BASE", color: T.blue, desc: "ETH $2-3K, MAVAN launches, moderate growth" },
  bull: { label: "BULL", color: T.green, desc: "ETH breaks ATH, Alchemy 5% hit, staking revenue" },
};

/* ═══════════════════════════════════════════════════
   LLM-DRIVEN SIMULATION ENGINE (MiroFish-style)
   
   Each round: all 21 agents reason via a single Anthropic
   API call. The LLM evaluates each agent's persona against
   the current market state, stimuli, and prior round context.
   Returns per-agent sentiment, reasoning, and action.
   
   This is the core MiroFish insight: predictions emerge
   from collective LLM reasoning, not programmed formulas.
═══════════════════════════════════════════════════ */
async function runLLMRound(roundNum, marketState, activeStimuli, prevRoundSummary, scenarioMode) {
  const stimDesc = activeStimuli.map(s => {
    const st = STIMULI.find(x => x.id === s.id);
    return st ? `${st.name} (${(s.intensity||1).toFixed(1)}x) — ${st.desc}` : "";
  }).filter(Boolean).join("; ");

  // Pick 8 most important agents per round (rotate + always include key archetypes)
  const coreIds = ["tom_lee", "ark", "short_seller", "analyst", "reddit_bull", "arb", "macro_bull", "macro_bear"];
  const rotatingIds = AGENTS.filter(a => !coreIds.includes(a.id)).map(a => a.id);
  const rotateStart = ((roundNum - 1) * 3) % rotatingIds.length;
  const extraIds = [rotatingIds[rotateStart % rotatingIds.length], rotatingIds[(rotateStart + 1) % rotatingIds.length], rotatingIds[(rotateStart + 2) % rotatingIds.length]];
  const roundAgentIds = [...new Set([...coreIds, ...extraIds])];
  const roundAgents = AGENTS.filter(a => roundAgentIds.includes(a.id));

  const agentList = roundAgents.map(a =>
    `- ${a.name} [id:${a.id}] (${a.type}): ${a.persona.split(".").slice(0, 2).join(".")}.`
  ).join("\n");

  const userMsg = `SCENARIO: ${scenarioMode.toUpperCase()} CASE | QUARTER: Q${roundNum} of ${SIM_ROUNDS}

MARKET STATE:
BMNR: $${marketState.stockPrice.toFixed(2)} | ETH: $${marketState.ethPrice.toFixed(0)} | mNAV: ${marketState.mNAV.toFixed(2)}x | NAV/Shr: $${marketState.navPerShare.toFixed(2)} | ETH/Shr: ${marketState.ethPerShare.toFixed(6)} | Holdings: ${fN(marketState.ethHoldings)} ETH (${(marketState.ethHoldings / 120e6 * 100).toFixed(1)}% supply) | Breakeven: ${marketState.breakevenMNav.toFixed(2)}x | Flywheel: ${marketState.mNAV > marketState.breakevenMNav ? "ACCRETIVE" : "DILUTIVE"}

${stimDesc ? `EVENTS: ${stimDesc}` : "NO EVENTS"}
${prevRoundSummary ? `PREV QUARTER: ${prevRoundSummary}` : "First quarter."}

AGENTS:
${agentList}

For the ${scenarioMode.toUpperCase()} case, determine each agent's reaction. Lean ${scenarioMode === "bear" ? "bearish — things go wrong" : scenarioMode === "bull" ? "bullish — catalysts hit" : "moderate — mixed signals"}. Think about herding, contrarianism, reflexivity.`;

  try {
    const res = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: "claude-sonnet-4-20250514",
        max_tokens: 4096,
        messages: [{
          role: "user",
          content: `You are a financial market simulation engine. You MUST respond with ONLY a raw JSON object. No markdown fences, no backticks, no explanation before or after the JSON. Just the raw JSON starting with { and ending with }.

${userMsg}

Respond with ONLY this JSON structure (no other text):
{"agents":[{"id":"agent_id","sentiment":-1.0 to 1.0,"action":"BUY or SELL or HOLD","reasoning":"1 sentence","priceTarget":30}],"ethPriceChange":0.05,"mNavChange":0.02,"quarterSummary":"2 sentences"}`
        }],
      }),
    });

    if (!res.ok) {
      const errText = await res.text().catch(() => "");
      console.error(`LLM round ${roundNum} HTTP ${res.status}:`, errText.slice(0, 200));
      return null;
    }

    const data = await res.json();
    const txt = (data.content || []).filter(b => b.type === "text").map(b => b.text).join("\n");

    if (!txt || txt.length < 10) {
      console.error(`LLM round ${roundNum}: empty response`);
      return null;
    }

    // Strip markdown fences if present
    let cleaned = txt.replace(/```json\s*/gi, "").replace(/```\s*/g, "").trim();

    // Try direct parse first (ideal case: model returned pure JSON)
    let parsed = null;
    try { parsed = JSON.parse(cleaned); } catch {}

    // Fallback: extract the outermost JSON object containing "agents"
    if (!parsed) {
      // Find the opening { before "agents" and match to its closing }
      const agentsIdx = cleaned.indexOf('"agents"');
      if (agentsIdx === -1) { console.error(`LLM round ${roundNum}: no "agents" in response`); return null; }

      // Walk backward to find the opening brace
      let start = cleaned.lastIndexOf("{", agentsIdx);
      if (start === -1) { console.error(`LLM round ${roundNum}: no opening brace`); return null; }

      // Walk forward from start, counting braces to find the matching close
      let depth = 0;
      let end = -1;
      for (let i = start; i < cleaned.length; i++) {
        if (cleaned[i] === "{") depth++;
        else if (cleaned[i] === "}") { depth--; if (depth === 0) { end = i; break; } }
      }
      if (end === -1) { console.error(`LLM round ${roundNum}: unbalanced braces`); return null; }

      try { parsed = JSON.parse(cleaned.slice(start, end + 1)); } catch (e) {
        console.error(`LLM round ${roundNum}: JSON parse failed:`, e.message, cleaned.slice(start, start + 100));
        return null;
      }
    }

    if (!parsed || !Array.isArray(parsed.agents) || parsed.agents.length === 0) {
      console.error(`LLM round ${roundNum}: invalid structure`, JSON.stringify(parsed).slice(0, 100));
      return null;
    }

    // Fill in agents that weren't in this round's LLM call
    const fullAgents = AGENTS.map(a => {
      const llmA = parsed.agents.find(la => la.id === a.id);
      if (llmA) return llmA;
      // Agents not in this round: carry forward a neutral estimate based on bias
      return { id: a.id, sentiment: a.bias * 0.5, action: "HOLD", reasoning: "Not polled this quarter.", priceTarget: null };
    });
    parsed.agents = fullAgents;

    console.log(`LLM round ${roundNum} OK: ${parsed.agents.length} agents, ethΔ=${parsed.ethPriceChange}, summary=${(parsed.quarterSummary||"").slice(0, 50)}`);
    return parsed;
  } catch (e) {
    console.error(`LLM round ${roundNum} exception:`, e);
    return null;
  }
}

/* ═══ FORMULA ENGINE (fast fallback) ═══ */
function runFormulaSimulation(activeStimuli, scenarioMode, live) {
  const scenarioMul = { bear: -0.4, base: 0.0, bull: 0.4 }[scenarioMode];
  const stimPressure = {};
  AGENTS.forEach(a => {
    let p = 0;
    activeStimuli.forEach(s => {
      const st = STIMULI.find(x => x.id === s.id);
      if (st) p += st.impact * (s.intensity || 1) * 0.5;
    });
    stimPressure[a.id] = p;
  });

  const agentStates = {};
  AGENTS.forEach(a => { agentStates[a.id] = { sentiment: a.bias + scenarioMul * 0.3, history: [], reasoning: "" }; });

  let ethPrice = live.ethPrice, ethHoldings = live.ethBalance, shares = live.shares;
  let cash = live.cash, mNAV = live.mNAV;
  const btcVal = live.btcVal, beastVal = live.beast;
  const rounds = [];
  let prevSent = 0;

  for (let r = 0; r <= SIM_ROUNDS; r++) {
    if (r > 0) {
      AGENTS.forEach(a => {
        const st = agentStates[a.id];
        let ns = a.bias * 0.3 + scenarioMul * 0.15;
        ns += (stimPressure[a.id] || 0) * Math.max(0.3, 1 - r * 0.05);
        if (a.susceptibility > 0) {
          let ni = 0, nw = 0;
          AGENTS.forEach(o => { if (o.id !== a.id) { const w = o.influence * a.susceptibility; ni += agentStates[o.id].sentiment * w; nw += w; } });
          if (nw > 0) ns += (ni / nw) * a.susceptibility * 0.4;
        }
        if (a.memory > 0 && st.history.length > 0) ns += st.history.slice(-3).reduce((s, v) => s + v, 0) / Math.min(3, st.history.length) * a.memory * 0.2;
        if (a.id === "arb") ns = -(mNAV - 1.0) * 0.5;
        if (a.id === "momentum") ns = prevSent * 0.8;
        ns += (Math.random() - 0.5) * 0.15;
        st.sentiment = Math.max(-1, Math.min(1, ns));
        st.history.push(st.sentiment);
        st.reasoning = st.sentiment > 0.2 ? "Bullish on current setup" : st.sentiment < -0.2 ? "Concerned about downside risks" : "Watching from the sidelines";
      });
    }

    let aggS = 0, aggW = 0;
    AGENTS.forEach(a => { aggS += agentStates[a.id].sentiment * a.influence; aggW += a.influence; });
    aggS = aggW > 0 ? aggS / aggW : 0;
    prevSent = aggS;

    if (r > 0) {
      ethPrice *= (1 + aggS * 0.08 + (Math.random() - 0.5) * 0.06);
      ethPrice = Math.max(200, ethPrice);
      mNAV *= (1 + aggS * 0.06 + (Math.random() - 0.5) * 0.04);
      mNAV = Math.max(0.3, Math.min(4.0, mNAV));
    }

    const ethVal = ethHoldings * ethPrice;
    const nav = ethVal + btcVal + beastVal + cash;
    const navPS = safe(nav, shares);
    const stockP = mNAV * navPS;
    const ethPS = safe(ethHoldings, shares);
    const bev = safe(ethVal, nav);

    let issued = 0, bought = 0, raised = 0;
    if (r > 0 && mNAV > bev && mNAV > 0.8) {
      issued = Math.round(shares * 0.02 * Math.min(1, (mNAV - bev) / 0.3));
      raised = issued * stockP;
      bought = raised / ethPrice;
      ethHoldings += bought; shares += issued;
    }

    const snap = AGENTS.map(a => ({ ...a, sentiment: agentStates[a.id].sentiment, reasoning: agentStates[a.id].reasoning }));
    const bullish = snap.filter(a => a.sentiment > 0.1).length;
    const bearish = snap.filter(a => a.sentiment < -0.1).length;

    rounds.push({ round: r, ethPrice, mNAV, navPerShare: navPS, stockPrice: stockP, ethPerShare: ethPS,
      ethHoldings, shares, cash: Math.max(0, cash), sharesIssued: issued, ethBought: bought,
      capitalRaised: raised, isAccretive: mNAV > bev, breakevenMNav: bev,
      aggSentiment: aggS, bullish, bearish, agentSnapshot: snap, quarterSummary: "", llmPowered: false });
  }
  return rounds;
}

/* ═══════════════════════════════════════════════════
   FULL LLM SIMULATION (async, progressive)
═══════════════════════════════════════════════════ */
async function runFullLLMSimulation(activeStimuli, scenarioMode, live, onRoundComplete) {
  let ethPrice = live.ethPrice, ethHoldings = live.ethBalance, shares = live.shares;
  let cash = live.cash, mNAV = live.mNAV;
  const btcVal = live.btcVal, beastVal = live.beast;
  const rounds = [];
  let prevSummary = "";

  // Round 0: initial state
  const ethVal0 = ethHoldings * ethPrice;
  const nav0 = ethVal0 + btcVal + beastVal + cash;
  const snap0 = AGENTS.map(a => ({ ...a, sentiment: a.bias, reasoning: "Awaiting first quarter data." }));
  rounds.push({ round: 0, ethPrice, mNAV, navPerShare: safe(nav0, shares), stockPrice: mNAV * safe(nav0, shares),
    ethPerShare: safe(ethHoldings, shares), ethHoldings, shares, cash, sharesIssued: 0, ethBought: 0,
    capitalRaised: 0, isAccretive: true, breakevenMNav: safe(ethVal0, nav0),
    aggSentiment: 0, bullish: AGENTS.filter(a => a.bias > 0.1).length, bearish: AGENTS.filter(a => a.bias < -0.1).length,
    agentSnapshot: snap0, quarterSummary: "Initial state. Simulation begins.", llmPowered: true });
  onRoundComplete([...rounds]);

  for (let r = 1; r <= SIM_ROUNDS; r++) {
    const marketState = {
      stockPrice: rounds[r-1].stockPrice, ethPrice, mNAV,
      navPerShare: rounds[r-1].navPerShare, ethPerShare: rounds[r-1].ethPerShare,
      ethHoldings, breakevenMNav: rounds[r-1].breakevenMNav,
    };

    const llmResult = await runLLMRound(r, marketState, activeStimuli, prevSummary, scenarioMode);

    if (llmResult && llmResult.agents) {
      // Apply LLM-derived market changes
      const ethChg = typeof llmResult.ethPriceChange === "number" ? llmResult.ethPriceChange : 0;
      const mNavChg = typeof llmResult.mNavChange === "number" ? llmResult.mNavChange : 0;
      ethPrice *= (1 + Math.max(-0.5, Math.min(0.5, ethChg)));
      ethPrice = Math.max(200, ethPrice);
      mNAV *= (1 + Math.max(-0.4, Math.min(0.4, mNavChg)));
      mNAV = Math.max(0.3, Math.min(4.0, mNAV));
      prevSummary = llmResult.quarterSummary || "";

      // Build agent snapshot from LLM output
      const snap = AGENTS.map(a => {
        const llmAgent = llmResult.agents.find(la => la.id === a.id);
        return {
          ...a,
          sentiment: llmAgent ? Math.max(-1, Math.min(1, llmAgent.sentiment || 0)) : a.bias,
          reasoning: llmAgent?.reasoning || "No comment this quarter.",
          action: llmAgent?.action || "HOLD",
          priceTarget: llmAgent?.priceTarget || null,
        };
      });

      // Aggregate sentiment
      let aggS = 0, aggW = 0;
      snap.forEach(a => { aggS += a.sentiment * (AGENTS.find(x=>x.id===a.id)?.influence || 0.5); aggW += (AGENTS.find(x=>x.id===a.id)?.influence || 0.5); });
      aggS = aggW > 0 ? aggS / aggW : 0;

      // Flywheel
      const ethVal = ethHoldings * ethPrice;
      const nav = ethVal + btcVal + beastVal + cash;
      const navPS = safe(nav, shares);
      const stockP = mNAV * navPS;
      const ethPS = safe(ethHoldings, shares);
      const bev = safe(ethVal, nav);

      let issued = 0, bought = 0, raised = 0;
      if (mNAV > bev && mNAV > 0.8) {
        issued = Math.round(shares * 0.02 * Math.min(1, (mNAV - bev) / 0.3));
        raised = issued * stockP; bought = raised / ethPrice;
        ethHoldings += bought; shares += issued;
      }

      rounds.push({ round: r, ethPrice, mNAV, navPerShare: navPS, stockPrice: stockP, ethPerShare: ethPS,
        ethHoldings, shares, cash: Math.max(0, cash), sharesIssued: issued, ethBought: bought,
        capitalRaised: raised, isAccretive: mNAV > bev, breakevenMNav: bev,
        aggSentiment: aggS, bullish: snap.filter(a => a.sentiment > 0.1).length,
        bearish: snap.filter(a => a.sentiment < -0.1).length,
        agentSnapshot: snap, quarterSummary: prevSummary, llmPowered: true });
    } else {
      // LLM failed — use formula fallback for this round
      const fallbackRound = runFormulaSimulation(activeStimuli, scenarioMode, { ...live, ethPrice, ethBalance: ethHoldings, shares, cash, mNAV, btcVal, beast: beastVal });
      const fr = fallbackRound[Math.min(r, fallbackRound.length - 1)];
      if (fr) {
        ethPrice = fr.ethPrice; mNAV = fr.mNAV; ethHoldings = fr.ethHoldings; shares = fr.shares;
        rounds.push({ ...fr, round: r, llmPowered: false, quarterSummary: "⚠ LLM unavailable — formula fallback used." });
      }
    }
    onRoundComplete([...rounds]);
  }
  return rounds;
}

/* ═══ UI COMPONENTS ═══ */
function CornerBrackets({ color = T.green, size = 12, inset = 7 }) {
  const s = { position: "absolute", width: size, height: size };
  return (<><div style={{ ...s, top: inset, left: inset, borderTop: "1px solid " + color, borderLeft: "1px solid " + color }} /><div style={{ ...s, top: inset, right: inset, borderTop: "1px solid " + color, borderRight: "1px solid " + color }} /><div style={{ ...s, bottom: inset, left: inset, borderBottom: "1px solid " + color, borderLeft: "1px solid " + color }} /><div style={{ ...s, bottom: inset, right: inset, borderBottom: "1px solid " + color, borderRight: "1px solid " + color }} /></>);
}
function Metric({ label, value, sub, color = T.green, compact }) {
  return (<div style={{ background: T.white, border: "1px solid " + T.border, padding: compact ? "8px 10px" : "11px 13px", position: "relative", flex: 1, minWidth: compact ? 95 : 115 }}>
    <div style={{ position: "absolute", top: 0, left: 0, width: "100%", height: 2, background: color, opacity: 0.5 }} />
    <div style={{ fontSize: 7.5, fontWeight: 600, color: T.textDim, textTransform: "uppercase", letterSpacing: "1.5px", marginBottom: compact ? 2 : 3, fontFamily: T.mono }}>{label}</div>
    <div style={{ fontSize: compact ? 14 : 17, fontWeight: 900, color, letterSpacing: "-0.02em", fontFamily: T.cond }}>{value}</div>
    {sub && <div style={{ fontSize: 8, color: T.textLight, marginTop: 1, fontFamily: T.mono }}>{sub}</div>}
  </div>);
}
function TabBtn({ active, label, onClick }) {
  return (<button onClick={onClick} style={{ padding: "7px 14px", fontFamily: T.mono, fontSize: 8, letterSpacing: "2px", textTransform: "uppercase", cursor: "crosshair", transition: "all 0.15s", background: active ? T.green : "transparent", color: active ? "#fff" : T.textDim, border: "1px solid " + (active ? T.green : T.border), clipPath: "polygon(4px 0%, 100% 0%, calc(100% - 4px) 100%, 0% 100%)" }}>{label}</button>);
}
function ChartTip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (<div style={{ background: T.white, border: "1px solid " + T.border, padding: "8px 11px", fontFamily: T.mono, fontSize: 9, boxShadow: "0 3px 10px rgba(0,0,0,0.06)" }}>
    <div style={{ fontWeight: 700, color: T.text, marginBottom: 3, letterSpacing: "1px" }}>Q{label}</div>
    {payload.filter(p => p.value != null).map((p, i) => (<div key={i} style={{ display: "flex", justifyContent: "space-between", gap: 12, marginBottom: 1 }}><span style={{ color: T.textDim, display: "flex", alignItems: "center", gap: 3 }}><span style={{ width: 5, height: 5, background: p.color, display: "inline-block" }} />{p.name}</span><span style={{ fontWeight: 600, color: p.color }}>{typeof p.value === "number" ? (Math.abs(p.value) < 1 ? p.value.toFixed(4) : "$"+p.value.toFixed(0)) : p.value}</span></div>))}
  </div>);
}
function StimulusCard({ st, active, intensity, onToggle, onInt }) {
  const pos = st.impact > 0; const ac = pos ? T.green : T.red;
  return (<div onClick={() => onToggle(st.id)} style={{ background: active ? (pos ? T.greenDim : T.redDim) : T.white, border: "1px solid " + (active ? (pos ? T.greenBorder : T.redBorder) : T.border), padding: "7px 9px", cursor: "crosshair", transition: "all 0.15s", userSelect: "none" }}>
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <span style={{ fontSize: 14 }}>{st.icon}</span>
      <div style={{ flex: 1, minWidth: 0 }}><div style={{ fontSize: 9.5, fontWeight: 600, color: T.text, fontFamily: T.sans }}>{st.name}</div><div style={{ fontSize: 7.5, color: T.textLight, fontFamily: T.mono }}>{st.desc}</div></div>
      <div style={{ width: 14, height: 14, flexShrink: 0, border: "1.5px solid " + (active ? ac : T.textLight), background: active ? ac : "transparent", display: "flex", alignItems: "center", justifyContent: "center" }}>{active && <span style={{ color: "#fff", fontSize: 8, fontWeight: 900 }}>✓</span>}</div>
    </div>
    {active && (<div style={{ marginTop: 5, display: "flex", alignItems: "center", gap: 5 }} onClick={e => e.stopPropagation()}>
      <span style={{ fontSize: 7.5, color: T.textDim, fontFamily: T.mono }}>INT</span>
      <div style={{ flex: 1, position: "relative", height: 3, background: T.bg2 }}><div style={{ position: "absolute", top: 0, left: 0, height: "100%", width: ((intensity - 0.1) / 2.4) * 100 + "%", background: ac }} /><input type="range" min="0.1" max="2.5" step="0.1" value={intensity} onChange={e => onInt(st.id, +e.target.value)} style={{ position: "absolute", top: -8, left: 0, width: "100%", height: 20, opacity: 0, cursor: "crosshair" }} /></div>
      <span style={{ fontSize: 8.5, fontFamily: T.mono, color: T.text, fontWeight: 600, minWidth: 22 }}>{intensity.toFixed(1)}×</span>
    </div>)}
  </div>);
}
function AgentRow({ agent, expanded, onToggle }) {
  const s = agent.sentiment || 0;
  const c = s > 0.1 ? T.green : s < -0.1 ? T.red : T.gold;
  const act = agent.action || "HOLD";
  return (<div style={{ borderBottom: "1px solid " + T.border }}>
    <div onClick={onToggle} style={{ display: "grid", gridTemplateColumns: "17px 1fr 55px 52px", gap: 5, padding: "5px 9px", fontSize: 9, fontFamily: T.mono, alignItems: "center", cursor: "crosshair", background: expanded ? T.bg2 : "transparent" }}>
      <span style={{ fontSize: 12 }}>{agent.icon}</span>
      <div><div style={{ fontWeight: 600, color: T.text, fontFamily: T.sans, fontSize: 9.5 }}>{agent.name}</div><div style={{ fontSize: 7, color: T.textLight, letterSpacing: "1px" }}>{agent.type}</div></div>
      <span style={{ fontWeight: 700, color: c, textAlign: "center" }}>{(s >= 0 ? "+" : "") + (s * 100).toFixed(0)}%</span>
      <span style={{ fontWeight: 700, color: act === "BUY" ? T.green : act === "SELL" ? T.red : T.gold, textAlign: "right", fontSize: 8, letterSpacing: "1px" }}>{act}</span>
    </div>
    {expanded && agent.reasoning && (
      <div style={{ padding: "4px 9px 8px 30px", background: T.bg2 }}>
        <div style={{ fontFamily: T.sans, fontSize: 10, color: T.textDim, fontWeight: 300, lineHeight: 1.5, fontStyle: "italic" }}>"{agent.reasoning}"</div>
        {agent.priceTarget && <div style={{ fontFamily: T.mono, fontSize: 8, color: T.blue, marginTop: 3 }}>PT: ${agent.priceTarget}</div>}
      </div>
    )}
  </div>);
}

/* ═══ MAIN APP ═══ */
export default function MiroFishSimulator() {
  const [stims, setStims] = useState([]);
  const [catFilter, setCatFilter] = useState("All");
  const [scenario, setScenario] = useState("base");
  const [tab, setTab] = useState("simulation");
  const [mode, setMode] = useState("llm"); // "llm" or "formula"
  const [live, setLive] = useState(FALLBACK);
  const [dataStatus, setDataStatus] = useState("loading");
  const [simData, setSimData] = useState(null); // current scenario data (progressive)
  const [formulaResults, setFormulaResults] = useState(null); // all 3 scenario formula results
  const [simStatus, setSimStatus] = useState("idle"); // idle | running | done
  const [simRound, setSimRound] = useState(0);
  const [expandedAgent, setExpandedAgent] = useState(null);
  const abortRef = useRef(false);

  useEffect(() => {
    let c = false;
    (async () => { setDataStatus("loading"); const r = await fetchLiveBMNR(); if (c) return; if (r) { setLive(r); setDataStatus("live"); } else setDataStatus("fallback"); })();
    return () => { c = true; };
  }, []);

  const cats = useMemo(() => ["All", ...new Set(STIMULI.map(s => s.cat))], []);
  const filtered = useMemo(() => catFilter === "All" ? STIMULI : STIMULI.filter(s => s.cat === catFilter), [catFilter]);
  const toggle = useCallback(id => setStims(p => p.find(s => s.id === id) ? p.filter(s => s.id !== id) : [...p, { id, intensity: 1.0 }]), []);
  const setInt = useCallback((id, v) => setStims(p => p.map(s => s.id === id ? { ...s, intensity: v } : s)), []);

  const runSim = useCallback(async () => {
    abortRef.current = false;
    setSimStatus("running"); setSimRound(0); setSimData(null);

    // Always run formula for comparison
    const fResults = {
      bear: runFormulaSimulation(stims, "bear", live),
      base: runFormulaSimulation(stims, "base", live),
      bull: runFormulaSimulation(stims, "bull", live),
    };
    setFormulaResults(fResults);

    if (mode === "llm") {
      await runFullLLMSimulation(stims, scenario, live, (progressiveData) => {
        if (abortRef.current) return;
        setSimData(progressiveData);
        setSimRound(progressiveData.length - 1);
      });
    } else {
      setSimData(fResults[scenario]);
    }
    if (!abortRef.current) setSimStatus("done");
  }, [stims, scenario, live, mode]);

  const data = simData;
  const final = data && data.length > 1 ? data[data.length - 1] : null;
  const initial = data && data.length > 0 ? data[0] : null;
  const sc = SCENARIO_META[scenario];

  const chartData = data ? data.map(d => ({ round: d.round, stockPrice: d.stockPrice, mNAV: d.mNAV, ethPerShare: d.ethPerShare, sentiment: d.aggSentiment, ethPrice: d.ethPrice })) : [];
  const gridBg = "linear-gradient(rgba(0,0,0,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(0,0,0,0.02) 1px, transparent 1px)";

  return (
    <div style={{ minHeight: "100vh", background: T.bg, color: T.text, fontFamily: T.sans, backgroundImage: gridBg, backgroundSize: "60px 60px" }}>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=Barlow:wght@300;400;500;600;700;900&family=Barlow+Condensed:wght@400;600;700;900&display=swap');@keyframes ts{from{transform:translateX(0)}to{transform:translateX(-33.33%)}}@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}`}</style>

      {/* NAV */}
      <nav style={{ height: 48, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 22px", background: "rgba(247,248,250,0.92)", backdropFilter: "blur(16px)", borderBottom: "1px solid " + T.border, position: "sticky", top: 0, zIndex: 100 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
          <svg width="20" height="20" viewBox="0 0 28 28"><polygon points="14,2 26,26 2,26" fill="none" stroke={T.green} strokeWidth="1.5" /><polygon points="14,8 22,24 6,24" fill={T.greenDim} stroke={T.green} strokeWidth="0.5" /></svg>
          <span style={{ fontWeight: 900, fontSize: 13, letterSpacing: "0.18em", textTransform: "uppercase" }}>BMNR</span>
          <span style={{ fontFamily: T.mono, fontSize: 7.5, letterSpacing: "2px", color: T.textLight }}>MIROFISH SIMULATOR</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <div style={{ fontFamily: T.mono, fontSize: 7, letterSpacing: "1.5px", color: mode === "llm" ? T.purple : T.blue, padding: "3px 8px", border: "1px solid " + (mode === "llm" ? T.purpleBorder : T.blueBorder), background: mode === "llm" ? T.purpleDim : T.blueDim }}>
            {mode === "llm" ? "▸ LLM-DRIVEN" : "▸ FORMULA"}
          </div>
          <div style={{ fontFamily: T.mono, fontSize: 7, letterSpacing: "1.5px", padding: "3px 8px", display: "flex", alignItems: "center", gap: 3, color: dataStatus === "live" ? T.green : dataStatus === "loading" ? T.gold : T.red, border: "1px solid " + (dataStatus === "live" ? T.greenBorder : dataStatus === "loading" ? T.goldBorder : T.redBorder), background: dataStatus === "live" ? T.greenDim : dataStatus === "loading" ? T.goldDim : T.redDim }}>
            <span style={{ width: 4, height: 4, borderRadius: "50%", background: "currentColor", display: "inline-block", animation: dataStatus === "loading" ? "pulse 1s infinite" : "none" }} />
            {dataStatus === "live" ? `LIVE ${live.fetchedAt||""}` : dataStatus === "loading" ? "FETCHING" : "CACHED"}
          </div>
        </div>
      </nav>

      {/* TICKER */}
      <div style={{ height: 24, overflow: "hidden", display: "flex", alignItems: "center", borderBottom: "1px solid " + T.border, background: T.greenDim }}>
        <div style={{ display: "flex", whiteSpace: "nowrap", animation: "ts 35s linear infinite" }}>
          {[...Array(3)].map((_, rep) => (<div key={rep} style={{ display: "flex" }}>
            {[`${AGENTS.length} AGENTS`, `${STIMULI.length} STIMULI`, `mNAV ${live.mNAV.toFixed(2)}x`, `${fN(live.ethBalance)} ETH`, `$${live.price} BMNR`, mode === "llm" ? "LLM SWARM REASONING" : "FORMULA ENGINE"].map((t, i) => (
              <span key={i} style={{ fontFamily: T.mono, fontSize: 7, letterSpacing: "3px", textTransform: "uppercase", padding: "0 28px", color: T.green }}>▸ {t}</span>
            ))}
          </div>))}
        </div>
      </div>

      <div style={{ display: "flex", minHeight: "calc(100vh - 72px)" }}>
        {/* LEFT */}
        <div style={{ width: 280, padding: "14px 16px", borderRight: "1px solid " + T.border, overflowY: "auto", maxHeight: "calc(100vh - 72px)", background: T.white, flexShrink: 0 }}>
          {/* Mode toggle */}
          <div style={{ display: "flex", gap: 4, marginBottom: 12 }}>
            {[["llm", "LLM AGENTS", T.purple], ["formula", "FORMULA", T.blue]].map(([m, l, c]) => (
              <button key={m} onClick={() => setMode(m)} style={{ flex: 1, padding: "7px 4px", fontFamily: T.mono, fontSize: 7.5, letterSpacing: "1.5px", cursor: "crosshair", background: mode === m ? c + "12" : T.white, border: "1px solid " + (mode === m ? c : T.border), color: mode === m ? c : T.textDim, fontWeight: mode === m ? 700 : 400 }}>{l}</button>
            ))}
          </div>

          {mode === "llm" && <div style={{ padding: "6px 8px", background: T.purpleDim, border: "1px solid " + T.purpleBorder, marginBottom: 12, fontFamily: T.mono, fontSize: 7.5, color: T.purple, lineHeight: 1.5 }}>Each quarter, all 21 agents reason via Claude about the market state. Predictions emerge from collective intelligence.</div>}

          {/* Scenario */}
          <div style={{ display: "flex", alignItems: "baseline", gap: 7, marginBottom: 10 }}>
            <span style={{ fontFamily: T.mono, fontSize: 8, color: T.green, letterSpacing: "2px" }}>01</span>
            <span style={{ fontFamily: T.cond, fontWeight: 700, fontSize: 13, textTransform: "uppercase", letterSpacing: "0.05em" }}>SCENARIO</span>
            <div style={{ flex: 1, height: 1, background: T.border }} />
          </div>
          <div style={{ display: "flex", gap: 4, marginBottom: 12 }}>
            {(["bear", "base", "bull"]).map(k => {
              const m = SCENARIO_META[k];
              return (<button key={k} onClick={() => setScenario(k)} style={{ flex: 1, padding: "7px 5px", cursor: "crosshair", textAlign: "left", background: scenario === k ? m.color + "10" : T.white, border: "1px solid " + (scenario === k ? m.color : T.border) }}>
                <div style={{ fontFamily: T.mono, fontSize: 8, fontWeight: 700, letterSpacing: "2px", color: m.color }}>{m.label}</div>
                <div style={{ fontFamily: T.mono, fontSize: 6.5, color: T.textLight, marginTop: 1, lineHeight: 1.3 }}>{m.desc.split(",")[0]}</div>
              </button>);
            })}
          </div>

          {/* Stimuli */}
          <div style={{ display: "flex", alignItems: "baseline", gap: 7, marginBottom: 8 }}>
            <span style={{ fontFamily: T.mono, fontSize: 8, color: T.blue, letterSpacing: "2px" }}>02</span>
            <span style={{ fontFamily: T.cond, fontWeight: 700, fontSize: 13, textTransform: "uppercase", letterSpacing: "0.05em" }}>STIMULI</span>
            {stims.length > 0 && <span style={{ fontFamily: T.mono, fontSize: 7.5, color: T.gold, fontWeight: 600 }}>{stims.length}</span>}
            <div style={{ flex: 1, height: 1, background: T.border }} />
          </div>
          <div style={{ display: "flex", gap: 3, marginBottom: 8, flexWrap: "wrap" }}>
            {cats.map(c => (<button key={c} onClick={() => setCatFilter(c)} style={{ fontFamily: T.mono, fontSize: 7, letterSpacing: "1px", padding: "2px 7px", cursor: "crosshair", background: catFilter === c ? T.blueDim : "transparent", border: "1px solid " + (catFilter === c ? T.blueBorder : T.border), color: catFilter === c ? T.blue : T.textLight }}>{c.toUpperCase()}</button>))}
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 3, marginBottom: 12, maxHeight: 320, overflowY: "auto" }}>
            {filtered.map(s => (<StimulusCard key={s.id} st={s} active={!!stims.find(x => x.id === s.id)} intensity={stims.find(x => x.id === s.id)?.intensity || 1} onToggle={toggle} onInt={setInt} />))}
          </div>

          <button onClick={runSim} disabled={simStatus === "running"} style={{ width: "100%", padding: "11px", background: simStatus === "running" ? T.bg2 : T.green, color: simStatus === "running" ? T.textDim : "#fff", border: "none", fontFamily: T.mono, fontSize: 9, fontWeight: 600, letterSpacing: "3px", cursor: simStatus === "running" ? "wait" : "crosshair", clipPath: "polygon(6px 0%, 100% 0%, calc(100% - 6px) 100%, 0% 100%)" }}>
            {simStatus === "running" ? `▸ SIMULATING Q${simRound}/${SIM_ROUNDS}...` : "▸ RUN SIMULATION"}
          </button>
          {simStatus === "running" && (<div style={{ marginTop: 6, height: 3, background: T.bg2 }}><div style={{ height: "100%", width: (simRound / SIM_ROUNDS * 100) + "%", background: T.purple, transition: "width 0.3s" }} /></div>)}
        </div>

        {/* RIGHT */}
        <div style={{ flex: 1, padding: "14px 20px", minWidth: 0, overflowY: "auto", maxHeight: "calc(100vh - 72px)" }}>
          {/* Metrics */}
          {final && initial ? (
            <div style={{ display: "flex", gap: 7, flexWrap: "wrap", marginBottom: 14 }}>
              <Metric compact label="STOCK" value={fmt(final.stockPrice)} sub={pct(safe(final.stockPrice - initial.stockPrice, initial.stockPrice))} color={final.stockPrice >= initial.stockPrice ? T.green : T.red} />
              <Metric compact label="mNAV" value={final.mNAV.toFixed(2) + "x"} color={final.mNAV > 1 ? T.green : T.red} />
              <Metric compact label="ETH/SHR" value={final.ethPerShare.toFixed(6)} sub={pct(safe(final.ethPerShare - initial.ethPerShare, initial.ethPerShare))} color={final.ethPerShare >= initial.ethPerShare ? T.green : T.red} />
              <Metric compact label="ETH" value={fmt(final.ethPrice)} color={T.blue} />
              <Metric compact label="SENT." value={(final.aggSentiment >= 0 ? "+" : "") + (final.aggSentiment * 100).toFixed(0)} sub={`${final.bullish}B / ${final.bearish}Be`} color={final.aggSentiment >= 0 ? T.green : T.red} />
              {final.llmPowered && <Metric compact label="ENGINE" value="LLM" sub="Claude-powered" color={T.purple} />}
            </div>
          ) : (
            <div style={{ display: "flex", gap: 7, flexWrap: "wrap", marginBottom: 14 }}>
              <Metric compact label="BMNR" value={fmt(live.price)} sub={dataStatus === "live" ? "Live" : "Cached"} color={T.blue} />
              <Metric compact label="mNAV" value={live.mNAV.toFixed(2) + "x"} color={T.green} />
              <Metric compact label="ETH" value={fmt(live.ethPrice)} color={T.blue} />
              <Metric compact label="AGENTS" value={AGENTS.length.toString()} color={T.purple} />
            </div>
          )}

          <div style={{ display: "flex", gap: 3, marginBottom: 14 }}>
            {["simulation", "agents", "scenarios", "flywheel"].map(t => (<TabBtn key={t} active={tab === t} label={t} onClick={() => setTab(t)} />))}
          </div>

          {/* SIMULATION TAB */}
          {tab === "simulation" && (<>
            {!data || data.length < 2 ? (
              <div style={{ textAlign: "center", padding: "50px 20px" }}>
                {simStatus === "running" ? (
                  <><div style={{ fontFamily: T.mono, fontSize: 10, letterSpacing: "2px", color: T.purple, marginBottom: 6, animation: "pulse 1.5s infinite" }}>AGENTS REASONING Q{simRound}...</div><div style={{ fontFamily: T.sans, fontSize: 12, fontWeight: 300, color: T.textDim }}>Each agent is analyzing the market via Claude</div></>
                ) : (
                  <><div style={{ fontFamily: T.mono, fontSize: 10, letterSpacing: "2px", color: T.textLight, marginBottom: 6 }}>NO SIMULATION YET</div><div style={{ fontFamily: T.sans, fontSize: 12, fontWeight: 300, color: T.textDim }}>Select a scenario, toggle stimuli, and run</div></>
                )}
              </div>
            ) : (<>
              <div style={{ background: T.white, border: "1px solid " + T.border, padding: "12px 9px 4px", marginBottom: 12 }}>
                <div style={{ fontFamily: T.mono, fontSize: 7.5, letterSpacing: "2px", color: sc.color, marginBottom: 6, paddingLeft: 3 }}>▸ STOCK PRICE · {sc.label} · {data.length - 1} QUARTERS {final?.llmPowered ? "· LLM" : "· FORMULA"}</div>
                <ResponsiveContainer width="100%" height={200}>
                  <ComposedChart data={chartData}>
                    <defs><linearGradient id="sg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={sc.color} stopOpacity={0.12} /><stop offset="100%" stopColor={sc.color} stopOpacity={0} /></linearGradient></defs>
                    <CartesianGrid strokeDasharray="3 3" stroke={T.border} />
                    <XAxis dataKey="round" tick={{ fontSize: 7, fontFamily: T.mono, fill: T.textLight }} tickFormatter={v => "Q" + v} />
                    <YAxis tick={{ fontSize: 7, fontFamily: T.mono, fill: T.textLight }} tickFormatter={v => "$" + v.toFixed(0)} />
                    <Tooltip content={<ChartTip />} />
                    <ReferenceLine y={live.price} stroke={T.gold} strokeDasharray="4 4" />
                    <Area type="monotone" dataKey="stockPrice" stroke={sc.color} strokeWidth={2} fill="url(#sg)" dot={{ fill: sc.color, r: 2 }} name="Stock $" />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>

              {/* Quarter narrative feed (LLM mode) */}
              {data.some(d => d.quarterSummary && d.llmPowered) && (
                <div style={{ background: T.white, border: "1px solid " + T.border, padding: "10px 12px", marginBottom: 12 }}>
                  <div style={{ fontFamily: T.mono, fontSize: 7.5, letterSpacing: "2px", color: T.purple, marginBottom: 8 }}>▸ QUARTER-BY-QUARTER NARRATIVE</div>
                  {data.filter(d => d.round > 0 && d.quarterSummary).map(d => (
                    <div key={d.round} style={{ display: "flex", gap: 8, marginBottom: 6, paddingBottom: 6, borderBottom: "1px solid " + T.border }}>
                      <div style={{ fontFamily: T.mono, fontSize: 8, color: sc.color, fontWeight: 700, minWidth: 20 }}>Q{d.round}</div>
                      <div style={{ fontFamily: T.sans, fontSize: 10, color: T.textDim, fontWeight: 300, lineHeight: 1.5 }}>
                        {d.quarterSummary}
                        {d.llmPowered === false && <span style={{ color: T.red, fontFamily: T.mono, fontSize: 7.5 }}> [formula fallback]</span>}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Verdict */}
              {final && initial && (
                <div style={{ padding: "12px 14px", position: "relative", background: final.stockPrice >= initial.stockPrice ? T.greenDim : T.redDim, border: "1px solid " + (final.stockPrice >= initial.stockPrice ? T.greenBorder : T.redBorder) }}>
                  <CornerBrackets color={final.stockPrice >= initial.stockPrice ? T.green : T.red} size={10} inset={5} />
                  <div style={{ fontFamily: T.mono, fontSize: 7.5, fontWeight: 600, letterSpacing: "3px", color: final.stockPrice >= initial.stockPrice ? T.green : T.red, marginBottom: 4 }}>▸ {sc.label} VERDICT {final.llmPowered ? "· LLM-DERIVED" : "· FORMULA"}</div>
                  <div style={{ fontFamily: T.sans, fontSize: 11, lineHeight: 1.7, color: T.textDim, fontWeight: 300 }}>
                    Over {SIM_ROUNDS} quarters, {AGENTS.length} agents drove BMNR from {fmt(initial.stockPrice)} to <strong style={{ color: T.text }}>{fmt(final.stockPrice)}</strong> ({pct(safe(final.stockPrice - initial.stockPrice, initial.stockPrice))}).
                    ETH/share: {initial.ethPerShare.toFixed(6)} → {final.ethPerShare.toFixed(6)}. mNAV: {initial.mNAV.toFixed(2)}x → {final.mNAV.toFixed(2)}x.
                    Consensus: {final.bullish} bullish / {final.bearish} bearish.{stims.length > 0 ? ` ${stims.length} stimuli shaped agent reasoning.` : ""}
                  </div>
                </div>
              )}
            </>)}
          </>)}

          {/* AGENTS TAB */}
          {tab === "agents" && (<>
            <div style={{ background: T.white, border: "1px solid " + T.border, overflow: "hidden", marginBottom: 12 }}>
              <div style={{ display: "grid", gridTemplateColumns: "17px 1fr 55px 52px", gap: 5, padding: "7px 9px", fontSize: 7, fontWeight: 600, color: T.textLight, textTransform: "uppercase", borderBottom: "1px solid " + T.borderMed, letterSpacing: "1.5px", fontFamily: T.mono, background: T.bg2 }}>
                <div></div><div>AGENT</div><div style={{ textAlign: "center" }}>SIGNAL</div><div style={{ textAlign: "right" }}>ACTION</div>
              </div>
              {(final ? final.agentSnapshot : AGENTS.map(a => ({ ...a, sentiment: a.bias, reasoning: a.persona.split(".")[0] + ".", action: "HOLD" }))).map(a => (
                <AgentRow key={a.id} agent={a} expanded={expandedAgent === a.id} onToggle={() => setExpandedAgent(expandedAgent === a.id ? null : a.id)} />
              ))}
            </div>
            <div style={{ padding: "10px 12px", background: T.purpleDim, border: "1px solid " + T.purpleBorder }}>
              <div style={{ fontFamily: T.mono, fontSize: 7.5, letterSpacing: "2px", color: T.purple, marginBottom: 4 }}>▸ {mode === "llm" ? "LLM AGENT REASONING" : "FORMULA AGENT MODEL"}</div>
              <div style={{ fontFamily: T.sans, fontSize: 10.5, lineHeight: 1.6, color: T.textDim, fontWeight: 300 }}>
                {mode === "llm" ? "Each agent's persona is sent to Claude with the full market context. The LLM reasons in-character about what that agent would think, feel, and do — producing emergent collective predictions rather than programmed outcomes. Click any agent row to see their reasoning." : "Agents update sentiment via network propagation formulas. Faster but less realistic — outcomes are pre-determined by equations, not emergent reasoning."}
              </div>
            </div>
          </>)}

          {/* SCENARIOS TAB */}
          {tab === "scenarios" && formulaResults && (<>
            <div style={{ background: T.white, border: "1px solid " + T.border, padding: "14px 9px 4px", marginBottom: 12 }}>
              <div style={{ fontFamily: T.mono, fontSize: 7.5, letterSpacing: "2px", color: T.textDim, marginBottom: 6, paddingLeft: 3 }}>▸ STOCK PRICE — ALL SCENARIOS (FORMULA)</div>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={formulaResults.base.map((d, i) => ({ round: d.round, bull: formulaResults.bull[i]?.stockPrice, base: formulaResults.base[i]?.stockPrice, bear: formulaResults.bear[i]?.stockPrice }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke={T.border} />
                  <XAxis dataKey="round" tick={{ fontSize: 7, fontFamily: T.mono, fill: T.textLight }} tickFormatter={v => "Q" + v} />
                  <YAxis tick={{ fontSize: 7, fontFamily: T.mono, fill: T.textLight }} tickFormatter={v => "$" + v.toFixed(0)} />
                  <Tooltip content={<ChartTip />} /><ReferenceLine y={live.price} stroke={T.gold} strokeDasharray="4 4" />
                  <Line type="monotone" dataKey="bull" stroke={T.green} strokeWidth={2} name="Bull" dot={false} />
                  <Line type="monotone" dataKey="base" stroke={T.blue} strokeWidth={2} name="Base" dot={false} />
                  <Line type="monotone" dataKey="bear" stroke={T.red} strokeWidth={2} name="Bear" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
              {(["bear", "base", "bull"]).map(k => { const m = SCENARIO_META[k]; const f = formulaResults[k]; const fl = f[f.length-1]; const fi = f[0]; return (
                <div key={k} style={{ background: T.white, border: "1px solid " + T.border, padding: 12, position: "relative" }}>
                  <div style={{ position: "absolute", top: 0, left: 0, width: "100%", height: 2, background: m.color, opacity: 0.6 }} />
                  <div style={{ fontFamily: T.mono, fontSize: 8, fontWeight: 700, letterSpacing: "2px", color: m.color, marginBottom: 3 }}>{m.label}</div>
                  <div style={{ fontFamily: T.sans, fontSize: 9, color: T.textDim, marginBottom: 8, fontWeight: 300 }}>{m.desc}</div>
                  {[{ l: "FINAL", v: fmt(fl.stockPrice), c: fl.stockPrice >= fi.stockPrice ? T.green : T.red },
                    { l: "RETURN", v: pct(safe(fl.stockPrice - fi.stockPrice, fi.stockPrice)), c: fl.stockPrice >= fi.stockPrice ? T.green : T.red },
                    { l: "mNAV", v: fl.mNAV.toFixed(2) + "x", c: fl.mNAV > 1 ? T.green : T.red },
                  ].map(({ l, v, c }) => (<div key={l} style={{ marginBottom: 3 }}><div style={{ fontFamily: T.mono, fontSize: 6.5, color: T.textLight, letterSpacing: "1px" }}>{l}</div><div style={{ fontFamily: T.mono, fontSize: 11, fontWeight: 700, color: c }}>{v}</div></div>))}
                </div>); })}
            </div>
          </>)}
          {tab === "scenarios" && !formulaResults && <div style={{ textAlign: "center", padding: "50px", color: T.textLight, fontFamily: T.sans, fontSize: 12, fontWeight: 300 }}>Run a simulation to compare scenarios</div>}

          {/* FLYWHEEL TAB */}
          {tab === "flywheel" && data && data.length > 1 && (<>
            <div style={{ background: T.white, border: "1px solid " + T.border, padding: "12px 9px 4px", marginBottom: 12 }}>
              <div style={{ fontFamily: T.mono, fontSize: 7.5, letterSpacing: "2px", color: T.green, marginBottom: 6, paddingLeft: 3 }}>▸ ETH/SHARE ACCRETION</div>
              <ResponsiveContainer width="100%" height={180}>
                <AreaChart data={chartData}>
                  <defs><linearGradient id="eg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={final.ethPerShare >= initial.ethPerShare ? T.green : T.red} stopOpacity={0.15} /><stop offset="100%" stopColor={final.ethPerShare >= initial.ethPerShare ? T.green : T.red} stopOpacity={0} /></linearGradient></defs>
                  <CartesianGrid strokeDasharray="3 3" stroke={T.border} />
                  <XAxis dataKey="round" tick={{ fontSize: 7, fontFamily: T.mono, fill: T.textLight }} tickFormatter={v => "Q" + v} />
                  <YAxis tick={{ fontSize: 7, fontFamily: T.mono, fill: T.textLight }} domain={["dataMin - 0.0001", "dataMax + 0.0001"]} tickFormatter={v => v.toFixed(5)} />
                  <Tooltip content={<ChartTip />} /><ReferenceLine y={initial.ethPerShare} stroke={T.gold} strokeDasharray="4 4" />
                  <Area type="monotone" dataKey="ethPerShare" stroke={final.ethPerShare >= initial.ethPerShare ? T.green : T.red} strokeWidth={2} fill="url(#eg)" dot={{ r: 2 }} name="ETH/Shr" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div style={{ background: T.white, border: "1px solid " + T.border, overflow: "hidden" }}>
              <div style={{ display: "grid", gridTemplateColumns: "28px 1fr 1fr 1fr 1fr 1fr 48px", gap: 4, padding: "7px 9px", fontSize: 7, fontWeight: 600, color: T.textLight, textTransform: "uppercase", borderBottom: "1px solid " + T.borderMed, letterSpacing: "1.5px", fontFamily: T.mono, background: T.bg2 }}>
                <div>Q</div><div>ISSUED</div><div>ETH IN</div><div>ETH/SHR</div><div>mNAV</div><div>PRICE</div><div style={{ textAlign: "right" }}>ACCR?</div>
              </div>
              {data.slice(1).map(d => (<div key={d.round} style={{ display: "grid", gridTemplateColumns: "28px 1fr 1fr 1fr 1fr 1fr 48px", gap: 4, padding: "5px 9px", fontSize: 9, fontFamily: T.mono, borderBottom: "1px solid " + T.border }}>
                <div style={{ color: T.textLight, fontWeight: 700 }}>{d.round}</div>
                <div>{d.sharesIssued > 0 ? fN(d.sharesIssued) : "—"}</div>
                <div style={{ color: T.blue }}>{d.ethBought > 0 ? fN(d.ethBought) : "—"}</div>
                <div>{d.ethPerShare.toFixed(6)}</div>
                <div style={{ color: d.isAccretive ? T.green : T.red, fontWeight: 600 }}>{d.mNAV.toFixed(2)}x</div>
                <div style={{ color: T.textDim }}>{fmt(d.stockPrice)}</div>
                <div style={{ textAlign: "right", fontWeight: 700, color: d.isAccretive ? T.green : T.red }}>{d.isAccretive ? "YES" : "NO"}</div>
              </div>))}
            </div>
          </>)}
          {tab === "flywheel" && (!data || data.length < 2) && <div style={{ textAlign: "center", padding: "50px", color: T.textLight, fontFamily: T.sans, fontSize: 12, fontWeight: 300 }}>Run a simulation to see flywheel data</div>}
        </div>
      </div>

      <div style={{ padding: "8px 22px", borderTop: "1px solid " + T.border, display: "flex", justifyContent: "space-between", background: T.white }}>
        <span style={{ fontFamily: T.mono, fontSize: 7, color: T.textLight, letterSpacing: "2px" }}><span style={{ color: T.green, fontWeight: 600 }}>WEDGE</span> × MIROFISH × BMNR</span>
        <span style={{ fontFamily: T.mono, fontSize: 7, color: T.textLight, letterSpacing: "1px" }}>EDUCATIONAL ONLY · NOT FINANCIAL ADVICE · {mode === "llm" ? "LLM AGENT-BASED" : "FORMULA"} MODEL</span>
      </div>
    </div>
  );
}
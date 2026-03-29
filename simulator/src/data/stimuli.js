/**
 * Market Stimuli Catalog
 * 
 * Each stimulus represents a market event that agents react to.
 * `impact` is the base directional strength (-1 to 1).
 * 
 * To add a new stimulus:
 * 1. Add an entry with a unique `id`
 * 2. Set `cat` to an existing category or create a new one
 * 3. Set `impact` — positive = bullish, negative = bearish
 * 4. Write a clear `desc` for the UI
 */

export const STIMULI = [
  // ── ETH Ecosystem ──
  { id: "eth_5k", name: "ETH Breaks $5,000", cat: "ETH", icon: "🚀", impact: 0.7, desc: "Institutional adoption wave" },
  { id: "eth_crash", name: "ETH Crashes < $800", cat: "ETH", icon: "💀", impact: -0.8, desc: "Crypto winter 3.0" },
  { id: "eth_etf_in", name: "ETH ETF Mega-Inflows", cat: "ETH", icon: "📈", impact: 0.5, desc: "$10B+ spot ETF flows" },
  { id: "eth_etf_out", name: "ETH ETF Redemptions", cat: "ETH", icon: "📤", impact: -0.45, desc: "Institutions dump positions" },
  { id: "eth_upgrade", name: "Pectra Upgrade", cat: "ETH", icon: "⬆️", impact: 0.3, desc: "Protocol upgrade succeeds" },

  // ── BitMine Business ──
  { id: "mavan", name: "MAVAN Staking Live", cat: "BitMine", icon: "⚡", impact: 0.6, desc: "$330M+ annual staking rev" },
  { id: "mavan_delay", name: "MAVAN Delayed", cat: "BitMine", icon: "⏳", impact: -0.35, desc: "Technical issues" },
  { id: "alchemy5", name: "Alchemy 5% Hit", cat: "BitMine", icon: "🧪", impact: 0.65, desc: "5% of all ETH supply" },
  { id: "beast_ipo", name: "Beast Industries IPO", cat: "BitMine", icon: "🎬", impact: 0.4, desc: "$200M stake monetized" },
  { id: "scandal", name: "Executive Scandal", cat: "BitMine", icon: "⚠️", impact: -0.6, desc: "Accounting concerns" },
  { id: "sp500", name: "Index Inclusion", cat: "BitMine", icon: "🏛️", impact: 0.45, desc: "S&P 500 / Russell add" },

  // ── Corporate ──
  { id: "dilution", name: "100x Auth Used", cat: "Corporate", icon: "💧", impact: -0.55, desc: "Massive dilution" },
  { id: "buyback", name: "Buyback $500M", cat: "Corporate", icon: "🔄", impact: 0.35, desc: "Aggressive buyback" },
  { id: "convert", name: "Convertible $2B", cat: "Corporate", icon: "📜", impact: -0.2, desc: "Debt for ETH buys" },

  // ── Macro ──
  { id: "fed_cut", name: "Fed Cuts 150bps", cat: "Macro", icon: "📉", impact: 0.4, desc: "Aggressive easing" },
  { id: "recession", name: "US Recession", cat: "Macro", icon: "🏚️", impact: -0.5, desc: "Risk-off everywhere" },
  { id: "pro_crypto", name: "Pro-Crypto Law", cat: "Macro", icon: "⚖️", impact: 0.4, desc: "Regulatory clarity" },
  { id: "sec", name: "SEC Crackdown", cat: "Macro", icon: "🚫", impact: -0.6, desc: "Investment co. risk" },
  { id: "btc_150k", name: "BTC $150K", cat: "Macro", icon: "₿", impact: 0.45, desc: "BTC supercycle" },

  // ── Technical ──
  { id: "squeeze", name: "Short Squeeze", cat: "Technical", icon: "🔥", impact: 0.6, desc: "30%+ SI unwind" },
  { id: "ark_exit", name: "ARK Sells All", cat: "Technical", icon: "🚪", impact: -0.5, desc: "Cathie exits" },
  { id: "rival", name: "Rival Treasury", cat: "Technical", icon: "🏁", impact: -0.25, desc: "Major competitor" },

  // ── Social ──
  { id: "viral", name: "Viral Social Pump", cat: "Social", icon: "📱", impact: 0.3, desc: "BMNR trends on X" },
  { id: "fud", name: "Coordinated FUD", cat: "Social", icon: "🗞️", impact: -0.35, desc: "Short-seller report" },
  { id: "openai", name: "OpenAI/Eightco Win", cat: "Social", icon: "🤖", impact: 0.35, desc: "$80M bet pays off" },
];

export const STIMULUS_CATEGORIES = [...new Set(STIMULI.map(s => s.cat))];

/**
 * LLM Provider Abstraction Layer
 * 
 * Add your own provider by implementing the LLMProvider interface:
 * - id: unique string identifier
 * - name: display name
 * - call(messages, options): async function returning { text: string }
 * 
 * Supported out of the box:
 * - Anthropic (Claude) — via claude.ai artifact API or direct API
 * - OpenAI (GPT-4, etc.) — via direct API
 * - Google (Gemini) — via direct API
 * - OpenRouter — meta-provider supporting 100+ models
 * - Ollama — local models, no API key needed
 * - Custom — bring your own endpoint
 */

// ─── JSON PARSER (shared across all providers) ───
export function parseJSON(text) {
  if (!text || text.length < 10) return null;

  // Strip markdown fences
  let cleaned = text.replace(/```json\s*/gi, "").replace(/```\s*/g, "").trim();

  // Try direct parse
  try { return JSON.parse(cleaned); } catch {}

  // Fallback: find outermost { } containing "agents"
  const idx = cleaned.indexOf('"agents"');
  if (idx === -1) return null;
  let start = cleaned.lastIndexOf("{", idx);
  if (start === -1) return null;
  let depth = 0, end = -1;
  for (let i = start; i < cleaned.length; i++) {
    if (cleaned[i] === "{") depth++;
    else if (cleaned[i] === "}") { depth--; if (depth === 0) { end = i; break; } }
  }
  if (end === -1) return null;
  try { return JSON.parse(cleaned.slice(start, end + 1)); } catch { return null; }
}

// ─── ANTHROPIC PROVIDER ───
export const AnthropicProvider = {
  id: "anthropic",
  name: "Anthropic (Claude)",
  models: ["claude-sonnet-4-20250514", "claude-haiku-4-5-20251001"],
  defaultModel: "claude-sonnet-4-20250514",
  requiresKey: false, // false when running inside claude.ai artifacts

  async call(messages, { model, maxTokens = 4096, apiKey } = {}) {
    const headers = { "Content-Type": "application/json" };
    if (apiKey) {
      headers["x-api-key"] = apiKey;
      headers["anthropic-version"] = "2023-06-01";
    }

    const res = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers,
      body: JSON.stringify({
        model: model || this.defaultModel,
        max_tokens: maxTokens,
        messages,
      }),
    });

    if (!res.ok) {
      const err = await res.text().catch(() => "");
      throw new Error(`Anthropic ${res.status}: ${err.slice(0, 200)}`);
    }

    const data = await res.json();
    const text = (data.content || []).filter(b => b.type === "text").map(b => b.text).join("\n");
    return { text, raw: data };
  }
};

// ─── OPENAI PROVIDER ───
export const OpenAIProvider = {
  id: "openai",
  name: "OpenAI (GPT-4)",
  models: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o3-mini"],
  defaultModel: "gpt-4o",
  requiresKey: true,

  async call(messages, { model, maxTokens = 4096, apiKey } = {}) {
    if (!apiKey) throw new Error("OpenAI requires an API key. Set it in Settings → LLM Provider.");

    const res = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify({
        model: model || this.defaultModel,
        max_tokens: maxTokens,
        messages: messages.map(m => ({ role: m.role, content: m.content })),
        temperature: 0.7,
      }),
    });

    if (!res.ok) {
      const err = await res.text().catch(() => "");
      throw new Error(`OpenAI ${res.status}: ${err.slice(0, 200)}`);
    }

    const data = await res.json();
    const text = data.choices?.[0]?.message?.content || "";
    return { text, raw: data };
  }
};

// ─── GOOGLE GEMINI PROVIDER ───
export const GeminiProvider = {
  id: "gemini",
  name: "Google (Gemini)",
  models: ["gemini-2.5-flash", "gemini-2.5-pro"],
  defaultModel: "gemini-2.5-flash",
  requiresKey: true,

  async call(messages, { model, maxTokens = 4096, apiKey } = {}) {
    if (!apiKey) throw new Error("Gemini requires an API key from ai.google.dev.");

    const m = model || this.defaultModel;
    const contents = messages.map(msg => ({
      role: msg.role === "assistant" ? "model" : "user",
      parts: [{ text: msg.content }],
    }));

    const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${m}:generateContent?key=${apiKey}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents,
        generationConfig: { maxOutputTokens: maxTokens, temperature: 0.7 },
      }),
    });

    if (!res.ok) {
      const err = await res.text().catch(() => "");
      throw new Error(`Gemini ${res.status}: ${err.slice(0, 200)}`);
    }

    const data = await res.json();
    const text = data.candidates?.[0]?.content?.parts?.[0]?.text || "";
    return { text, raw: data };
  }
};

// ─── OPENROUTER PROVIDER (100+ models) ───
export const OpenRouterProvider = {
  id: "openrouter",
  name: "OpenRouter (Multi-Model)",
  models: [
    "anthropic/claude-sonnet-4",
    "openai/gpt-4o",
    "google/gemini-2.5-flash",
    "meta-llama/llama-4-maverick",
    "deepseek/deepseek-r1",
    "mistralai/mistral-large-latest",
  ],
  defaultModel: "anthropic/claude-sonnet-4",
  requiresKey: true,

  async call(messages, { model, maxTokens = 4096, apiKey } = {}) {
    if (!apiKey) throw new Error("OpenRouter requires an API key from openrouter.ai.");

    const res = await fetch("https://openrouter.ai/api/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
        "HTTP-Referer": "https://github.com/mirofish-bmnr",
        "X-Title": "MiroFish BMNR Simulator",
      },
      body: JSON.stringify({
        model: model || this.defaultModel,
        max_tokens: maxTokens,
        messages: messages.map(m => ({ role: m.role, content: m.content })),
      }),
    });

    if (!res.ok) {
      const err = await res.text().catch(() => "");
      throw new Error(`OpenRouter ${res.status}: ${err.slice(0, 200)}`);
    }

    const data = await res.json();
    const text = data.choices?.[0]?.message?.content || "";
    return { text, raw: data };
  }
};

// ─── OLLAMA PROVIDER (local, free) ───
export const OllamaProvider = {
  id: "ollama",
  name: "Ollama (Local)",
  models: ["llama3.1:70b", "llama3.1:8b", "mixtral:8x7b", "qwen2.5:32b", "deepseek-r1:32b", "gemma3:27b"],
  defaultModel: "llama3.1:70b",
  requiresKey: false,

  async call(messages, { model, maxTokens = 4096, baseUrl = "http://localhost:11434" } = {}) {
    const res = await fetch(`${baseUrl}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: model || this.defaultModel,
        messages: messages.map(m => ({ role: m.role, content: m.content })),
        stream: false,
        options: { num_predict: maxTokens, temperature: 0.7 },
      }),
    });

    if (!res.ok) {
      const err = await res.text().catch(() => "");
      throw new Error(`Ollama ${res.status}: ${err.slice(0, 200)}`);
    }

    const data = await res.json();
    const text = data.message?.content || "";
    return { text, raw: data };
  }
};

// ─── CUSTOM OPENAI-COMPATIBLE PROVIDER ───
export const CustomProvider = {
  id: "custom",
  name: "Custom (OpenAI-compatible)",
  models: ["default"],
  defaultModel: "default",
  requiresKey: true,

  async call(messages, { model, maxTokens = 4096, apiKey, baseUrl } = {}) {
    if (!baseUrl) throw new Error("Custom provider requires a base URL. Set it in Settings.");

    const headers = { "Content-Type": "application/json" };
    if (apiKey) headers.Authorization = `Bearer ${apiKey}`;

    const res = await fetch(`${baseUrl}/v1/chat/completions`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        model: model || "default",
        max_tokens: maxTokens,
        messages: messages.map(m => ({ role: m.role, content: m.content })),
      }),
    });

    if (!res.ok) {
      const err = await res.text().catch(() => "");
      throw new Error(`Custom ${res.status}: ${err.slice(0, 200)}`);
    }

    const data = await res.json();
    const text = data.choices?.[0]?.message?.content || "";
    return { text, raw: data };
  }
};

// ─── PROVIDER REGISTRY ───
export const PROVIDERS = {
  anthropic: AnthropicProvider,
  openai: OpenAIProvider,
  gemini: GeminiProvider,
  openrouter: OpenRouterProvider,
  ollama: OllamaProvider,
  custom: CustomProvider,
};

export function getProvider(id) {
  return PROVIDERS[id] || AnthropicProvider;
}

export function getAllProviders() {
  return Object.values(PROVIDERS);
}

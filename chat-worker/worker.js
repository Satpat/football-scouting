// football-chat — a stateless Cloudflare Worker that turns a football question
// into SQL, and SQL results into prose.
//
// It is the ONLY backend the scouting site has: the site stays a static
// Observable Framework build on GitHub Pages, and this Worker holds the OpenAI
// key so the key never touches a visitor's browser. It stores nothing.
//
// Flow:  browser POST { system, messages }  ->  OpenAI (structured output)
//        ->  { action: "query", sql } | { action: "answer", answer }  ->  browser
//
// The Worker never sees football data. All 9 tables live in the browser in
// DuckDB-WASM, so the browser runs the SQL and owns the retry loop; this Worker
// is a single-shot relay. That is why it can stay stateless and tiny.
//
// The model may only CHOOSE WHAT TO ASK. It never supplies figures: every number
// in an answer comes from a query the page actually ran and always displays.
// That is this Worker's equivalent of rr-tailor's sanitize() — the model cannot
// invent a goal tally any more than the tailor can invent an employer.

// ── config (change these two if the model name / effort ever changes) ────────
// Deliberately NOT rr-tailor's gpt-5.5/high: that Worker does one careful
// resume rewrite and takes 15-30s, which is right there and wrong here. Chat
// needs fast turns, and SQL generation is cheap, checkable and retryable.
const MODEL = "gpt-5.6-luna";
const REASONING_EFFORT = "low"; // one of: low | medium | high | xhigh | max
const OPENAI_URL = "https://api.openai.com/v1/responses";
const MAX_OUTPUT_TOKENS = 3000;

// Models the page is allowed to escalate to, so a stray or forged request can't
// select something expensive. Keep in sync with the selector in src/chat.md.
const ALLOWED_MODELS = ["gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"];

// Only these origins may call the Worker. Localhost is allowed too so the page
// can be tested against `npm run dev` before it ships to Pages.
const ALLOWED_ORIGINS = ["https://satpat.github.io"];
const ALLOW_LOCAL = true;

// Size caps. The system prompt is built in the browser from labels.json +
// notes.json + DESCRIBE output (~15K tokens) and sent with each request — that
// keeps prompt iteration a page edit instead of a Worker redeploy. These caps
// stop the relay being used to ship something much larger than that.
const MAX_SYSTEM_CHARS = 120000;
const MAX_BODY_CHARS = 400000;
const MAX_MESSAGES = 24;

// ── structured-output schema (strict) ───────────────────────────────────────
// One shape for both steps. strict json_schema requires every property to be
// listed in `required`, so the unused branch is sent as null rather than omitted.
const SCHEMA = {
  type: "object",
  additionalProperties: false,
  required: ["action", "sql", "answer", "note"],
  properties: {
    action: { type: "string", enum: ["query", "answer"] },
    sql: { type: ["string", "null"], description: "DuckDB SELECT when action is query, else null" },
    answer: { type: ["string", "null"], description: "Markdown answer when action is answer, else null" },
    note: { type: ["string", "null"], description: "One short line on what this step is for" },
  },
};

// ── entry point ──────────────────────────────────────────────────────────────
export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const allowed = originAllowed(origin);

    if (request.method === "OPTIONS") {
      return new Response(null, { status: allowed ? 204 : 403, headers: cors(origin) });
    }
    if (request.method !== "POST") return reply({ error: "Method not allowed" }, 405, origin);
    if (!allowed) return reply({ error: "Origin not allowed" }, 403, origin);

    const ip = request.headers.get("CF-Connecting-IP") || "unknown";
    if (rateLimited(ip)) {
      return reply({ error: "Too many requests — slow down and try again shortly." }, 429, origin);
    }

    return handleChat(request, env, origin);
  },
};

// ── rate limiting ────────────────────────────────────────────────────────────
// Best-effort, not a hard guarantee: this Map lives in one Worker isolate and resets
// whenever Cloudflare recycles it, so it won't stop a determined or distributed abuser.
// It's here to blunt a stray script looping on this endpoint — the origin allowlist
// above is the only other gate, and it's forgeable. For real production traffic, add a
// Cloudflare rate-limiting rule in front of this instead (see README "Security notes").
const RATE_LIMIT_WINDOW_MS = 60_000;
const RATE_LIMIT_MAX = 12; // requests per IP per window
const rateLimitHits = new Map(); // ip -> recent request timestamps

function rateLimited(ip) {
  const now = Date.now();
  const hits = (rateLimitHits.get(ip) ?? []).filter((t) => now - t < RATE_LIMIT_WINDOW_MS);
  hits.push(now);
  rateLimitHits.set(ip, hits);
  // Cap how many distinct IPs we track so a spray of one-off callers can't grow this
  // map without bound between isolate recycles.
  if (rateLimitHits.size > 5000) rateLimitHits.clear();
  return hits.length > RATE_LIMIT_MAX;
}

// ── /chat — one step of the question -> SQL -> answer loop ───────────────────
async function handleChat(request, env, origin) {
  const raw = await request.text();
  if (raw.length > MAX_BODY_CHARS) {
    return reply({ error: "Request too large" }, 413, origin);
  }

  let body;
  try {
    body = JSON.parse(raw);
  } catch {
    return reply({ error: "Invalid JSON body" }, 400, origin);
  }

  const { system, messages, model } = body || {};
  if (typeof system !== "string" || !system.trim()) {
    return reply({ error: "Missing system prompt" }, 400, origin);
  }
  if (system.length > MAX_SYSTEM_CHARS) {
    return reply({ error: "System prompt too large" }, 413, origin);
  }
  if (!Array.isArray(messages) || messages.length === 0) {
    return reply({ error: "Missing messages" }, 400, origin);
  }
  if (messages.length > MAX_MESSAGES) {
    return reply({ error: "Too many messages" }, 413, origin);
  }
  for (const m of messages) {
    if (!m || (m.role !== "user" && m.role !== "assistant") || typeof m.content !== "string") {
      return reply({ error: "Malformed message" }, 400, origin);
    }
  }

  // Unknown model names fall back to the default rather than erroring, so a
  // stale page cached in someone's browser keeps working after a rename.
  const chosen = ALLOWED_MODELS.includes(model) ? model : MODEL;

  // Plumbing test with no key and no spend — see .dev.vars.example.
  if (env.CHAT_MOCK === "1") {
    return reply(mockStep(messages), 200, origin);
  }

  if (!env.OPENAI_API_KEY) return reply({ error: "Worker missing OPENAI_API_KEY" }, 500, origin);

  let out;
  try {
    out = await callOpenAI(env.OPENAI_API_KEY, system, messages, chosen);
  } catch (e) {
    return reply({ error: "Chat failed upstream", detail: String(e).slice(0, 300) }, 502, origin);
  }
  return reply(sanitizeStep(out), 200, origin);
}

// ── OpenAI call (Responses API, structured output) ───────────────────────────
async function callOpenAI(key, system, messages, model) {
  return callResponses(key, {
    model,
    input: [{ role: "system", content: system }, ...messages],
    text: { format: { type: "json_schema", name: "chat_step", schema: SCHEMA, strict: true } },
    max_output_tokens: MAX_OUTPUT_TOKENS,
  });
}

// Shared Responses-API call: structured output, with the reasoning-param
// fallback shape. Returns the parsed JSON payload.
async function callResponses(key, base) {
  // The Responses API takes reasoning as { effort }. A couple of API surfaces
  // instead expect a top-level reasoning_effort; if the first shape is rejected
  // for a reasoning-param reason, retry with the other so a param rename upstream
  // doesn't hard-break this.
  let res = await postJson(key, { ...base, reasoning: { effort: REASONING_EFFORT } });
  if (!res.ok) {
    const errText = await res.text();
    if (res.status === 400 && /reasoning/i.test(errText)) {
      res = await postJson(key, { ...base, reasoning_effort: REASONING_EFFORT });
      if (!res.ok) throw new Error(`OpenAI ${res.status}: ${(await res.text()).slice(0, 300)}`);
    } else {
      throw new Error(`OpenAI ${res.status}: ${errText.slice(0, 300)}`);
    }
  }

  const data = await res.json();
  if (data.status && data.status !== "completed") {
    throw new Error(`OpenAI status ${data.status}`);
  }
  const step = JSON.parse(extractText(data));
  // Usage is surfaced so the page can show what a question actually cost.
  if (data.usage) step.usage = data.usage;
  return step;
}

function postJson(key, payload) {
  return fetch(OPENAI_URL, {
    method: "POST",
    headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

// The Responses API returns an aggregated `output_text`; fall back to walking
// the output array for the message's text part.
function extractText(data) {
  if (typeof data.output_text === "string" && data.output_text.trim()) return data.output_text;
  const msg = (data.output || []).find((o) => o.type === "message");
  const part = msg && (msg.content || []).find((c) => c.type === "output_text" || c.type === "text");
  if (part && part.text) return part.text;
  throw new Error("No output text in response");
}

// ── sanitize ─────────────────────────────────────────────────────────────────
// Make the branch coherent before it reaches the page: a "query" with no SQL and
// an "answer" with no text are both dead ends the page would otherwise have to
// guess at. The SQL itself is guarded browser-side in chat-agent.js, next to the
// DuckDB connection that has to run it.
function sanitizeStep(out) {
  const action = out.action === "query" && str(out.sql) ? "query" : "answer";
  const step = {
    action,
    sql: action === "query" ? out.sql.trim() : null,
    answer: action === "answer" ? (str(out.answer) ? out.answer.trim() : "I couldn't work that one out.") : null,
    note: str(out.note) ? out.note.trim().slice(0, 300) : null,
  };
  if (out.usage) step.usage = out.usage;
  return step;
}

function str(v) {
  return typeof v === "string" && v.trim().length > 0;
}

// ── mock (CHAT_MOCK=1): exercises the full browser loop with no OpenAI spend ──
// First call asks for a query; once a result has come back, it answers. That is
// the same two-phase shape the real model produces — including a `usage` figure,
// so the page's loop, SQL guard, table rendering, deep links and cost display can
// all be tested offline.
function mockStep(messages) {
  const sawResult = messages.some((m) => m.role === "user" && m.content.includes("Query result"));
  if (sawResult) {
    return {
      action: "answer",
      sql: null,
      answer: "**Mock answer.** The loop ran end to end: the page sent a question, got SQL back, executed it in DuckDB, and returned here with the rows.",
      note: "mock",
      usage: { input_tokens: 420, output_tokens: 65 },
    };
  }
  return {
    action: "query",
    sql: "SELECT player_id, team_id, player_name, club, league, goals\nFROM players\nORDER BY goals DESC\nLIMIT 5",
    note: "mock: top scorers",
    usage: { input_tokens: 380, output_tokens: 40 },
  };
}

// ── CORS helpers ─────────────────────────────────────────────────────────────
function originAllowed(origin) {
  if (!origin) return ALLOW_LOCAL; // some fetches send no Origin header
  if (ALLOWED_ORIGINS.includes(origin)) return true;
  if (ALLOW_LOCAL && (origin === "null" || /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(origin))) {
    return true;
  }
  return false;
}
// Only ever reflects an Origin that's actually on the allowlist — a disallowed origin gets
// "null" here, not its own value, so the response headers can't be misread as granting an
// origin they were sent to reject.
function cors(origin) {
  return {
    "Access-Control-Allow-Origin": originAllowed(origin) ? (origin || "*") : "null",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    Vary: "Origin",
  };
}
function reply(obj, status, origin) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json", ...cors(origin) },
  });
}

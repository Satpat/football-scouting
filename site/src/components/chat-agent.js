// The chat loop: question -> SQL -> rows -> answer.
//
// The loop lives here, in the browser, because the data does: all nine tables are
// already in DuckDB-WASM from the page's `sql:` front matter. The Worker only ever
// answers "what should I ask next?", which is why it can stay stateless.

// Rows shown in the page's table. The model sees far fewer (MODEL_ROWS) — it needs
// enough to characterise the result, not the whole thing.
const MAX_ROWS = 500;
const MODEL_ROWS = 50;

// How long the page waits on a query before giving up on it. DuckDB-WASM has no
// cancellation hook reachable from here, so a runaway query (a big cross join, a
// runaway recursive CTE) keeps burning CPU in the worker thread regardless — this
// only stops the *page* waiting on it forever, so the loop can report the failure
// and the visitor can try a narrower question instead of reloading the tab.
const QUERY_TIMEOUT_MS = 20000;

// ── SQL guard ────────────────────────────────────────────────────────────────
// Not a security boundary: every byte of this data is public and already sitting in
// the visitor's browser. It is here so a stray statement can't corrupt the DuckDB
// session mid-conversation, and so failures read as "rejected, because X" instead of
// a mangled table. This is the counterpart of rr-tailor's sanitize().
const FORBIDDEN = /\b(attach|detach|copy|install|load|create|insert|update|delete|drop|alter|pragma|export|truncate|vacuum|checkpoint)\b/i;

export function guardSql(sql) {
  const raw = String(sql ?? "").trim();
  if (!raw) return {ok: false, reason: "empty query"};

  // One statement only. A single trailing semicolon is fine; anything else is not.
  const body = raw.replace(/;\s*$/, "");
  if (body.includes(";")) return {ok: false, reason: "multiple statements are not allowed"};
  if (!/^\s*(with|select)\b/i.test(body)) return {ok: false, reason: "only SELECT or WITH queries are allowed"};

  const hit = body.match(FORBIDDEN);
  if (hit) return {ok: false, reason: `"${hit[0]}" is not allowed — this is read-only`};

  return {ok: true, sql: body};
}

// ── running it ───────────────────────────────────────────────────────────────
// Arrow hands back BigInt for BIGINT columns and Date for dates; both break
// JSON.stringify on the way to the model, so flatten them here once.
function plain(v) {
  if (typeof v === "bigint") return Number(v);
  if (v instanceof Date) return v.toISOString().slice(0, 10);
  return v;
}

export async function runSql(query, sql) {
  // Wrap rather than trusting the model to limit: one forgotten LIMIT over
  // member_matches is 42,308 rows into the page.
  const timeout = new Promise((_, reject) =>
    setTimeout(() => reject(new Error(`Query took longer than ${QUERY_TIMEOUT_MS / 1000}s — try a narrower question`)), QUERY_TIMEOUT_MS));
  const result = await Promise.race([query(`SELECT * FROM (${sql}) AS _q LIMIT ${MAX_ROWS + 1}`), timeout]);
  const columns = result.schema.fields.map((f) => f.name);
  const all = result.toArray().map((r) => {
    const o = r.toJSON();
    for (const k of Object.keys(o)) o[k] = plain(o[k]);
    return o;
  });
  const truncated = all.length > MAX_ROWS;
  return {columns, rows: truncated ? all.slice(0, MAX_ROWS) : all, truncated};
}

// ── the Worker call ──────────────────────────────────────────────────────────
async function step(endpoint, system, messages, model) {
  let res;
  try {
    res = await fetch(endpoint, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({system, messages, model}),
    });
  } catch {
    throw new Error("Couldn't reach the chat service. Check your connection and try again.");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error ? `${data.error}${data.detail ? ` — ${data.detail}` : ""}` : `Chat service returned ${res.status}`);
  return data;
}

// ── the loop ─────────────────────────────────────────────────────────────────
// Returns {answer, steps, usage}. `steps` is what the page renders under the answer:
// one entry per query attempt, each with its SQL and either rows or a failure.
export async function ask({question, history = [], system, model, query, endpoint, onStep, maxQueries = 3}) {
  const messages = [...history, {role: "user", content: question}];
  const steps = [];
  const usage = {input_tokens: 0, output_tokens: 0};

  for (let i = 0; i <= maxQueries; i++) {
    const forceAnswer = i === maxQueries;
    if (forceAnswer) {
      messages.push({
        role: "user",
        content: "No more queries are available. Answer now using only the results above. If they are not enough, say what is missing.",
      });
    }

    onStep?.({phase: "thinking", attempt: i + 1});
    const out = await step(endpoint, system, messages, model);
    if (out.usage) {
      usage.input_tokens += out.usage.input_tokens ?? 0;
      usage.output_tokens += out.usage.output_tokens ?? 0;
    }

    if (out.action === "answer" || forceAnswer) {
      return {answer: out.answer ?? "I couldn't work that one out.", steps, usage};
    }

    // action === "query"
    messages.push({role: "assistant", content: JSON.stringify({action: "query", sql: out.sql})});

    const guard = guardSql(out.sql);
    if (!guard.ok) {
      steps.push({sql: out.sql, note: out.note, error: `Rejected: ${guard.reason}`});
      onStep?.({phase: "rejected", attempt: i + 1, reason: guard.reason});
      messages.push({role: "user", content: `That SQL was rejected: ${guard.reason}. Send a single read-only SELECT.`});
      continue;
    }

    onStep?.({phase: "running", attempt: i + 1, sql: guard.sql, note: out.note});
    try {
      const {columns, rows, truncated} = await runSql(query, guard.sql);
      steps.push({sql: guard.sql, note: out.note, columns, rows, truncated});
      // Errors and empty results both go back as ordinary results so the model can
      // correct itself rather than the turn dying on a typo.
      messages.push({
        role: "user",
        content: `Query result (${rows.length}${truncated ? "+" : ""} rows)${truncated ? ", truncated" : ""}:\n` +
          (rows.length ? JSON.stringify(rows.slice(0, MODEL_ROWS)) : "[] — no rows matched."),
      });
    } catch (e) {
      const msg = String(e.message ?? e).slice(0, 400);
      steps.push({sql: guard.sql, note: out.note, error: msg});
      onStep?.({phase: "failed", attempt: i + 1, error: msg});
      messages.push({role: "user", content: `Query failed: ${msg}\nFix the SQL and try again.`});
    }
  }

  return {answer: "I couldn't work that one out.", steps, usage};
}

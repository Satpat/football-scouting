---
title: Ask the data
toc: false
sql:
  players: ./data/players.csv
  shortlist: ./data/shortlist.csv
  careers: ./data/careers.csv
  matches: ./data/matches.csv
  ladders: ./data/ladders.csv
  teams: ./data/teams.csv
  clubs: ./data/clubs.csv
  appearances: ./data/appearances.parquet
  member_matches: ./data/member_matches.parquet
---

# Ask the data

```js
import {labels, fmt, formats, iconHeaders, clubCell, shortLeagueOnly} from "./components/labels.js";
import {dataTable} from "./components/data-table.js";
import {buildSchemaPrompt} from "./components/schema-prompt.js";
import {ask} from "./components/chat-agent.js";
import {renderMarkdown} from "./components/markdown.js";
const meta = await FileAttachment("./data/meta.json").json();
```

```js
// Framework's page-scope `sql` is a tagged template; joining a one-element array runs
// a dynamic string through the same DuckDB connection the other pages use.
const query = (q) => sql([q]);
// Built once per page load from labels.json + notes.json + DESCRIBE — see schema-prompt.js.
const system = await buildSchemaPrompt(query);
```

```js
// The Worker is the only backend. Locally it's `npm run dev` in chat-worker/;
// in production it's the deployed Cloudflare Worker.
const ENDPOINT = ["localhost", "127.0.0.1"].includes(location.hostname)
  ? "http://127.0.0.1:8787/chat"
  : "https://football-chat.veerlo.workers.dev/chat";
```

<div class="section">
  <div>

```js
const modelSel = Inputs.select(
  new Map([["Fast (default)", "gpt-5.6-luna"], ["Balanced", "gpt-5.6-terra"], ["Thorough", "gpt-5.6-sol"]]),
  {label: "Model", value: "gpt-5.6-luna"}
);
display(modelSel);
```
  <p class="muted">Every answer is produced by a real SQL query, shown under it. Fast is right for almost everything; escalate if an answer looks wrong.</p>
  </div>
  <div>
  <p class="muted"><b>${meta.players.toLocaleString()}</b> players · <b>${meta.matches.toLocaleString()}</b> matches · <b>${meta.appearances.toLocaleString()}</b> appearances · State League 1 &amp; 2, the NPL and SAASL, all grades, ${meta.season}.</p>
  <p class="muted">Try: “top 10 scorers in SL1 Seniors”, “which U18s have senior minutes?”, “best goals per 90 over 600 minutes”, “compare the top two goalkeepers by clean sheet rate”.</p>
  </div>
</div>

```js
// The transcript is a plain array so the input box never gets rebuilt underneath the
// user; `version` is the only reactive value, and bumping it re-runs the render cell.
const log = [];
const version = Mutable(0);
const bump = () => (version.value = version.value + 1);
```

```js
const EXAMPLES = [
  "Top 10 goalscorers in SL1 Seniors",
  "Which U18 players have senior minutes?",
  "Best non-penalty goals per 90 over 600 minutes",
  "Which teams concede the fewest goals per match?",
];

const box = html`<textarea class="chat-input" rows="1" placeholder="Ask about players, teams or form…"></textarea>`;
const sendBtn = html`<button class="mbtn" type="button">Ask</button>`;
const cancelBtn = html`<button class="mbtn" type="button" hidden>Cancel</button>`;

const autoresize = () => {
  box.style.height = "auto";
  box.style.height = `${Math.min(box.scrollHeight, 200)}px`;
};
box.addEventListener("input", autoresize);

async function send(text) {
  const question = String(text ?? "").trim();
  if (!question || sendBtn.disabled) return;
  box.value = "";
  autoresize();
  box.disabled = true;
  sendBtn.disabled = true;

  const controller = new AbortController();
  cancelBtn.hidden = false;
  cancelBtn.onclick = () => controller.abort();

  const turn = {question, steps: [], pending: "Thinking…"};
  log.push(turn);
  bump();

  try {
    // Only prior questions and answers go back as history — the intermediate SQL and
    // row dumps would balloon the prompt for very little benefit on a follow-up.
    const history = log.slice(0, -1).filter((t) => t.answer).flatMap((t) => [
      {role: "user", content: t.question},
      {role: "assistant", content: t.answer},
    ]).slice(-6);

    const {answer, steps, usage} = await ask({
      question, history, system, model: modelSel.value, query, endpoint: ENDPOINT, signal: controller.signal,
      onStep: (s) => {
        turn.pending = s.phase === "running" ? `Running query ${s.attempt}…`
          : s.phase === "failed" ? `Query ${s.attempt} failed, retrying…`
          : s.phase === "rejected" ? `Query ${s.attempt} rejected, retrying…`
          : `Thinking…`;
        bump();
      },
    });
    Object.assign(turn, {answer, steps, usage, pending: null});
  } catch (e) {
    Object.assign(turn, {error: e.name === "AbortError" ? "Cancelled." : String(e.message ?? e), pending: null});
  } finally {
    box.disabled = false;
    sendBtn.disabled = false;
    cancelBtn.hidden = true;
    box.focus();
    bump();
  }
}

sendBtn.onclick = () => send(box.value);
box.onkeydown = (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(box.value); }
};
```

```js
// ── rendering ────────────────────────────────────────────────────────────────
// Numbers the model invents (total_goals, avg_minutes) have no labels.json entry, so
// fall back to a sensible numeric format rather than String(42).
function cellFormats(cols) {
  const base = formats(cols);
  for (const c of cols) {
    if (labels[c]) continue;
    base[c] = (v) => v == null ? "–"
      : typeof v === "number" ? (Number.isInteger(v) ? v.toLocaleString() : v.toFixed(2))
      : String(v);
  }
  return base;
}

function resultTable(step) {
  if (!step.rows?.length) return html`<p class="muted">No rows matched.</p>`;
  // player_id / team_id are requested so rows can be linked, but they're hashes — keep
  // them out of the visible table.
  const cols = step.columns.filter((c) => c !== "player_id" && c !== "team_id");
  const f = cellFormats(cols);
  if (cols.includes("player_name") && step.columns.includes("player_id")) {
    f.player_name = (v, row) => html`<a href="./player?id=${row.player_id}&team=${row.team_id ?? ""}">${v}</a>`;
  }
  if (cols.includes("club")) f.club = (v) => clubCell(v, 16);
  if (cols.includes("league")) f.league = shortLeagueOnly;
  return dataTable(step.rows, {
    columns: cols, header: iconHeaders(cols), format: f,
    width: {player_name: 170, club: 150, league: 150},
    pageSize: 12,
    columnVisibility: cols.length > 6,
  });
}

function stepEl(step, i) {
  const wrap = html`<div class="chat-step"></div>`;
  if (step.error) {
    wrap.append(html`<p class="chat-err">Query ${i + 1}: ${step.error}</p>`);
  } else {
    wrap.append(resultTable(step));
    if (step.truncated) wrap.append(html`<p class="muted">Showing the first 500 rows.</p>`);
  }
  wrap.append(html`<details class="chat-sql"><summary>${step.note || `SQL for query ${i + 1}`}</summary><pre><code>${step.sql}</code></pre></details>`);
  return wrap;
}

function turnEl(turn) {
  const wrap = html`<div class="chat-turn"></div>`;
  wrap.append(html`<div class="chat-q">${turn.question}</div>`);
  if (turn.answer) {
    const a = html`<div class="chat-a"></div>`;
    a.append(renderMarkdown(turn.answer));
    wrap.append(a);
  }
  if (turn.error) wrap.append(html`<p class="chat-err">${turn.error}</p>`);
  (turn.steps ?? []).forEach((s, i) => wrap.append(stepEl(s, i)));
  if (turn.pending) wrap.append(html`<p class="chat-pending">${turn.pending}</p>`);
  const u = turn.usage;
  if (u && (u.input_tokens || u.output_tokens)) {
    wrap.append(html`<p class="chat-usage">${u.input_tokens.toLocaleString()} in · ${u.output_tokens.toLocaleString()} out tokens</p>`);
  }
  return wrap;
}
```

<div class="card">

```js
{
  version; // re-render whenever a turn changes
  // Capture BEFORE appending new content — after appending, the page is always
  // taller, so checking "near bottom" post-render would almost always read false.
  const nearBottom = document.documentElement.scrollHeight - window.scrollY - window.innerHeight < 150;
  const out = html`<div class="chat-log"></div>`;
  if (!log.length) {
    const chips = html`<div class="chat-chips"></div>`;
    for (const q of EXAMPLES) {
      const c = html`<button class="chat-chip" type="button">${q}</button>`;
      c.onclick = () => send(q);
      chips.append(c);
    }
    out.append(html`<p class="muted">Ask a question in plain English. Every answer shows the SQL it came from, so you can check it.</p>`, chips);
  }
  for (const t of log) out.append(turnEl(t));
  display(out);
  if (nearBottom && log.length) {
    requestAnimationFrame(() => window.scrollTo({top: document.documentElement.scrollHeight, behavior: "smooth"}));
  }
}
```

```js
display(html`<div class="chat-composer">${box}${sendBtn}${cancelBtn}</div>`);
box.focus();
```

</div>

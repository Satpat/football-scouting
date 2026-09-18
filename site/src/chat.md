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
  <p class="muted"><b>${meta.players.toLocaleString()}</b> players · <b>${meta.matches.toLocaleString()}</b> matches · <b>${meta.appearances.toLocaleString()}</b> appearances · State League 1 &amp; 2, all grades, ${meta.season}.</p>
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

const box = html`<textarea class="chat-input" rows="2" placeholder="Ask about players, teams or form…"></textarea>`;
const sendBtn = html`<button class="mbtn" type="button">Ask</button>`;

async function send(text) {
  const question = String(text ?? "").trim();
  if (!question || sendBtn.disabled) return;
  box.value = "";
  sendBtn.disabled = true;

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
      question, history, system, model: modelSel.value, query, endpoint: ENDPOINT,
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
    Object.assign(turn, {error: String(e.message ?? e), pending: null});
  } finally {
    sendBtn.disabled = false;
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
    f.player_name = (v, i) => html`<a href="./player?id=${step.rows[i].player_id}&team=${step.rows[i].team_id ?? ""}">${v}</a>`;
  }
  if (cols.includes("club")) f.club = (v) => clubCell(v, 16);
  if (cols.includes("league")) f.league = shortLeagueOnly;
  return Inputs.table(step.rows, {
    columns: cols, header: iconHeaders(cols), format: f,
    // +0.5 because Inputs.table sizes the scroller in rows and an exact count leaves the
    // last row half-clipped under the header; the same trick as its own 11.5 default.
    rows: Math.min(step.rows.length + 0.5, 12.5), width: {player_name: 170, club: 150, league: 150},
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
  return wrap;
}
```

<div class="card">

```js
{
  version; // re-render whenever a turn changes
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
}
```

```js
display(html`<div class="chat-composer">${box}${sendBtn}</div>`);
```

</div>

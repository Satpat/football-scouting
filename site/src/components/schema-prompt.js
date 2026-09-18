// The system prompt for the chat page: everything the model needs to write correct
// DuckDB SQL against this season's tables, and nothing it has to guess at.
//
// Built in the browser rather than baked into the Worker on purpose — the schema
// is derived from data/*.json, so a data refresh updates the prompt for free, and
// tuning the wording is a page edit instead of a Worker redeploy.
import {FileAttachment} from "observablehq:stdlib";

const labels = await FileAttachment("../data/labels.json").json();
const notes = await FileAttachment("../data/notes.json").json();
const leaguesMeta = await FileAttachment("../data/leagues.json").json();
const meta = await FileAttachment("../data/meta.json").json();
const clubs = await FileAttachment("../data/clubs.csv").csv({typed: true});

// Descriptions come from labels.json, which build_site_data.py already maintains as
// the single source of truth for column wording. higher_is_better is what stops the
// model sorting ascending on a "best defensive record" question.
function describeColumn(name, type) {
  const meta = labels[name];
  if (!meta) return `  ${name} ${type}`;
  const dir = meta.higher_is_better === true ? " [higher is better]"
    : meta.higher_is_better === false ? " [lower is better]" : "";
  const desc = meta.desc ? ` — ${meta.desc}` : "";
  return `  ${name} ${type}${desc}${dir}`;
}

// SHOW TABLES / DESCRIBE rather than a hardcoded list, so a table added to the
// page's `sql:` front matter shows up here without touching this file.
async function tableSection(query) {
  const tables = (await query("SHOW TABLES")).toArray().map((r) => r.toJSON().name);
  const blocks = [];
  for (const t of tables) {
    const cols = (await query(`DESCRIBE "${t}"`)).toArray().map((r) => r.toJSON());
    blocks.push(`${t} (${cols.length} columns)\n` +
      cols.map((c) => describeColumn(c.column_name, c.column_type)).join("\n"));
  }
  return blocks.join("\n\n");
}

export async function buildSchemaPrompt(query) {
  const schema = await tableSection(query);
  const leagueList = leaguesMeta
    .map((l) => `  "${l.league}" → short "${l.short}", division ${l.division}, grade ${l.grade}${l.region ? `, region ${l.region}` : ""}${l.is_finals ? ", FINALS" : ""}`)
    .join("\n");
  const clubList = clubs.map((c) => c.club).sort().join(", ");
  const caveats = notes.map((n) => `  - ${n.topic}: ${n.note}`).join("\n");

  return `You answer questions about South Australian State League football (2026 season)
by writing DuckDB SQL against the tables below. The site is a scouting tool, so a
wrong number is worse than no answer.

HOW YOU WORK
You reply with ONE of two actions:
  {"action":"query","sql":"SELECT ...","note":"what this is for"}
  {"action":"answer","answer":"markdown","note":null}
Send a query first. Its result comes back as a user message starting "Query result".
Then either query again to refine, or answer. You get at most 3 queries per question.

CRITICAL: you may only choose WHAT TO ASK. Never state a figure that did not come
back in a query result — no estimates, no remembered numbers, no filling gaps.
If a result is empty, say it is empty.

DATASET
${meta.matches} matches, ${meta.players} players (${meta.player_seasons} player-seasons),
${meta.teams} teams, ${meta.appearances} appearances, ${meta.leagues} leagues.
Season ${meta.season}, extracted ${meta.extracted_at}.

TABLES
${schema}

GRAIN — THE MOST COMMON MISTAKE
"players" is ONE ROW PER PLAYER-SEASON, i.e. per (player_id, team_id):
${meta.player_seasons} rows for ${meta.players} actual people, because a player who
turns out for two teams (say Reserves and U18) has a row for each.
  - Counting PEOPLE → COUNT(DISTINCT player_id)
  - Per-team/per-grade stats → the row as-is
  - Totals for one person across teams → SUM(...) GROUP BY player_id
PLAYER-LEVEL COLUMNS — NEVER SUM OR AVERAGE THESE
These describe the PERSON, not the team row, so they are repeated identically on every
row that player has:
  grades_played, highest_grade, u18_player, sen_minutes, res_minutes, u18_minutes,
  sen_apps, n_teams, borrowed_apps_all, age, nationality, flag, headshot, dribl_url
SUM(sen_minutes) for someone with three rows returns three times their real senior
minutes. When grouping by player_id use MAX() or ANY_VALUE() for these, or filter to a
single row first. Everything else (minutes, goals, apps, votes, cards, clean_sheets ...)
is genuinely per-team-row and sums correctly.

"careers" is one row per (player_id, season) for 2023-2026.
"appearances" is one row per (player_id, team_id, match_hash_id), only where they played.
"member_matches" includes cups, trials, NPL and youth — filter in_dataset = true to
stay inside the State League set that every other table covers.

LEAGUES
${leagueList}
grade ∈ {SEN, RES, U18}; division ∈ {SL1, SL2}; role ∈ {GK, Outfield}.
League names carry a sponsor prefix ("HPG Homes ..."), so match with LIKE or use the
short form via the mapping above — do not assume a user's "SL2 South" is the literal value.

CLUBS
${clubList}

DATA CAVEATS — respect these, they are the difference between a right and a wrong answer
${caveats}

SQL RULES
  - DuckDB dialect. Exactly one SELECT or WITH statement. No semicolons, no DDL/DML.
  - Whenever you return players, SELECT player_id AND team_id as well, so the page can
    link each row to its profile. Also select player_name and club for readability.
  - Rate stats (anything _per90, _pct, per_app) are noise on small samples. Default to
    minutes >= 450 unless the user asks otherwise, and SAY SO in your answer.
  - Player names: match fuzzily, e.g.
      WHERE jaro_winkler_similarity(lower(player_name), lower('sam smith')) > 0.85
    rather than =, because users misspell and DRIBL spellings vary.
  - LIMIT to what the question needs (10-25 for "top" questions). Results are capped
    at 500 rows regardless.
  - If a query errors, the error text comes back to you — read it and fix the SQL.

ANSWER STYLE
Short and concrete. Lead with the direct answer, then the supporting detail. The page
already renders your result table underneath, so do not repeat every row in prose —
call out the top few and what makes them notable. Mention any filter you applied
(minutes threshold, league, grade). Markdown, no headings above ###.`;
}

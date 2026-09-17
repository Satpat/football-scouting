---
title: Player profile
toc: false
sql:
  appearances: ./data/appearances.parquet
  member_matches: ./data/member_matches.parquet
---

```js
import {label, short, describe, fmt, fmtDate, toDate, iconHeaders, formats, crest, clubCell, clubInfo, percentile, shortLeague, shortLeagueOnly, leagueGrade, isNumericCol, GRADE_NAME} from "./components/labels.js";
import {radar} from "./components/radar.js";
import {icon, iconHeader, gemMark} from "./components/icons.js";
const players = await FileAttachment("./data/players.csv").csv({typed: true});
const careers = await FileAttachment("./data/careers.csv").csv({typed: true});
const q = new URLSearchParams(location.search);
const pid = q.get("id");
const tidParam = q.get("team");
const rowsFor = players.filter((d) => d.player_id === pid);
```

```js
// No player chosen: search
const searched = pid ? [] : view(Inputs.search(players, {placeholder: "Search a player, club or team…", columns: ["player_name", "club", "team"]}));
```

```js
if (!pid) display(html`<h1>Player profile</h1><p class="muted">Pick a player to open their profile.</p>`);
if (!pid) display(Inputs.table(searched, {columns: ["player_name", "club", "team", "league", "age", "apps", "goals", "minutes"], header: iconHeaders(["player_name", "club", "team", "league", "age", "apps", "goals", "minutes"]),
  format: {...formats(["age", "apps", "goals", "minutes"]), player_name: (v, i) => html`<a href="./player?id=${searched[i].player_id}&team=${searched[i].team_id}">${v}</a>`}, rows: 20, select: false}));
if (pid && !rowsFor.length) display(html`<h1>Player not found</h1><p class="muted">No player with id <code>${pid}</code>. <a href="./player">Search instead</a>.</p>`);
```

```js
const teamRows = (rowsFor.some((r) => r.apps > 0) ? rowsFor.filter((r) => r.apps > 0) : rowsFor).slice().sort((a, b) => b.minutes - a.minutes);
const defaultTeam = teamRows.find((r) => r.team_id === tidParam)?.team_id ?? teamRows[0]?.team_id;
const teamSel = view(Inputs.radio(new Map(teamRows.map((r) => [`${r.club} · ${GRADE_NAME[r.grade]} · ${shortLeague(r.league)} — ${r.apps} apps`, r.team_id])), {value: defaultTeam, label: rowsFor.length ? "Team" : ""}));
```

```js
const p = rowsFor.find((r) => r.team_id === teamSel) ?? teamRows[0];
```

```js
const club = p ? clubInfo(p.club) : null;
const accent = p?.club_accent || "#1e5631";
const primary = p?.club_color || "#ffffff";
```

<div>${p ? html`<div class="profile-head" style="background: linear-gradient(135deg, ${accent}, ${accent}cc);">
  ${p.headshot ? html`<img class="headshot" src="${p.headshot}" alt="${p.player_name}" referrerpolicy="no-referrer">` : ""}
  ${(() => { const c = crest(p.club, 56); c.loading = "eager"; return c; })()}
  <div>
    <h1>${p.player_name}</h1>
    <div class="sub">${p.club} · ${p.team}</div>
    <div class="badges">
      <span class="badge grade">${GRADE_NAME[p.grade]} · ${p.division}</span>
      ${p.hidden_gem ? gemMark() : ""}
      ${p.u18_player ? html`<span class="badge grade">U18 player</span>` : ""}
      ${p.role === "GK" ? html`<span class="badge grade">Goalkeeper</span>` : ""}
      ${p.minutes_est_apps > 0 ? html`<span class="badge est" title="${describe("minutes_est_apps")}">${p.minutes_est_apps} apps est. minutes</span>` : ""}
    </div>
  </div>
  <div class="actions">
    <a href="${p.dribl_url}" target="_blank" rel="noopener">View on DRIBL ↗</a>
    <a href="./?player=${p.player_id}&team=${p.team_id}">Open in Explorer</a>
  </div>
</div>` : ""}</div>

```js
const fact = (labelText, value) => html`<div class="fact"><div class="fv">${value ?? "–"}</div><div class="fl">${labelText}</div></div>`;
const tile = (col, value, extra) => html`<div class="tile"><div class="tv">${extra ?? ""}${fmt(col, value)}</div><div class="tl">${label(col)}</div></div>`;
const cardGlyph = (kind) => html`<span class="card-glyph ${kind}"></span>`;
const seasonCols = ["apps", "starts", "minutes", "goals", "goals_open_play", "goals_penalty", "votes", "yellow_cards", "red_cards", "clean_sheets", "goals_go_ahead", "goals_winner", "captain_apps", "borrowed_apps"];
const rateCols = ["npg_per90", "goals_per90", "votes_per_app", "team_goal_share_pct", "minutes_share_pct", "start_rate_pct", "gd_on_pitch_vs_team", "ga_on_pitch_per90", "clean_sheet_pct", "yellows_per90", "ppg_when_playing", "ppg_start_diff"];
const seasonTable = (rows) => html`<table class="stats"><thead><tr><th>Club</th><th>Grade</th><th>League</th>${seasonCols.map((c) => html`<th>${iconHeader(c, `${label(c)} — ${describe(c)}`)}</th>`)}</tr></thead>
  <tbody>${rows.map((r) => html`<tr class="${r.team_id === p?.team_id ? "sel" : ""}"><td>${clubCell(r.club, 16)}</td><td>${GRADE_NAME[r.grade]}</td><td>${shortLeagueOnly(r.league)}</td>${seasonCols.map((c) => html`<td>${fmt(c, r[c])}</td>`)}</tr>`)}</tbody></table>`;
```

<div class="grid grid-cols-3" style="grid-auto-rows: auto;">
  ${p ? html`<div class="card">
    <h2>Profile</h2>
    <div class="facts2">
      ${fact("Age", p.age)}
      ${fact("Nationality", p.flag ? html`<span class="flag" title="${p.nationality}">${p.flag}</span> ${p.nationality}` : p.nationality)}
      ${fact("Shirt", p.jersey)}
      ${fact("Role", p.role)}
      ${fact("Grade", GRADE_NAME[p.grade])}
      ${fact("League", shortLeague(p.league))}
      ${fact("Grades played", p.grades_played)}
      ${fact("Highest grade", GRADE_NAME[p.highest_grade])}
      ${fact("Senior minutes", fmt("sen_minutes", p.sen_minutes))}
      ${fact("Team finished", p.team_ladder_pos ? `${p.team_ladder_pos} of ${p.ladder_teams}` : "–")}
      ${fact("Team points per game", fmt("team_ppg", p.team_ppg))}
      ${fact("Teams this season", p.n_teams)}
    </div>
  </div>` : ""}
  ${p ? html`<div class="card grid-colspan-2">
    <h2><span class="h2-crest">${crest(p.club, 22)}</span> ${shortLeague(p.league)} 2026 <span class="muted">— ${p.club ?? ""}</span></h2>
    <div class="tiles2">
      ${tile("apps", p.apps)}${tile("starts", p.starts)}${tile("minutes", p.minutes)}${tile("goals", p.goals)}
      ${tile("goals_open_play", p.goals_open_play)}${tile("goals_penalty", p.goals_penalty)}${tile("votes", p.votes)}
      ${tile("yellow_cards", p.yellow_cards, cardGlyph("y"))}${tile("red_cards", p.red_cards, cardGlyph("r"))}
      ${p.role === "GK" ? tile("clean_sheets", p.clean_sheets) : tile("goals_go_ahead", p.goals_go_ahead)}
      ${tile("goals_winner", p.goals_winner)}${p.captain_apps > 0 ? tile("captain_apps", p.captain_apps) : ""}
    </div>
    <div class="tiles2 rates">
      ${tile("npg_per90", p.npg_per90)}${tile("votes_per_app", p.votes_per_app)}${tile("team_goal_share_pct", p.team_goal_share_pct)}
      ${tile("minutes_share_pct", p.minutes_share_pct)}${tile("gd_on_pitch_vs_team", p.gd_on_pitch_vs_team)}
      ${p.role === "GK" ? tile("ga_on_pitch_per90", p.ga_on_pitch_per90) : tile("ppg_start_diff", p.ppg_start_diff)}
    </div>
    ${p.minutes_est_apps > 0 ? html`<p class="muted">${p.minutes_est_apps} of ${p.apps} appearances have estimated minutes (subs not recorded).</p>` : ""}
    ${rowsFor.filter((r) => r.apps > 0).length > 1 ? html`<details><summary class="muted">All teams this season</summary>${seasonTable(rowsFor.filter((r) => r.apps > 0).sort((a, b) => b.minutes - a.minutes))}</details>` : ""}
  </div>` : ""}
</div>

```js
const TRAITS = [
  ["npg_per90", false], ["votes_per_app", false], ["minutes_share_pct", false], ["team_goal_share_pct", false],
  ["gd_on_pitch_vs_team", false], ["yellows_per90", true],
];
const GK_TRAITS = [["ga_on_pitch_per90", true], ["clean_sheet_pct", false], ["votes_per_app", false], ["minutes_share_pct", false], ["gd_on_pitch_vs_team", false], ["yellows_per90", true]];
const peers = p ? players.filter((d) => d.league === p.league && d.role === p.role && d.minutes >= 450) : [];
const traits = p ? (p.role === "GK" ? GK_TRAITS : TRAITS).map(([col, invert]) => ({col, invert, value: p[col], pct: percentile(peers.map((d) => d[col]), p[col], invert)})) : [];
```

<div class="grid grid-cols-3" style="grid-auto-rows: auto;">
  ${p ? html`<div class="card">
    <h2>Player traits</h2>
    <p class="muted" style="margin-top:-0.5rem">Percentile vs ${peers.length} ${p.role === "GK" ? "goalkeepers" : "outfield players"} in this league with 450+ minutes. Cards and goals conceded are inverted.</p>
    <div class="radar-wrap">${resize((width) => radar(traits.map((t) => ({...t, label: label(t.col).replace(" per 90", "/90").replace("Best-on-ground ", "").replace("On-pitch goal difference vs team", "GD vs team").replace("Share of team ", "Team ")})), {size: Math.min(width, 380), accent, levels: 3}))}</div>
  </div>` : ""}
  ${p ? html`<div class="card grid-colspan-2">
    <h2>Season so far</h2>
    ${seasonRows.length ? resize((width) => {
      let g = 0, m = 0;
      const cum = seasonRows.map((r, i) => ({i: i + 1, date: r.date, goals: (g += r.goals ?? 0), minutes: (m += r.minutes ?? 0), opp: r.side === "home" ? r.away_team : r.home_team, result: r.result, comp: r.league}));
      return Plot.plot({width, height: 240, marginLeft: 40, x: {label: "Appearance (all competitions) →"}, y: {label: "↑ Cumulative goals", grid: true},
        marks: [Plot.lineY(cum, {x: "i", y: "goals", stroke: accent, curve: "step-after", strokeWidth: 2}),
                Plot.dot(cum, {x: "i", y: "goals", fill: (d) => d.result === "W" ? "#2ca02c" : d.result === "D" ? "#999" : "#d62728", r: 4,
                  channels: {Date: (d) => fmtDate(d.date), Opponent: "opp", Result: "result", Competition: "comp", Minutes: "minutes"}, tip: {format: {x: false, y: true}}})]});
    }) : html`<p class="muted">No matches recorded.</p>`}
    <p class="muted">Dot colour shows the match result.</p>
  </div>` : ""}
</div>

```js
const allMatches = p
  ? (await sql`SELECT * FROM member_matches WHERE player_id = ${p.player_id} ORDER BY date`).toArray().map((r) => r.toJSON())
  : [];
const seasonRows = allMatches.filter((r) => r.did_play);
const compChoices = new Map([["All competitions", "All competitions"], ...[...new Set(allMatches.map((r) => r.league))].map((l) => [shortLeague(l), l])]);
```

```js
const compInput = Inputs.select(compChoices, {value: "All competitions", label: ""});
const compSel = Generators.input(compInput);
```

```js
const matchRows = allMatches.filter((r) => r.did_play).filter((r) => compSel === "All competitions" || r.league === compSel)
  .sort((a, b) => d3.descending(toDate(a.date), toDate(b.date)))
  .map((r) => ({...r, opponent: r.side === "home" ? r.away_team : r.side === "away" ? r.home_team : `${r.home_team} v ${r.away_team}`,
    opponent_club: r.side === "home" ? r.away_club : r.side === "away" ? r.home_club : null,
    own: r.side === "home" ? r.home_score : r.away_score, opp: r.side === "home" ? r.away_score : r.home_score,
    ha: r.side === "home" ? "H" : r.side === "away" ? "A" : "–", cup: !/State League/.test(r.league)}));
const PAGE = 10;
```

```js
const page = Mutable(0);
const setPage = (n) => (page.value = Math.max(0, Math.min(n, Math.ceil(matchRows.length / PAGE) - 1)));
```

```js
const pageRows = matchRows.slice(page * PAGE, page * PAGE + PAGE);
const shortDate = (v) => { const d = toDate(v); return d ? d3.timeFormat("%-d %b")(d) : "–"; };
const voteBadge = (v) => v > 0 ? html`<span class="vote v${v}">${v}</span>` : html`<span class="muted">–</span>`;
const matchList = html`<div class="mlist">
  <div class="mrow mhead">
    <span></span><span>Opponent</span><span>Grade</span><span>League</span><span></span>
    ${["minutes", "goals", "votes", "yellow_cards", "red_cards"].map((c) => html`<span>${iconHeader(c, label(c))}</span>`)}
  </div>
  ${pageRows.map((r) => html`<div class="mrow">
    <span class="mdate">${shortDate(r.date)} <span class="ha-pill">${r.ha}</span></span>
    <span class="mopp">${crest(r.opponent_club, 20)} ${r.opponent_club ?? r.opponent}</span>
    <span>${leagueGrade(r.league) ?? "–"}</span>
    <span>${shortLeagueOnly(r.league)}</span>
    <span class="mres">${r.result ? html`<span class="pill ${r.result}">${r.result}</span>` : ""} <span class="score"><b class="${r.own >= r.opp ? "hi" : ""}">${r.own ?? "–"}</b> - <b class="${r.opp >= r.own ? "hi" : ""}">${r.opp ?? "–"}</b></span>${r.borrowed_side ? html`<span class="brw-slot" title="Borrowed for this match">${icon("handshake", {size: 12})}</span>` : ""}</span>
    <span>${fmt("minutes", r.minutes)}</span>
    <span>${r.goals || "0"}</span>
    <span>${voteBadge(r.votes ?? 0)}</span>
    <span>${r.yellow_cards ? html`${cardGlyph("y")} ${r.yellow_cards}` : "0"}</span>
    <span>${r.red_cards ? html`${cardGlyph("r")} ${r.red_cards}` : "0"}</span>
  </div>`)}
  <div class="mnav">
    <button class="mbtn" disabled=${page === 0 ? true : null} onclick=${() => setPage(page - 1)}>‹ Previous</button>
    <span class="muted">${matchRows.length ? `${page * PAGE + 1}–${Math.min((page + 1) * PAGE, matchRows.length)} of ${matchRows.length}` : "No matches"}</span>
    <button class="mbtn" disabled=${(page + 1) * PAGE >= matchRows.length ? true : null} onclick=${() => setPage(page + 1)}>Next ›</button>
  </div>
</div>`;
```

```js
const careerRows = p ? careers.filter((c) => c.player_id === p.player_id).sort((a, b) => d3.descending(a.season, b.season)) : [];
const careerStatCols = ["played", "started", "minutes", "goals", "votes", "yellow_cards", "red_cards", "clean_sheets", "was_goalkeeper"];
const leaguesOf = (c) => String(c.leagues ?? "").split("; ").filter(Boolean);
const careerTable = html`<table class="stats career-table"><thead><tr><th>Season</th><th>Club</th>${careerStatCols.map((c) => html`<th>${isNumericCol(c) ? iconHeader(c, label(c)) : label(c)}</th>`)}</tr></thead>
  <tbody>${careerRows.flatMap((c) => [
    html`<tr class="season-row"><td>${c.season}</td><td>${clubCell(String(c.clubs).split("; ")[0], 18)}</td>${careerStatCols.map((col) => html`<td>${fmt(col, c[col])}</td>`)}</tr>`,
    ...leaguesOf(c).map((l) => html`<tr class="league-row"><td></td><td class="league-name">${GRADE_NAME[leagueGrade(l)] ?? "–"} · ${shortLeagueOnly(l)}</td><td colspan="${careerStatCols.length}"></td></tr>`),
  ])}</tbody></table>`;
```

<div class="grid grid-cols-2" style="grid-auto-rows: auto;">
  ${p ? html`<div class="card">
    <div class="mtitle"><h2>Match stats</h2>${compInput}</div>
    ${matchList}
    <p class="muted">Includes cups and trials. Minutes are DRIBL's own; votes are 3-2-1 best-on-ground.</p>
  </div>` : ""}
  ${p ? html`<div class="card">
    <h2>Career <span class="muted">— seasons recorded in DRIBL</span></h2>
    <div class="table-scroll">${careerTable}</div>
    <p class="muted">Leagues/grades played that season are listed under it.</p>
  </div>` : ""}
</div>

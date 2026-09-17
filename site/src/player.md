---
title: Player profile
toc: false
sql:
  appearances: ./data/appearances.parquet
  member_matches: ./data/member_matches.parquet
---

```js
import {label, short, describe, fmt, fmtDate, headers, formats, crest, clubCell, clubInfo, percentile, GRADE_NAME} from "./components/labels.js";
import {radar} from "./components/radar.js";
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
if (!pid) display(Inputs.table(searched, {columns: ["player_name", "club", "team", "league", "age", "apps", "goals", "minutes"], header: headers(["player_name", "club", "team", "league", "age", "apps", "goals", "minutes"]),
  format: {...formats(["age", "apps", "goals", "minutes"]), player_name: (v, i) => html`<a href="./player?id=${searched[i].player_id}&team=${searched[i].team_id}">${v}</a>`}, rows: 20, select: false}));
if (pid && !rowsFor.length) display(html`<h1>Player not found</h1><p class="muted">No player with id <code>${pid}</code>. <a href="./player">Search instead</a>.</p>`);
```

```js
const teamRows = (rowsFor.some((r) => r.apps > 0) ? rowsFor.filter((r) => r.apps > 0) : rowsFor).slice().sort((a, b) => b.minutes - a.minutes);
const defaultTeam = teamRows.find((r) => r.team_id === tidParam)?.team_id ?? teamRows[0]?.team_id;
const teamSel = view(Inputs.radio(new Map(teamRows.map((r) => [`${r.team} (${GRADE_NAME[r.grade]}) — ${r.apps} apps`, r.team_id])), {value: defaultTeam, label: rowsFor.length ? "Team" : ""}));
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
      ${p.hidden_gem ? html`<span class="badge gem">hidden gem</span>` : ""}
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
const kv = (rows) => html`<table class="kv"><tbody>${rows.map(([k, v]) => html`<tr><th>${k}</th><td>${v ?? "–"}</td></tr>`)}</tbody></table>`;
const seasonCols = ["apps", "starts", "minutes", "goals", "goals_open_play", "goals_penalty", "votes", "yellow_cards", "red_cards", "clean_sheets", "goals_go_ahead", "goals_winner", "captain_apps", "borrowed_apps"];
const seasonTable = (rows) => html`<table class="stats"><thead><tr><th>Team</th><th>League</th>${seasonCols.map((c) => html`<th title="${describe(c)}">${short(c)}</th>`)}</tr></thead>
  <tbody>${rows.map((r) => html`<tr class="${r.team_id === p?.team_id ? "sel" : ""}"><td>${r.team}</td><td>${r.league.replace("HPG Homes State League ", "SL")}</td>${seasonCols.map((c) => html`<td>${fmt(c, r[c])}</td>`)}</tr>`)}</tbody></table>`;
const rateCols = ["npg_per90", "goals_per90", "votes_per_app", "team_goal_share_pct", "minutes_share_pct", "start_rate_pct", "gd_on_pitch_vs_team", "ga_on_pitch_per90", "clean_sheet_pct", "yellows_per90", "ppg_when_playing", "ppg_start_diff"];
```

<div class="grid grid-cols-3" style="grid-auto-rows: auto;">
  <div class="card">
    <h2>Profile</h2>
    ${p ? kv([
      ["Age", p.age], ["Nationality", p.nationality], ["Shirt", p.jersey], ["Role", p.role],
      ["Grade", GRADE_NAME[p.grade]], ["League", p.league], ["Teams this season", p.n_teams],
      ["Grades played", p.grades_played], ["Highest grade", GRADE_NAME[p.highest_grade]],
      ["Senior minutes", fmt("sen_minutes", p.sen_minutes)],
      ["Team ladder position", p.team_ladder_pos ? `${p.team_ladder_pos} / ${p.ladder_teams}` : "–"],
      ["Team points per game", fmt("team_ppg", p.team_ppg)],
    ]) : ""}
  </div>
  <div class="card grid-colspan-2">
    <h2>Season 2026 by team</h2>
    ${p ? seasonTable(rowsFor.slice().sort((a, b) => b.minutes - a.minutes)) : ""}
    <h3 style="margin-top:1rem">Rates — ${p?.team ?? ""}</h3>
    ${p ? html`<table class="stats"><thead><tr>${rateCols.map((c) => html`<th title="${describe(c)}">${short(c)}</th>`)}</tr></thead><tbody><tr>${rateCols.map((c) => html`<td>${fmt(c, p[c])}</td>`)}</tr></tbody></table>` : ""}
    <p class="muted" style="margin-top:0.5rem">Hover a column header for its definition. ${p?.minutes_est_apps > 0 ? `${p.minutes_est_apps} of ${p.apps} appearances have estimated minutes (subs not recorded).` : ""}</p>
  </div>
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
  <div class="card">
    <h2>Player traits <span class="muted">— percentile vs ${peers.length} ${p?.role === "GK" ? "goalkeepers" : "outfield players"} in this league (450+ min)</span></h2>
    ${p ? html`<div class="radar-wrap">${radar(traits.map((t) => ({...t, label: short(t.col)})), {size: 340, accent})}
      <table class="radar-legend"><tbody>${traits.map((t) => html`<tr><th title="${describe(t.col)}">${label(t.col)}</th><td>${fmt(t.col, t.value)}</td><td><b>${t.pct == null ? "–" : t.pct + "%"}</b></td></tr>`)}</tbody></table></div>` : ""}
    <p class="muted">Higher is better on every axis; conceded goals and yellow cards are inverted. DRIBL records no positions, so peers are all ${p?.role === "GK" ? "goalkeepers" : "outfield players"}.</p>
  </div>
  <div class="card grid-colspan-2">
    <h2>Season so far</h2>
    ${p && seasonRows.length ? resize((width) => {
      let g = 0, m = 0;
      const cum = seasonRows.map((r, i) => ({i: i + 1, date: r.date, goals: (g += r.goals ?? 0), minutes: (m += r.minutes ?? 0), opp: r.side === "home" ? r.away_team : r.home_team, result: r.result, comp: r.league}));
      return Plot.plot({width, height: 240, marginLeft: 40, x: {label: "Appearance (all competitions) →"}, y: {label: "↑ Cumulative goals", grid: true},
        marks: [Plot.lineY(cum, {x: "i", y: "goals", stroke: accent, curve: "step-after", strokeWidth: 2}),
                Plot.dot(cum, {x: "i", y: "goals", fill: (d) => d.result === "W" ? "#2ca02c" : d.result === "D" ? "#999" : "#d62728", r: 4,
                  channels: {Date: (d) => fmtDate(d.date), Opponent: "opp", Result: "result", Competition: "comp", Minutes: "minutes"}, tip: {format: {x: false, y: true}}})]});
    }) : html`<p class="muted">No matches recorded.</p>`}
    <p class="muted">Cumulative goals by appearance across every competition; dots coloured by result.</p>
  </div>
</div>

```js
const allMatches = p
  ? (await sql`SELECT * FROM member_matches WHERE player_id = ${p.player_id} ORDER BY date`).toArray().map((r) => r.toJSON())
  : [];
const seasonRows = allMatches.filter((r) => r.did_play);
const compChoices = ["All competitions", ...new Set(allMatches.map((r) => r.league))];
```

```js
const compSel = view(Inputs.select(compChoices, {value: "All competitions", label: "Competition"}));
```

```js
const matchRows = allMatches.filter((r) => compSel === "All competitions" || r.league === compSel).map((r) => ({...r, opponent: r.side === "home" ? r.away_team : r.home_team, opponent_club: r.side === "home" ? r.away_club : r.home_club, ha: r.side === "home" ? "H" : "A"}));
const matchCols = ["date", "league", "full_round", "opponent", "ha", "result", "score", "did_play", "starting", "minutes", "goals", "votes", "yellow_cards", "red_cards", "is_captain", "clean_sheet", "in_dataset"];
const matchHdr = {...headers(matchCols), ha: "H/A", opponent: "Opponent", full_round: "Round"};
const matchFmt = {...formats(matchCols), date: fmtDate,
  opponent: (v, i) => { const s = document.createElement("span"); s.className = "club-cell"; s.append(crest(matchRows[i].opponent_club, 18), document.createTextNode(" " + v)); return s; },
  result: (v) => v ? html`<span class="pill ${v}">${v}</span>` : "", ha: (v) => v};
```

<div class="card">
  <h2>Match stats <span class="muted">— ${matchRows.length} matches${compSel === "All competitions" ? " in all competitions" : ""}</span></h2>
  ${p ? Inputs.table(matchRows, {columns: matchCols, header: matchHdr, format: matchFmt, rows: 30, select: false, width: {opponent: 260, league: 220, full_round: 110}, layout: "auto"}) : ""}
  <p class="muted">All matches DRIBL lists for this player this season, including cups and trial matches. Minutes here are DRIBL's own figures. "In SL dataset" marks the State League fixtures that feed the Explorer's stats.</p>
</div>

```js
const careerRows = p ? careers.filter((c) => c.player_id === p.player_id).sort((a, b) => d3.descending(a.season, b.season)) : [];
const careerCols = ["season", "clubs", "leagues", "played", "started", "minutes", "goals", "votes", "yellow_cards", "red_cards", "clean_sheets", "was_goalkeeper"];
```

<div class="card">
  <h2>Career <span class="muted">— seasons recorded in DRIBL</span></h2>
  ${p ? Inputs.table(careerRows, {columns: careerCols, header: headers(careerCols), format: {...formats(careerCols), clubs: (v, i) => { const s = document.createElement("span"); s.className = "club-cell"; s.append(crest(String(v).split("; ")[0], 18), document.createTextNode(" " + v)); return s; }}, rows: 10, select: false, width: {leagues: 420, clubs: 200}, layout: "auto"}) : ""}
</div>

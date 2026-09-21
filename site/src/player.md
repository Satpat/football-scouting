---
title: Player profile
toc: false
sql:
  appearances: ./data/appearances.parquet
  member_matches: ./data/member_matches.parquet
---

```js
import {label, short, describe, fmt, fmtDate, toDate, crest, clubCell, clubInfo, percentile, shortLeague, shortLeagueOnly, leagueGrade, isGradedLeague, isNumericCol, GRADE_NAME} from "./components/labels.js";
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
// This page is only ever reached by clicking a player, so a bare /player has no one to show.
// It used to answer that with a searchable table of every player-season, which duplicated the
// Explorer; point people at the two pages that link here instead.
if (!pid) display(html`<h1>Player profile</h1><p class="muted">Open a player from the <a href="./">Explorer</a> or the <a href="./shortlist">Player shortlist</a>.</p>`);
if (pid && !rowsFor.length) display(html`<h1>Player not found</h1><p class="muted">No player with id <code>${pid}</code>. Open a player from the <a href="./">Explorer</a> or the <a href="./shortlist">Player shortlist</a>.</p>`);
```

```js
const teamRows = (rowsFor.some((r) => r.apps > 0) ? rowsFor.filter((r) => r.apps > 0) : rowsFor).slice().sort((a, b) => b.minutes - a.minutes);
const defaultTeam = teamRows.find((r) => r.team_id === tidParam)?.team_id ?? teamRows[0]?.team_id;
const teamSel = view(Inputs.radio(new Map(teamRows.map((r) => [`${r.club} · ${GRADE_NAME[r.grade]} · ${shortLeagueOnly(r.league)} — ${r.apps} apps`, r.team_id])), {value: defaultTeam, label: rowsFor.length ? "Team" : ""}));
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
      ${p.emerging_senior ? html`<span class="badge" style="background:#0284c7;color:white;" title="${describe('emerging_senior')}">⚡ Emerging Senior</span>` : ""}
      ${p.undervalued_performer ? html`<span class="badge" style="background:#7c3aed;color:white;" title="${describe('undervalued_performer')}">🎯 Undervalued</span>` : ""}
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
const seasonCols = ["apps", "starts", "minutes", "goals", "votes", "yellow_cards", "red_cards", "clean_sheets"];
const seasonTable = (rows) => html`<table class="stats"><thead><tr><th>Club</th><th>Grade</th><th>League</th>${seasonCols.map((c) => html`<th>${iconHeader(c, `${label(c)} — ${describe(c)}`)}</th>`)}</tr></thead>
  <tbody>${rows.map((r) => html`<tr class="${r.team_id === p?.team_id ? "sel" : ""}"><td>${clubCell(r.club, 16)}</td><td>${GRADE_NAME[r.grade]}</td><td>${shortLeagueOnly(r.league)}</td>${seasonCols.map((c) => html`<td>${fmt(c, r[c])}</td>`)}</tr>`)}</tbody></table>`;
const profileCard = () => p ? html`<div class="card">
  <div class="split split-1-2">
    <div class="col">
    <h2>Profile</h2>
    <div class="facts2">
      ${fact("Age", p.age)}
      ${p.height_cm ? fact("Height", `${p.height_cm} cm`) : ""}
      ${p.position_sofa ? fact("Position", p.position_sofa) : ""}
      ${fact("Nationality", p.flag ? html`<span class="flag" title="${p.nationality}">${p.flag}</span> ${p.nationality}` : p.nationality)}
      ${fact("Shirt", p.jersey)}
      ${fact("Role", p.role)}
      ${fact("Grade", GRADE_NAME[p.grade])}
      ${fact("League", shortLeagueOnly(p.league))}
      ${fact("Grades played", p.grades_played)}
      ${fact("Highest grade", GRADE_NAME[p.highest_grade])}
      ${fact("Senior minutes", fmt("sen_minutes", p.sen_minutes))}
      ${fact("Team finished", p.team_ladder_pos ? `${p.team_ladder_pos} of ${p.ladder_teams}` : "–")}
      ${fact("Team points per game", fmt("team_ppg", p.team_ppg))}
      ${fact("Teams this season", p.n_teams)}
    </div>
    </div>
    <div class="col">
    <h2><span class="h2-crest">${crest(p.club, 22)}</span> ${shortLeague(p.league)} 2026 <span class="muted">— ${p.club ?? ""}</span></h2>
    <div class="tiles2">
      ${tile("apps", p.apps)}${tile("starts", p.starts)}${tile("minutes", p.minutes)}${tile("goals", p.goals)}
      ${p.assists > 0 ? tile("assists", p.assists) : ""}
      ${p.sofascore_rating ? tile("sofascore_rating", p.sofascore_rating) : ""}
      ${p.xg > 0 ? tile("xg", p.xg) : ""}
      ${p.xa > 0 ? tile("xa", p.xa) : ""}
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
    ${(p.sofascore_rating != null || p.passes_total > 0 || p.duels_total > 0) ? html`
    <h3 style="margin-top:1.25rem; margin-bottom: 0.5rem; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--theme-foreground-muted);">Sofascore Advanced Metrics</h3>
    <div class="tiles2">
      ${p.xg_p90 > 0 ? tile("xg_p90", p.xg_p90) : ""}
      ${p.xa_p90 > 0 ? tile("xa_p90", p.xa_p90) : ""}
      ${p.finishing_delta != null && p.xg > 0 ? tile("finishing_delta", p.finishing_delta) : ""}
      ${p.key_passes_p90 > 0 ? tile("key_passes_p90", p.key_passes_p90) : ""}
      ${p.big_chances_created > 0 ? tile("big_chances_created", p.big_chances_created) : ""}
      ${p.passes_p90 > 0 ? tile("passes_p90", p.passes_p90) : ""}
      ${p.pass_acc_pct > 0 ? tile("pass_acc_pct", p.pass_acc_pct) : ""}
      ${p.long_ball_acc_pct > 0 ? tile("long_ball_acc_pct", p.long_ball_acc_pct) : ""}
      ${p.duels_p90 > 0 ? tile("duels_p90", p.duels_p90) : ""}
      ${p.duel_win_pct > 0 ? tile("duel_win_pct", p.duel_win_pct) : ""}
      ${p.aerial_win_pct > 0 ? tile("aerial_win_pct", p.aerial_win_pct) : ""}
      ${p.tackles_p90 > 0 ? tile("tackles_p90", p.tackles_p90) : ""}
      ${p.interceptions_p90 > 0 ? tile("interceptions_p90", p.interceptions_p90) : ""}
      ${p.recoveries_p90 > 0 ? tile("recoveries_p90", p.recoveries_p90) : ""}
      ${p.defensive_actions_p90 > 0 ? tile("defensive_actions_p90", p.defensive_actions_p90) : ""}
      ${p.dribbles_p90 > 0 ? tile("dribbles_p90", p.dribbles_p90) : ""}
      ${p.dribble_success_pct > 0 ? tile("dribble_success_pct", p.dribble_success_pct) : ""}
      ${p.shots_p90 > 0 ? tile("shots_p90", p.shots_p90) : ""}
      ${p.shot_acc_pct > 0 ? tile("shot_acc_pct", p.shot_acc_pct) : ""}
      ${p.xg_per_shot > 0 ? tile("xg_per_shot", p.xg_per_shot) : ""}
      ${p.role === "GK" && p.saves > 0 ? tile("saves", p.saves) : ""}
      ${p.role === "GK" && p.saves_p90 > 0 ? tile("saves_p90", p.saves_p90) : ""}
      ${p.role === "GK" && p.saves_inside_box > 0 ? tile("saves_inside_box", p.saves_inside_box) : ""}
    </div>` : ""}
    ${p.minutes_est_apps > 0 ? html`<p class="muted">${p.minutes_est_apps} of ${p.apps} appearances have estimated minutes (subs not recorded).</p>` : ""}
    ${rowsFor.filter((r) => r.apps > 0).length > 1 ? html`<details><summary class="muted">All teams this season</summary><div class="table-scroll">${seasonTable(rowsFor.filter((r) => r.apps > 0).sort((a, b) => b.minutes - a.minutes))}</div></details>` : ""}
    </div>
  </div>
</div>` : null;
```

```js
const radarMode = Mutable("Standard");
const setRadarMode = (m) => (radarMode.value = m);
```

```js
const TRAITS = [
  ["npg_per90", false], ["votes_per_app", false], ["minutes_share_pct", false], ["team_goal_share_pct", false],
  ["gd_on_pitch_vs_team", false], ["yellows_per90", true],
];
const GK_TRAITS = [["ga_on_pitch_per90", true], ["clean_sheet_pct", false], ["votes_per_app", false], ["minutes_share_pct", false], ["gd_on_pitch_vs_team", false], ["yellows_per90", true]];

const ADV_TRAITS = [
  ["xg_p90", false], ["xa_p90", false], ["key_passes_p90", false],
  ["pass_acc_pct", false], ["duel_win_pct", false], ["defensive_actions_p90", false]
];
const ADV_GK_TRAITS = [
  ["saves_p90", false], ["clean_sheet_pct", false], ["pass_acc_pct", false],
  ["long_ball_acc_pct", false], ["ga_on_pitch_per90", true], ["sofascore_rating", false]
];

const hasSofaTraits = p && (p.duels_total > 0 || p.passes_total > 0 || (p.role === "GK" && p.saves > 0));
const isAdv = hasSofaTraits && radarMode === "Advanced";
const activeList = isAdv ? (p.role === "GK" ? ADV_GK_TRAITS : ADV_TRAITS) : (p.role === "GK" ? GK_TRAITS : TRAITS);
const peers = p ? players.filter((d) => d.league === p.league && d.role === p.role && d.minutes >= 450) : [];
const advPeers = isAdv ? peers.filter((d) => (d.duels_total > 0 || d.saves > 0)) : peers;
const traits = p ? activeList.map(([col, invert]) => ({col, invert, value: p[col], pct: percentile(advPeers.map((d) => d[col]), p[col], invert)})) : [];

const traitsCard = () => p ? html`<div class="card">
  <div style="display:flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
    <h2 style="margin:0;">Player traits</h2>
    ${hasSofaTraits ? html`<div style="display:flex; gap:4px;">
      <button class="mbtn ${radarMode === 'Standard' ? 'active' : ''}" style="padding:3px 10px; font-size:11px;" onclick=${() => setRadarMode("Standard")}>Standard</button>
      <button class="mbtn ${radarMode === 'Advanced' ? 'active' : ''}" style="padding:3px 10px; font-size:11px;" onclick=${() => setRadarMode("Advanced")}>Sofascore Advanced</button>
    </div>` : ""}
  </div>
  <p class="muted" style="margin-top:-0.25rem">Percentile vs ${advPeers.length} ${p.role === "GK" ? "goalkeepers" : "outfield players"} in this league with 450+ minutes${isAdv ? " and Sofascore data" : ""}. Cards and goals conceded are inverted.</p>
  <div class="radar-wrap" style="max-width: 440px; margin: 0 auto;">${resize((width) => radar(traits.map((t) => ({...t, label: label(t.col).replace(" per 90", "/90").replace("Best-on-ground ", "").replace("On-pitch goal difference vs team", "GD vs team").replace("Share of team ", "Team ")})), {size: Math.min(width, 380), accent, levels: 3}))}</div>
</div>` : null;
```

```js
const allMatches = p
  ? (await sql`SELECT * FROM member_matches WHERE player_id = ${p.player_id} ORDER BY date`).toArray().map((r) => r.toJSON())
  : [];
const seasonRows = allMatches.filter((r) => r.did_play);
// Keyed on the short label, not the raw league: the same competition appears under several raw
// spellings (sponsored and not, "Under 13's" vs "Under 13"), and a Map keyed on labels would keep
// only the last raw name per label and silently hide the other variant's matches. Filtering by
// label instead merges the variants, which is what a reader expects from one dropdown entry.
const compChoices = ["All competitions", ...new Set(allMatches.map((r) => shortLeague(r.league)))];
```

```js
const compInput = Inputs.select(compChoices, {value: "All competitions", label: ""});
const compSel = Generators.input(compInput);
```

```js
const matchRows = allMatches.filter((r) => r.did_play).filter((r) => compSel === "All competitions" || shortLeague(r.league) === compSel)
  .sort((a, b) => d3.descending(toDate(a.date), toDate(b.date)))
  .map((r) => ({...r, opponent: r.side === "home" ? r.away_team : r.side === "away" ? r.home_team : `${r.home_team} v ${r.away_team}`,
    opponent_club: r.side === "home" ? r.away_club : r.side === "away" ? r.home_club : null,
    own: r.side === "home" ? r.home_score : r.away_score, opp: r.side === "home" ? r.away_score : r.home_score,
    ha: r.side === "home" ? "H" : r.side === "away" ? "A" : "–", cup: !isGradedLeague(r.league)}));
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
const ratingPill = (v) => v != null && v > 0
  ? html`<span class="rating-badge ${v >= 7.5 ? 'hi' : v >= 6.8 ? 'mid' : 'low'}">${v.toFixed(1)}</span>`
  : html`<span class="muted">–</span>`;
const hasAnySofaMatches = matchRows.some((r) => r.sofascore_rating != null || r.xg != null);

const matchList = html`<div class="mlist">
  <div class="mrow ${hasAnySofaMatches ? 'has-sofa' : ''} mhead">
    <span></span><span>Opponent</span><span>Grade</span><span>League</span><span></span>
    ${hasAnySofaMatches
      ? ["minutes", "goals", "votes", "sofascore_rating", "xg", "yellow_cards", "red_cards"].map((c) => html`<span>${iconHeader(c, label(c))}</span>`)
      : ["minutes", "goals", "votes", "yellow_cards", "red_cards"].map((c) => html`<span>${iconHeader(c, label(c))}</span>`)}
  </div>
  ${pageRows.map((r) => html`<div class="mrow ${hasAnySofaMatches ? 'has-sofa' : ''}">
    <span class="mdate">${shortDate(r.date)} <span class="ha-pill">${r.ha}</span></span>
    <span class="mopp">${crest(r.opponent_club, 20)} ${r.opponent_club ?? r.opponent}</span>
    <span>${leagueGrade(r.league) ?? "–"}</span>
    <span>${shortLeagueOnly(r.league)}</span>
    <span class="mres">${r.result ? html`<span class="pill ${r.result}">${r.result}</span>` : ""} <span class="score"><b class="${r.own >= r.opp ? "hi" : ""}">${r.own ?? "–"}</b> - <b class="${r.opp >= r.own ? "hi" : ""}">${r.opp ?? "–"}</b></span>${r.borrowed_side ? html`<span class="brw-slot" title="Borrowed for this match">${icon("handshake", {size: 12})}</span>` : ""}</span>
    <span>${fmt("minutes", r.minutes)}</span>
    <span>${r.goals || "0"}</span>
    <span>${voteBadge(r.votes ?? 0)}</span>
    ${hasAnySofaMatches ? html`<span>${ratingPill(r.sofascore_rating)}</span>` : ""}
    ${hasAnySofaMatches ? html`<span>${r.xg != null ? r.xg.toFixed(2) : "–"}</span>` : ""}
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
const careerStatCols = ["played", "started", "minutes", "goals", "votes", "yellow_cards", "red_cards", "clean_sheets"];
const leaguesOf = (c) => String(c.leagues ?? "").split("; ").filter(Boolean);
const careerTable = html`<table class="stats career-table"><thead><tr><th>Season</th><th>Club</th>${careerStatCols.map((c) => html`<th>${isNumericCol(c) ? iconHeader(c, label(c)) : label(c)}</th>`)}</tr></thead>
  <tbody>${careerRows.flatMap((c) => [
    html`<tr class="season-row"><td>${c.season}</td><td>${clubCell(String(c.clubs).split("; ")[0], 18)}</td>${careerStatCols.map((col) => html`<td>${fmt(col, c[col])}</td>`)}</tr>`,
    ...leaguesOf(c).map((l) => html`<tr class="league-row"><td></td><td class="league-name">${GRADE_NAME[leagueGrade(l)] ?? "–"} · ${shortLeagueOnly(l)}</td><td colspan="${careerStatCols.length}"></td></tr>`),
  ])}</tbody></table>`;
const seasonChartCard = () => p ? html`<div class="card">
  <h2>Season so far</h2>
  ${seasonRows.length ? html`<div style="min-height: 280px">${resize((width) => {
    let g = 0, m = 0;
    const cum = seasonRows.map((r, i) => ({i: i + 1, date: r.date, goals: (g += r.goals ?? 0), minutes: (m += r.minutes ?? 0), opp: r.side === "home" ? r.away_team : r.home_team, result: r.result, comp: r.league}));
    return Plot.plot({width, height: 280, marginLeft: 40, x: {label: "Appearance (all competitions) →"}, y: {label: "↑ Cumulative goals", grid: true},
      marks: [Plot.lineY(cum, {x: "i", y: "goals", stroke: accent, curve: "step-after", strokeWidth: 2}),
              Plot.dot(cum, {x: "i", y: "goals", fill: (d) => d.result === "W" ? "#2ca02c" : d.result === "D" ? "#999" : "#d62728", r: 4,
                channels: {Date: (d) => fmtDate(d.date), Opponent: "opp", Result: "result", Competition: "comp", Minutes: "minutes"}, tip: {format: {x: false, y: true}}})]});
  })}</div>` : html`<p class="muted">No matches recorded.</p>`}
  <p class="muted">Dot colour shows the match result.</p>
</div>` : null;
const matchesCard = () => p ? html`<div class="card">
  <div class="mtitle"><h2>Match stats</h2>${compInput}</div>
  ${matchList}
  <p class="muted">Includes cups and trials. Minutes are DRIBL's own; votes are 3-2-1 best-on-ground.</p>
</div>` : null;
const careerCard = () => p ? html`<div class="card">
  <h2>Career <span class="muted">— seasons recorded in DRIBL</span></h2>
  <div class="table-scroll">${careerTable}</div>
  <p class="muted">Leagues/grades played that season are listed under it.</p>
</div>` : null;
```

```js
const tab = Mutable("Overview");
const setTab = (t) => (tab.value = t);
```

<div>${p ? html`
  <div class="tabbar" role="tablist">
    <button class="tab-btn ${tab === "Overview" ? "active" : ""}" onclick=${() => setTab("Overview")}>Overview</button>
    <button class="tab-btn ${tab === "Matches" ? "active" : ""}" onclick=${() => setTab("Matches")}>Matches</button>
    <button class="tab-btn ${tab === "Career" ? "active" : ""}" onclick=${() => setTab("Career")}>Career</button>
  </div>
  ${tab === "Overview" ? html`${profileCard()}${traitsCard()}` : ""}
  ${tab === "Matches" ? html`${seasonChartCard()}${matchesCard()}` : ""}
  ${tab === "Career" ? careerCard() : ""}
` : ""}</div>

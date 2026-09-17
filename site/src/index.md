---
title: Explorer
toc: false
sql:
  appearances: ./data/appearances.parquet
---

# Player explorer

```js
import {labels, label, short, describe, fmt, fmtDate, iconHeaders, formats, metricOptions, groupMetricSelect, crest, clubCell, shortLeague, GRADES, GRADE_NAME, GRADE_COLORS} from "./components/labels.js";
import {gemMark} from "./components/icons.js";
const players = await FileAttachment("./data/players.csv").csv({typed: true});
const leagues = await FileAttachment("./data/leagues.json").json();
const meta = await FileAttachment("./data/meta.json").json();
const playerCols = Object.keys(players[0]);
```

<p class="muted">${meta.matches.toLocaleString()} matches · ${meta.players.toLocaleString()} players · ${meta.appearances.toLocaleString()} appearances · State League 1 &amp; 2, all grades.</p>

<div class="section">
  <div>

```js
const role = view(Inputs.radio(["All", "Outfield", "GK"], {value: "All", label: "Role"}));
const gemsOnly = view(Inputs.toggle({label: "Hidden gems only", value: false}));
```
  <span class="muted">Hidden gem = Reserves/U18 player with no senior minutes all season.</span>
  </div>
  <div>

```js
const xMetric = view(groupMetricSelect(Inputs.select(metricOptions(playerCols), {value: "minutes", label: "X axis"})));
const yMetric = view(groupMetricSelect(Inputs.select(metricOptions(playerCols), {value: "goals", label: "Y axis"})));
```
  </div>
</div>

<details>
<summary>More filters</summary>
<div class="section">
  <div>

```js
const division = view(Inputs.checkbox(["SL1", "SL2"], {value: ["SL1", "SL2"], label: "Division"}));
const gradeSel = view(Inputs.checkbox(GRADES, {value: [...GRADES.values()], label: "Grade"}));
```
  </div>
  <div>

```js
const leagueChoices = new Map(leagues.filter((l) => division.includes(l.division) && gradeSel.includes(l.grade)).map((l) => [l.short, l.league]));
const leagueSel = view(Inputs.select(leagueChoices, {multiple: true, size: Math.min(leagueChoices.size, 12) || 1, value: [...leagueChoices.values()], label: "Leagues (⌘/ctrl-click to pick several)"}));
```
  </div>
  <div>

```js
const minMinutes = view(Inputs.range([0, 2000], {value: 450, step: 10, label: "Minimum minutes"}));
const minApps = view(Inputs.range([0, 25], {value: 3, step: 1, label: "Minimum appearances"}));
```
  </div>
  <div>

```js
const defenseView = view(Inputs.toggle({label: "Defensive impact view", value: role === "GK"}));
const defenseMetric = view(Inputs.radio(new Map([["Clean sheets", "clean_sheets"], ["Goals conceded on pitch", "ga_on_pitch"]]), {value: "clean_sheets", label: ""}));
```
  <span class="muted">Defensive view plots minutes played vs clean sheets or goals conceded on pitch — on for GK by default, or switch it on for any role.</span>
  </div>
  <div>

```js
const clubs = ["(none)", ...new Set(players.map((d) => d.club).sort())];
const club = view(Inputs.select(clubs, {value: "(none)", label: "Highlight club"}));
const labelTop = view(Inputs.range([0, 30], {value: 8, step: 1, label: "Label top N on Y"}));
```
  </div>
</div>
</details>

```js
const filtered = players.filter((d) =>
  division.includes(d.division) && gradeSel.includes(d.grade) && leagueSel.includes(d.league) &&
  (role === "All" || d.role === role) && d.minutes >= minMinutes && d.apps >= minApps && (!gemsOnly || d.hidden_gem)
);
const xs = defenseView ? "minutes" : xMetric, ys = defenseView ? defenseMetric : yMetric;
const withXY = filtered.filter((d) => d[xs] != null && d[ys] != null);
const yReversed = labels[ys]?.higher_is_better === false;
const rankY = yReversed ? d3.ascending : d3.descending;
const topN = [...withXY].sort((a, b) => rankY(a[ys], b[ys]) || d3.descending(a[xs], b[xs])).slice(0, labelTop);
```

```js
const selected = Mutable(null);
const setSelected = (d) => (selected.value = d);
```

```js
const tipChannels = {Player: "player_name", Club: "club", Team: "team", League: "league", Age: "age", Apps: "apps", Minutes: "minutes",
  Goals: "goals", "NP goals/90": "npg_per90", Votes: "votes", "Senior mins": "sen_minutes"};
function chart(width) {
  const p = Plot.plot({
    width, height: 560, grid: true, inset: 12, marginLeft: 50,
    style: {fontSize: "12px"},
    x: {label: `${label(xs)} →`, nice: true},
    y: {label: `${yReversed ? "↓" : "↑"} ${label(ys)}`, nice: true, reverse: yReversed},
    color: {...GRADE_COLORS, legend: true, tickFormat: (g) => GRADE_NAME[g]},
    marks: [
      Plot.ruleX([d3.median(withXY, (d) => d[xs])], {stroke: "#bbb", strokeDasharray: "3,3"}),
      Plot.ruleY([d3.median(withXY, (d) => d[ys])], {stroke: "#bbb", strokeDasharray: "3,3"}),
      Plot.dot(withXY, {
        x: xs, y: ys, fill: "grade", r: 4.5, fillOpacity: 0.65,
        stroke: (d) => (d.hidden_gem ? "#b8860b" : "white"), strokeWidth: (d) => (d.hidden_gem ? 1.5 : 0.5),
        channels: tipChannels,
        tip: {format: {x: (v) => fmt(xs, v), y: (v) => fmt(ys, v), fill: (g) => GRADE_NAME[g], stroke: false, strokeWidth: false,
          Minutes: (v) => fmt("minutes", v), Apps: (v) => fmt("apps", v), Goals: (v) => fmt("goals", v),
          "NP goals/90": (v) => fmt("npg_per90", v), Votes: (v) => fmt("votes", v), "Senior mins": (v) => fmt("sen_minutes", v)}},
      }),
      club === "(none)" ? null : Plot.dot(withXY.filter((d) => d.club === club), {x: xs, y: ys, r: 8, stroke: "red", strokeWidth: 2, fill: "none"}),
      Plot.text(topN, {x: xs, y: ys, text: "player_name", dy: -9, fontSize: 10, fill: "currentColor", stroke: "var(--theme-background)", strokeWidth: 3}),
      selected ? Plot.dot([selected], {x: xs, y: ys, r: 10, stroke: "black", strokeWidth: 2, fill: "none"}) : null,
    ],
  });
  p.addEventListener("click", () => { if (p.value) setSelected(p.value); });
  return p;
}
```

<div class="grid grid-cols-3" style="grid-auto-rows: auto;">
  <div class="card grid-colspan-2">
    <h2>${label(ys)} vs ${label(xs)} <span class="muted">— ${withXY.length.toLocaleString()} players shown${gemsOnly ? " (hidden gems only)" : ""}</span></h2>
    <p class="muted">${describe(ys)}. ${describe(xs)}. Dashed lines are medians of the players shown. Gold outline = hidden gem (no senior minutes).${yReversed ? " Axis flipped so the top shows the best performers." : ""} Each point is one player-season (a player who played for two teams appears twice). Hover for details, click to pin a player.</p>
    <div style="min-height: 560px">${resize(chart)}</div>
  </div>
  <div class="card">
    ${selected ? detail(selected) : html`<h2>Pick a player</h2><p class="muted">Click a point on the chart or a row in the table below.</p>`}
  </div>
</div>

```js
function detail(d) {
  const k = (col) => html`<div><div class="v">${fmt(col, d[col])}</div><div class="l">${short(col)}</div></div>`;
  const gk = d.role === "GK";
  return html`<h2 style="display:flex;align-items:center;gap:8px">${crest(d.club, 28)} <a href="./player?id=${d.player_id}&team=${d.team_id}">${d.player_name}</a></h2>
  <p>${d.club} · ${GRADE_NAME[d.grade]} · ${shortLeague(d.league)} · age ${d.age ?? "–"}</p>
  <div class="badges"><span class="badge grade">${GRADE_NAME[d.grade]} · ${d.division}</span>${d.hidden_gem ? gemMark() : ""}${d.u18_player ? html`<span class="badge grade">U18 player</span>` : ""}${d.minutes_est_apps > 0 ? html`<span class="badge est" title="${describe("minutes_est_apps")}">${d.minutes_est_apps} apps est. minutes</span>` : ""}</div>
  <p><a href="./player?id=${d.player_id}&team=${d.team_id}"><b>Open full profile →</b></a> · <a href="${d.dribl_url}" target="_blank" rel="noopener">DRIBL ↗</a></p>
  <div class="kpi">${k("age")}${k("apps")}${k("starts")}${k("minutes")}${gk ? k("clean_sheets") : k("goals")}${gk ? k("ga_on_pitch_per90") : k("npg_per90")}${k("votes")}${k("team_goal_share_pct")}${k("gd_on_pitch_vs_team")}${k("yellow_cards")}${k("captain_apps")}${k("borrowed_apps")}${k("sen_minutes")}</div>
  <p class="muted" style="margin-top:0.75rem">Grades played: ${d.grades_played} · highest: ${GRADE_NAME[d.highest_grade]} · ${d.n_teams} team${d.n_teams === 1 ? "" : "s"} · team finished ${d.team_ladder_pos ?? "–"}/${d.ladder_teams ?? "–"} (${fmt("team_ppg", d.team_ppg)} PPG)</p>
  <p class="muted">${d.goals_go_ahead} go-ahead · ${d.goals_winner} winners · ${d.goals_equaliser} equalisers · ${d.goals_late} late goals · ${d.goals_penalty} pens · team PPG when starting vs not: ${fmt("ppg_start_diff", d.ppg_start_diff)}</p>`;
}
```

```js
const matchRows = selected
  ? (await sql`SELECT date_local, round, league, opponent, home_away, result, team_gf, team_ga, starting, sub_on_min, sub_off_min, minutes, minutes_estimated, goals, goals_penalty, votes, yellow_cards, red_cards, borrowed, is_captain, gf_on_pitch, ga_on_pitch, clean_sheet
       FROM appearances WHERE player_id = ${selected.player_id} AND team_id = ${selected.team_id} ORDER BY date_local`).toArray().map((r) => r.toJSON())
  : [];
```

```js
const matchCols = ["date_local", "round", "opponent", "home_away", "result", "team_gf", "team_ga", "starting", "sub_on_min", "sub_off_min", "minutes", "minutes_estimated", "goals", "goals_penalty", "votes", "yellow_cards", "red_cards", "borrowed", "is_captain", "gf_on_pitch", "ga_on_pitch", "clean_sheet"];
```

<div class="grid grid-cols-3" style="grid-auto-rows: auto;">
  <div class="card grid-colspan-2">
    <h2>${selected ? `${selected.player_name} — match by match` : "Match by match"}</h2>
    ${selected ? Inputs.table(matchRows, {columns: matchCols, header: iconHeaders(matchCols), format: {...formats(matchCols), date_local: fmtDate}, rows: 12, select: false, width: {opponent: 220}}) : html`<p class="muted">Select a player to see every appearance, queried live with SQL from the appearances file.</p>`}
  </div>
  <div class="card">
    <h2>Season so far</h2>
    ${selected && matchRows.length ? resize((width) => {
      let g = 0, m = 0;
      const cum = matchRows.map((r, i) => ({i: i + 1, date: fmtDate(r.date_local), goals: (g += r.goals), minutes: (m += r.minutes), opp: r.opponent, result: r.result}));
      return Plot.plot({width, height: 220, marginLeft: 40, x: {label: "Appearance →"}, y: {label: "↑ Cumulative goals", grid: true},
        marks: [Plot.lineY(cum, {x: "i", y: "goals", stroke: "#e6550d", curve: "step-after"}),
                Plot.dot(cum, {x: "i", y: () => 0, fill: (d) => d.result === "W" ? "#2ca02c" : d.result === "D" ? "#999" : "#d62728", r: 4,
                  channels: {Date: "date", Opponent: "opp", Result: "result", Minutes: "minutes"}, tip: {format: {x: false, y: false}}})]});
    }) : html`<p class="muted">Cumulative goals by appearance; dots show W/D/L.</p>`}
  </div>
</div>

## Players shown

```js
const tableCols = ["player_name", "club", "league", "grade", "age", "role", "apps", "starts", "minutes", "goals", "goals_open_play", "npg_per90", "team_goal_share_pct", "votes", "votes_per_app", "gd_on_pitch_vs_team", "clean_sheets", "ga_on_pitch_per90", "yellow_cards", "red_cards", "captain_apps", "borrowed_apps", "sen_minutes", "hidden_gem"];
const searched = view(Inputs.search(filtered, {placeholder: "Search player, club or team…", columns: ["player_name", "club", "team"]}));
```

```js
const picked = view(Inputs.table(searched, {columns: tableCols, header: iconHeaders(tableCols), format: {...formats(tableCols), player_name: (v, i) => html`<a href="./player?id=${searched[i].player_id}&team=${searched[i].team_id}">${v}</a>`, club: (v) => clubCell(v, 16)}, rows: 18, multiple: false,
  sort: ys, reverse: labels[ys]?.higher_is_better !== false, width: {player_name: 170, club: 150, league: 170}}));
```

```js
if (picked) setSelected(picked);
```

```js
// deep link: ?player=<player_id>[&team=<team_id>]
{
  const q = new URLSearchParams(location.search);
  const pid = q.get("player"), tid = q.get("team");
  if (pid) {
    const hit = players.find((d) => d.player_id === pid && (!tid || d.team_id === tid)) ?? players.find((d) => d.player_id === pid);
    if (hit) setSelected(hit);
  }
}
```

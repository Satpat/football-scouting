---
title: Explorer
toc: false
sql:
  appearances: ./data/appearances.parquet
---

# Player explorer

```js
import {labels, label, short, describe, fmt, fmtDate, iconHeaders, formats, metricOptions, groupMetricSelect, crest, clubCell, shortLeague, shortLeagueOnly, GRADES, GRADE_NAME, GRADE_COLORS, withTooltip} from "./components/labels.js";
import {gemMark} from "./components/icons.js";
const players = await FileAttachment("./data/players.csv").csv({typed: true});
const leagues = await FileAttachment("./data/leagues.json").json();
const meta = await FileAttachment("./data/meta.json").json();
const playerCols = Object.keys(players[0]);
```

<p class="muted">${meta.matches.toLocaleString()} matches · ${meta.players.toLocaleString()} players · ${meta.appearances.toLocaleString()} appearances · State League 1 &amp; 2, the NPL and SAASL, all grades.</p>

<div class="section">
  <div>

```js
const role = view(Inputs.radio(["All", "Outfield", "GK"], {value: "All", label: "Role"}));
const gemsOnly = view(withTooltip(Inputs.toggle({label: "💎 Hidden gems only", value: false}), "Active in Reserves/U18 with 0 senior minutes across the season."));
const emergingOnly = view(withTooltip(Inputs.toggle({label: "⚡ Emerging seniors only", value: false}), "U21 players in Senior NPL with Sofascore rating ≥ 7.0 or (xG/90 + xA/90) ≥ 0.40."));
const undervaluedOnly = view(withTooltip(Inputs.toggle({label: "🎯 Undervalued only", value: false}), "Players on bottom-half NPL teams (min 450 minutes) with duel win rate ≥ 60% or passing accuracy ≥ 80%."));
```
  <p class="muted" style="margin-top: 6px; font-size: 12px; line-height: 1.45;">
    <b>💎 Gem:</b> Reserves/U18, 0 senior mins.<br>
    <b>⚡ Emerging:</b> U21 in Senior NPL, rating &ge; 7.0 or (xG+xA)/90 &ge; 0.40.<br>
    <b>🎯 Undervalued:</b> Bottom-half NPL team, min 450 mins, &ge;60% duels or &ge;80% passes.
  </p>
  </div>
  <div>

```js
const PRESETS = {
  custom: {label: "Custom axes", x: null, y: null},
  finishing: {label: "Finishing (xG vs Goals/90)", x: "xg_p90", y: "goals_per90"},
  creation: {label: "Creation (Key passes vs xA/90)", x: "key_passes_p90", y: "xa_p90"},
  defending: {label: "Ball Winning (Int vs Tackles/90)", x: "interceptions_p90", y: "tackles_p90"},
  duels: {label: "Duels (Duels/90 vs Win %)", x: "duels_p90", y: "duel_win_pct"},
  retention: {label: "Retention (Passes/90 vs Pass %)", x: "passes_p90", y: "pass_acc_pct"},
};
const preset = view(Inputs.radio(new Map(Object.entries(PRESETS).map(([k, v]) => [v.label, k])), {value: "custom", label: "Preset"}));
```
  </div>
  <div>

```js
const xMetric = view(groupMetricSelect(Inputs.select(metricOptions(playerCols), {value: "minutes", label: "X axis", disabled: preset !== "custom"})));
const yMetric = view(groupMetricSelect(Inputs.select(metricOptions(playerCols), {value: "goals", label: "Y axis", disabled: preset !== "custom"})));
```
  </div>
</div>

<details>
<summary>More filters</summary>
<div class="section">
  <div>

```js
const division = view(Inputs.checkbox(["SL1", "SL2", "NPL", "SAASL"], {value: ["SL1", "SL2", "NPL", "SAASL"], label: "Division"}));
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
const matchesArchetype = (d) => {
  const anyActive = gemsOnly || emergingOnly || undervaluedOnly;
  if (!anyActive) return true;
  return (gemsOnly && d.hidden_gem) ||
         (emergingOnly && d.emerging_senior) ||
         (undervaluedOnly && d.undervalued_performer);
};

const filtered = players.filter((d) =>
  division.includes(d.division) && gradeSel.includes(d.grade) && leagueSel.includes(d.league) &&
  (role === "All" || d.role === role) && d.minutes >= minMinutes && d.apps >= minApps &&
  matchesArchetype(d)
);
const xs = preset !== "custom" ? PRESETS[preset].x : (defenseView ? "minutes" : xMetric);
const ys = preset !== "custom" ? PRESETS[preset].y : (defenseView ? defenseMetric : yMetric);
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
  Goals: "goals", "NP goals/90": "npg_per90", Votes: "votes", "Senior mins": "sen_minutes",
  Rating: "sofascore_rating", xG: "xg", xA: "xa"};
const tipFormat = {x: (v) => fmt(xs, v), y: (v) => fmt(ys, v), fill: (g) => GRADE_NAME[g], stroke: false, strokeWidth: false,
  League: shortLeague, Minutes: (v) => fmt("minutes", v), Apps: (v) => fmt("apps", v), Goals: (v) => fmt("goals", v),
  "NP goals/90": (v) => fmt("npg_per90", v), Votes: (v) => fmt("votes", v), "Senior mins": (v) => fmt("sen_minutes", v),
  Rating: (v) => fmt("sofascore_rating", v), xG: (v) => fmt("xg", v), xA: (v) => fmt("xa", v)};
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
        tip: {format: tipFormat},
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
    <p class="muted">${describe(ys)}. ${describe(xs)}.</p>
    <p class="muted">Dashed lines are medians of the players shown. Gold outline = hidden gem (no senior minutes).${yReversed ? " Axis flipped so the top shows the best performers." : ""}</p>
    <p class="muted">Each point is one player-season (a player who played for two teams appears twice). Hover for details, click to pin a player.</p>
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
  const hasSofa = d.sofascore_rating != null || d.xg > 0 || d.passes_total > 0;
  return html`<h2 style="display:flex;align-items:center;gap:8px">${crest(d.club, 28)} <a href="./player?id=${d.player_id}&team=${d.team_id}">${d.player_name}</a></h2>
  <div class="badges">
    <span class="badge grade">${GRADE_NAME[d.grade]} · ${d.division}</span>
    ${d.hidden_gem ? gemMark() : ""}
    ${d.emerging_senior ? html`<span class="badge" style="background:#0284c7;color:white;" title="${describe('emerging_senior')}">⚡ Emerging Senior</span>` : ""}
    ${d.undervalued_performer ? html`<span class="badge" style="background:#7c3aed;color:white;" title="${describe('undervalued_performer')}">🎯 Undervalued</span>` : ""}
    ${d.u18_player ? html`<span class="badge grade">U18 player</span>` : ""}
    ${d.minutes_est_apps > 0 ? html`<span class="badge est" title="${describe("minutes_est_apps")}">${d.minutes_est_apps} apps est. minutes</span>` : ""}
  </div>
  <p><a href="./player?id=${d.player_id}&team=${d.team_id}"><b>Open full profile →</b></a> · <a href="${d.dribl_url}" target="_blank" rel="noopener">DRIBL ↗</a></p>
  <div class="kpi">${k("age")}${k("apps")}${k("starts")}${k("minutes")}${gk ? k("clean_sheets") : k("goals")}${gk ? k("ga_on_pitch_per90") : k("npg_per90")}${k("votes")}${k("team_goal_share_pct")}${k("gd_on_pitch_vs_team")}${k("yellow_cards")}${k("captain_apps")}${k("borrowed_apps")}${k("sen_minutes")}</div>
  ${hasSofa ? html`<div class="kpi" style="margin-top:0.5rem;background:rgba(59,130,246,0.06);border:1px solid rgba(59,130,246,0.2);border-radius:6px;padding:6px 8px;">
    ${d.sofascore_rating ? k("sofascore_rating") : ""}${d.xg > 0 ? k("xg_p90") : ""}${d.xa > 0 ? k("xa_p90") : ""}${d.key_passes_p90 > 0 ? k("key_passes_p90") : ""}${d.pass_acc_pct > 0 ? k("pass_acc_pct") : ""}${d.duel_win_pct > 0 ? k("duel_win_pct") : ""}
  </div>` : ""}
  <p class="muted" style="margin-top:0.75rem">Grades played: ${d.grades_played} · highest: ${GRADE_NAME[d.highest_grade]} · ${d.n_teams} team${d.n_teams === 1 ? "" : "s"} · team finished ${d.team_ladder_pos ?? "–"}/${d.ladder_teams ?? "–"} (${fmt("team_ppg", d.team_ppg)} PPG)</p>
  <p class="muted">${d.goals_go_ahead} go-ahead · ${d.goals_winner} winners · ${d.goals_equaliser} equalisers · ${d.goals_late} late goals · ${d.goals_penalty} pens · team PPG when starting vs not: ${fmt("ppg_start_diff", d.ppg_start_diff)}</p>`;
}
```

```js
const matchRows = selected
  ? (await sql`SELECT date_local, round, league, opponent, home_away, result, team_gf, team_ga, starting, sub_on_min, sub_off_min, minutes, minutes_estimated, goals, assists, sofascore_rating, xg, xa, key_passes, goals_penalty, votes, yellow_cards, red_cards, clean_sheet
       FROM appearances WHERE player_id = ${selected.player_id} AND team_id = ${selected.team_id} ORDER BY date_local`).toArray().map((r) => r.toJSON())
  : [];
```

```js
const matchCols = ["date_local", "round", "opponent", "home_away", "result", "team_gf", "team_ga", "starting", "minutes", "goals", "assists", "sofascore_rating", "xg", "xa", "key_passes", "votes", "yellow_cards", "red_cards", "clean_sheet"];
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
const tableCols = ["player_name", "club", "league", "grade", "age", "role", "apps", "starts", "minutes", "goals", "npg_per90", "sofascore_rating", "xg_p90", "xa_p90", "duel_win_pct", "pass_acc_pct", "votes", "votes_per_app", "gd_on_pitch_vs_team", "clean_sheets", "hidden_gem"];
const searched = view(Inputs.search(filtered, {placeholder: "Search player, club or team…", columns: ["player_name", "club", "team"]}));
```

```js
const picked = view(Inputs.table(searched, {columns: tableCols, header: iconHeaders(tableCols), format: {...formats(tableCols), player_name: (v, i) => html`<a href="./player?id=${searched[i].player_id}&team=${searched[i].team_id}">${v}</a>${searched[i].emerging_senior ? html` <span title="Emerging Senior">⚡</span>` : ""}${searched[i].undervalued_performer ? html` <span title="Undervalued Performer">🎯</span>` : ""}`, club: (v) => clubCell(v, 16), league: shortLeagueOnly}, rows: 18, multiple: false,
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

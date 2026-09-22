---
title: Explorer
toc: false
sql:
  appearances: ./data/appearances.parquet
---

# Player explorer

```js
import {labels, label, short, describe, fmt, iconHeaders, formats, metricOptions, groupMetricSelect, crest, clubCell, shortLeague, shortLeagueOnly, GRADES, GRADE_NAME, GRADE_COLORS, withTooltip} from "./components/labels.js";
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
  </div>
  <div class="preset-stack">

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
    width, height: 560, grid: true, inset: 12, marginLeft: 60, marginBottom: 50,
    style: {fontSize: "12px"},
    x: {label: `${label(xs)} →`, nice: true, labelAnchor: "center", labelOffset: 32},
    y: {label: `${label(ys)} ${yReversed ? "←" : "→"}`, nice: true, reverse: yReversed, labelAnchor: "center", labelOffset: 42},
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

<div class="grid explorer-main" style="grid-auto-rows: auto;">
  <div class="card">
    <h2>${label(ys)} vs ${label(xs)} <span class="muted">— ${withXY.length.toLocaleString()} players shown${gemsOnly ? " (hidden gems only)" : ""}</span></h2>
    <p class="muted">${describe(ys)}. ${describe(xs)}.</p>
    <p class="muted">Dashed lines are medians of the players shown. Gold outline = hidden gem (no senior minutes).${yReversed ? " Axis flipped so the top shows the best performers." : ""}</p>
    <p class="muted">Each point is one player-season (a player who played for two teams appears twice). Tap or click a point to see details.</p>
    <div style="min-height: 560px">${resize(chart)}</div>
  </div>
  <div class="card">
    ${selected ? detail(selected) : html`<h2>Pick a player</h2><p class="muted">Tap a point on the chart or a row in the table below.</p>`}
  </div>
</div>

```js
function detail(d) {
  const k = (col) => html`
    <div class="stat">
      <div class="v">${fmt(col, d[col])}</div>
      <div class="l">${short(col)}</div>
    </div>
  `;

  const gk = d.role === "GK";
  const hasSofa = d.sofascore_rating != null || d.market_value_eur != null || d.xg > 0 || d.xa > 0 || d.key_passes_p90 > 0 || d.pass_acc_pct > 0 || d.duel_win_pct > 0;

  return html`
    <div class="player-header">
      ${crest(d.club, 28)}
      <div>
        <h2>
          <a href="./player?id=${d.player_id}&team=${d.team_id}">
            ${d.player_name}
          </a>
        </h2>
      </div>
    </div>

    <div class="badges">
      <span class="badge grade">${GRADE_NAME[d.grade]} · ${d.division}</span>
      ${d.hidden_gem ? gemMark() : ""}
      ${d.emerging_senior ? html`
        <span class="badge emerging"
          title="${describe('emerging_senior')}">
          ⚡ Emerging Senior
        </span>
      ` : ""}
      ${d.undervalued_performer ? html`
        <span class="badge undervalued"
          title="${describe('undervalued_performer')}">
          🎯 Undervalued
        </span>
      ` : ""}
      ${d.u18_player ? html`
        <span class="badge grade">U18 player</span>
      ` : ""}
      ${d.minutes_est_apps > 0 ? html`
        <span class="badge est"
          title="${describe("minutes_est_apps")}">
          ${d.minutes_est_apps} apps est. minutes
        </span>
      ` : ""}
    </div>

    <div class="player-links">
      <a href="./player?id=${d.player_id}&team=${d.team_id}">
        <b>Open full profile →</b>
      </a>
      ·
      <a href="${d.dribl_url}" target="_blank" rel="noopener">
        DRIBL ↗
      </a>
      ${d.sofascore_url ? html`
        ·
        <a href="${d.sofascore_url}"
           target="_blank"
           rel="noopener"
           class="sofascore-link">
          Sofascore ↗
        </a>
      ` : ""}
    </div>

    <!--primary stats-->
    <div class="stat-section">
      <div class="stat-grid primary">
        ${k("age")}
        ${k("apps")}
        ${k("starts")}
        ${k("minutes")}
        ${gk ? k("clean_sheets") : k("goals")}
        ${gk ? k("ga_on_pitch_per90") : k("npg_per90")}
      </div>
    </div>

    <!--secondary stats-->
    <div class="stat-section secondary-section">
      <div class="stat-grid secondary">
        ${k("votes")}
        ${k("team_goal_share_pct")}
        ${k("gd_on_pitch_vs_team")}
        ${k("yellow_cards")}
        ${k("captain_apps")}
        ${k("borrowed_apps")}
        ${k("sen_minutes")}
      </div>
    </div>

    <!--advanced stats-->
    ${hasSofa ? html`
      <div class="advanced-section">
        <div class="section-label">Advanced</div>

        <div class="stat-grid advanced">
          ${d.sofascore_rating ? k("sofascore_rating") : ""}
          ${d.market_value_eur ? k("market_value_eur") : ""}
          ${d.xg > 0 ? k("xg_p90") : ""}
          ${d.xa > 0 ? k("xa_p90") : ""}
          ${d.key_passes_p90 > 0 ? k("key_passes_p90") : ""}
          ${d.pass_acc_pct > 0 ? k("pass_acc_pct") : ""}
          ${d.duel_win_pct > 0 ? k("duel_win_pct") : ""}
        </div>
      </div>
    ` : ""}

    <!--context-->
    <div class="player-context">
      <div class="context-row">
        <span>Grades played</span>
        <strong>${d.grades_played}</strong>
      </div>

      <div class="muted" style="margin-top:0.75rem">
        <div>${d.goals_go_ahead} go-ahead</div>
        <div>${d.goals_winner} winners</div>
        <div>${d.goals_equaliser} equalisers</div>
        <div>${d.goals_late} late goals</div>
        <div>${d.goals_penalty} pens</div>
      </div>

      <div class="ppg-stat">
        Team PPG when starting vs not:
        <strong>${fmt("ppg_start_diff", d.ppg_start_diff)}</strong>
      </div>
    </div>
  `;
}
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

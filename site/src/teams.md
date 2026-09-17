---
title: Teams & ladders
theme: dashboard
toc: false
---

# Teams & ladders

```js
import {label, fmt, headers, formats, crest, GRADE_NAME, GRADE_COLORS} from "./components/labels.js";
const clubFmt = (v) => { const s = document.createElement("span"); s.className = "club-cell"; s.append(crest(v, 18), document.createTextNode(" " + v)); return s; };
const teams = await FileAttachment("./data/teams.csv").csv({typed: true});
const ladders = await FileAttachment("./data/ladders.csv").csv({typed: true});
const leagues = await FileAttachment("./data/leagues.json").json();
```

```js
const leagueChoices = new Map(leagues.map((l) => [l.short, l.league]));
const league = view(Inputs.select(leagueChoices, {value: leagues[0].league, label: "League"}));
```

```js
const ladder = ladders.filter((d) => d.league === league).sort((a, b) => a.position - b.position);
const ladderCols = ["position", "team", "club", "played", "won", "drawn", "lost", "goals_for", "goals_against", "goal_difference", "points"];
const teamRows = teams.filter((d) => d.primary_league === league);
```

<div class="grid grid-cols-2" style="grid-auto-rows: auto;">
  <div class="card">
    <h2>${leagueChoices.entries().find(([, v]) => v === league)?.[0] ?? league} ladder</h2>
    ${Inputs.table(ladder, {columns: ladderCols, header: headers(ladderCols), format: {...formats(ladderCols), club: clubFmt}, rows: 14, select: false, width: {team: 260}})}
  </div>
  <div class="card">
    <h2>Attack vs defence (regular season)</h2>
    <p class="muted">Goals for per match vs goals against per match. Top-left is good.</p>
    ${resize((width) => Plot.plot({width, height: 420, grid: true, inset: 20,
      x: {label: "Goals against per match →"}, y: {label: "↑ Goals for per match"},
      marks: [
        Plot.dot(teamRows, {x: "ga_per_match", y: "gf_per_match", r: 6, fill: "grade", fillOpacity: 0.8, channels: {Team: "team", PPG: "ppg", Position: "ladder_pos", "Players used": "players_used", "Borrowed in": "borrowed_in_apps"}, tip: true}),
        Plot.text(teamRows, {x: "ga_per_match", y: "gf_per_match", text: "club", dy: -10, fontSize: 10, stroke: "var(--theme-background)", strokeWidth: 3, fill: "currentColor"})
      ]}))}
  </div>
</div>

## All teams

```js
const teamCols = ["team", "club", "primary_league", "grade", "division", "ladder_pos", "ppg", "gf_per_match", "ga_per_match", "gd_per_match", "matches", "players_used", "borrowed_in_apps", "borrowed_in_players"];
```

<div class="card">
  ${Inputs.table(teams, {columns: teamCols, header: headers(teamCols), format: {...formats(teamCols), club: clubFmt}, rows: 20, select: false, sort: "ppg", reverse: true, width: {team: 260, primary_league: 200}})}
  <p class="muted">"Borrowed in" counts appearances by players DRIBL flags as borrowed from another team in the same club — a high number means the team leans on players from other grades.</p>
</div>

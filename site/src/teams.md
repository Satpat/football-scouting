---
title: Teams & ladders
toc: false
---

# Teams & ladders

```js
import {shortHeaders, formats, clubCell, clubInfo} from "./components/labels.js";
import {crestHref} from "./components/crests.js";
const teamFmt = (v, i, rows) => clubCell(rows[i].club, 18);
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
const ladderCols = ["position", "team", "played", "won", "drawn", "lost", "goals_for", "goals_against", "goal_difference", "points"];
const teamRows = teams.filter((d) => d.primary_league === league).map((d) => ({...d, crestHref: crestHref[clubInfo(d.club)?.slug]}));
```

<div class="grid grid-cols-2" style="grid-auto-rows: auto;">
  <div class="card">
    <h2>${leagueChoices.entries().find(([, v]) => v === league)?.[0] ?? league} ladder</h2>
    ${Inputs.table(ladder, {columns: ladderCols, header: shortHeaders(ladderCols), format: {...formats(ladderCols), team: teamFmt}, rows: 20, select: false, layout: "auto", width: {team: 300}})}
  </div>

  <div class="card">
    <h2>Attack vs defence (regular season)</h2>
    <p class="muted">Goals for per match vs goals against per match. Top-right is good.</p>
    <div style="min-height: 420px">${resize((width) => Plot.plot({width, height: 420, grid: true, inset: 24,
      x: {label: "Goals against per match ←", reverse: true}, y: {label: "↑ Goals for per match"},
      marks: [
        Plot.dot(teamRows, {x: "ga_per_match", y: "gf_per_match", r: 14, fillOpacity: 0, channels: {Team: "team", PPG: "ppg", Position: "ladder_pos", "Players used": "players_used", "Borrowed in": "borrowed_in_apps"}, tip: true}),
        Plot.image(teamRows.filter((d) => d.crestHref), {x: "ga_per_match", y: "gf_per_match", src: "crestHref", width: 26, height: 26}),
        Plot.text(teamRows.filter((d) => !d.crestHref), {x: "ga_per_match", y: "gf_per_match", text: "club", dy: -10, fontSize: 10, stroke: "var(--theme-background)", strokeWidth: 3, fill: "currentColor"})
      ]}))}</div>
  </div>
</div>

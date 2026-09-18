---
title: Teams & ladders
toc: false
---

# Teams & ladders

```js
import {shortHeaders, formats, clubCell, clubInfo, GRADES, GRADE_NAME} from "./components/labels.js";
import {crestHref} from "./components/crests.js";
const teamFmt = (v, i, rows) => clubCell(rows[i].club, 18);
const teams = await FileAttachment("./data/teams.csv").csv({typed: true});
const ladders = await FileAttachment("./data/ladders.csv").csv({typed: true});
const leagues = await FileAttachment("./data/leagues.json").json();
```

```js
// The ladders are a complete grid of competition x grade, so a single dropdown listing all
// twelve combinations made readers scan a flat list for something they could pick on two axes.
// Finals are their own competition rather than a grade — they have all three grades of their own.
const compOf = (l) => l.is_finals ? `${l.division} Finals` : l.region ? `${l.division} ${l.region}` : l.division;
const comps = [...new Set(leagues.map(compOf))];
const comp = view(Inputs.select(comps, {value: comps[0], label: "League"}));
const grade = view(Inputs.select(GRADES, {value: "SEN", label: "Grade"}));
```

```js
const selected = leagues.find((l) => compOf(l) === comp && l.grade === grade);
const league = selected?.league;
const ladder = ladders.filter((d) => d.league === league).sort((a, b) => a.position - b.position);
const ladderCols = ["position", "team", "played", "won", "drawn", "lost", "goals_for", "goals_against", "goal_difference", "points"];
const teamRows = teams.filter((d) => d.primary_league === league).map((d) => ({...d, crestHref: crestHref[clubInfo(d.club)?.slug]}));
```

<div class="grid grid-ladder" style="grid-auto-rows: auto;">
  <div class="card ladder">
    <h2>${selected?.short ?? `${comp} ${GRADE_NAME[grade]}`} ladder</h2>
    ${ladder.length
      ? Inputs.table(ladder, {columns: ladderCols, header: shortHeaders(ladderCols), format: {...formats(ladderCols), team: teamFmt}, rows: 20, select: false, layout: "auto"})
      : html`<p class="muted">No ladder recorded for ${comp} ${GRADE_NAME[grade]}.</p>`}
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

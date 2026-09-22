---
title: Teams & ladders
toc: false
---

# Teams & ladders

```js
import {shortHeaders, formats, clubCell, clubInfo, GRADES, GRADE_NAME} from "./components/labels.js";
import {crestHref} from "./components/crests.js";
import {dataTable} from "./components/data-table.js";
const teamFmt = (v, row) => clubCell(row.club, 18);
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
const teamRows = teams.filter((d) => d.primary_league === league).map((d) => ({...d, crestHref: crestHref[clubInfo(d.club)?.slug]}));
const hasXg = teamRows.some((d) => d.team_xg_per_match != null && d.team_xg_per_match > 0);
const enrichedLadder = ladder.map((l) => {
  const t = teamRows.find((tr) => tr.team_id === l.team_id || tr.team === l.team);
  return {
    ...l,
    team_xg_per_match: t?.team_xg_per_match,
    team_xga_per_match: t?.team_xga_per_match,
    avg_possession_pct: t?.avg_possession_pct,
  };
});
const ladderCols = hasXg
  ? ["position", "team", "played", "won", "drawn", "lost", "goals_for", "goals_against", "points", "team_xg_per_match", "team_xga_per_match", "avg_possession_pct"]
  : ["position", "team", "played", "won", "drawn", "lost", "goals_for", "goals_against", "goal_difference", "points"];
const chartMode = view(Inputs.radio(["Actual (GF vs GA)", "Expected (xG vs xGA)"], {value: "Actual (GF vs GA)", label: "Chart view", disabled: !hasXg}));
```

```js
const useXg = hasXg && chartMode === "Expected (xG vs xGA)";
const xCol = useXg ? "team_xga_per_match" : "ga_per_match";
const yCol = useXg ? "team_xg_per_match" : "gf_per_match";
const xLabel = useXg ? "Expected goals against (xGA) per match ←" : "Goals against per match ←";
const yLabel = useXg ? "Expected goals for (xG) per match →" : "Goals for per match →";
const tipChannels = useXg
  ? {Team: "team", "xG/match": "team_xg_per_match", "xGA/match": "team_xga_per_match", "xGD/match": "team_xgd_per_match", "Possession %": "avg_possession_pct", PPG: "ppg", Position: "ladder_pos"}
  : {Team: "team", PPG: "ppg", Position: "ladder_pos", "Players used": "players_used", "Borrowed in": "borrowed_in_apps"};
```

<div class="grid grid-ladder" style="grid-auto-rows: auto;">
  <div class="card ladder">
    <h2>${selected?.short ?? `${comp} ${GRADE_NAME[grade]}`} ladder</h2>
    ${enrichedLadder.length
      ? dataTable(enrichedLadder, {columns: ladderCols, header: shortHeaders(ladderCols), format: {...formats(ladderCols), team: teamFmt}})
      : html`<p class="muted">No ladder recorded for ${comp} ${GRADE_NAME[grade]}.</p>`}
  </div>

  <div class="card">
    <h2>Attack vs defence (regular season)</h2>
    <p class="muted">${useXg ? "Expected goals created vs expected goals conceded per match (Sofascore data). Top-right is good." : "Goals for per match vs goals against per match. Top-right is good."}</p>
    <div style="min-height: 420px">${resize((width) => Plot.plot({width, height: 420, grid: true, inset: 24, marginLeft: 60, marginBottom: 50,
      x: {label: xLabel, reverse: true, labelAnchor: "center", labelOffset: 32}, y: {label: yLabel, labelAnchor: "center", labelOffset: 42},
      marks: [
        Plot.dot(teamRows, {x: xCol, y: yCol, r: 14, fillOpacity: 0, channels: tipChannels, tip: true}),
        Plot.image(teamRows.filter((d) => d.crestHref), {x: xCol, y: yCol, src: "crestHref", width: 26, height: 26}),
        Plot.text(teamRows.filter((d) => !d.crestHref), {x: xCol, y: yCol, text: "club", dy: -10, fontSize: 10, stroke: "var(--theme-background)", strokeWidth: 3, fill: "currentColor"})
      ]}))}</div>
  </div>
</div>

---
title: Shortlist
toc: false
---

# Shortlist

```js
import {fmt, iconHeaders, formats, shortLeagueOnly, GRADES} from "./components/labels.js";
const shortlist = await FileAttachment("./data/shortlist.csv").csv({typed: true});
const leagues = await FileAttachment("./data/leagues.json").json();
const notes = await FileAttachment("./data/notes.json").json();
```

<p class="muted">Players with at least 450 minutes and 5 appearances, ranked within role by <b>gem score</b>: a league-adjusted composite of non-penalty goals per 90, best-on-ground votes, on-pitch goal difference vs the team, share of team goals and minutes share, plus a bonus for having no senior minutes and for being a U18 player. Rates are shrunk toward the league average so short bursts don't dominate. Details on the <a href="./about">About</a> page.</p>

<div class="grid grid-cols-4 filters">
  <div class="card">

```js
const division = view(Inputs.checkbox(["SL1", "SL2"], {value: ["SL1", "SL2"], label: "Division"}));
const gradeSel = view(Inputs.checkbox(GRADES, {value: [...GRADES.values()], label: "Grade"}));
```
  </div>
  <div class="card">

```js
const leagueChoices = new Map(leagues.filter((l) => !l.is_finals && division.includes(l.division) && gradeSel.includes(l.grade)).map((l) => [l.short, l.league]));
const leagueSel = view(Inputs.select(leagueChoices, {multiple: true, size: Math.min(leagueChoices.size, 9) || 1, value: [...leagueChoices.values()], label: "Leagues"}));
```
  </div>
  <div class="card">

```js
const role = view(Inputs.radio(["Outfield", "GK"], {value: "Outfield", label: "Role"}));
const gemsOnly = view(Inputs.toggle({label: "Hidden gems only", value: true}));
const u18Only = view(Inputs.toggle({label: "U18 players only", value: false}));
```
  </div>
  <div class="card">

```js
const topN = view(Inputs.range([10, 400], {value: 50, step: 10, label: "Show top N"}));
const clubs = ["(all)", ...new Set(shortlist.map((d) => d.club).sort())];
const club = view(Inputs.select(clubs, {value: "(all)", label: "Club"}));
```
  </div>
</div>

```js
const rows = shortlist.filter((d) => d.role === role && division.includes(d.division) && gradeSel.includes(d.grade) && leagueSel.includes(d.league) &&
  (!gemsOnly || d.hidden_gem) && (!u18Only || d.u18_player) && (club === "(all)" || d.club === club))
  .sort((a, b) => d3.descending(a.gem_score, b.gem_score)).slice(0, topN).map((d, i) => ({...d, shown_rank: i + 1}));
```

```js
const outfieldCols = ["shown_rank", "player_name", "club", "league", "grade", "age", "gem_score", "apps", "minutes", "goals_open_play", "npg_per90", "team_goal_share_pct", "goals_go_ahead", "goals_winner", "votes", "gd_on_pitch_vs_team", "sen_minutes", "borrowed_apps", "team_ladder_pos"];
const gkCols = ["shown_rank", "player_name", "club", "league", "grade", "age", "gem_score", "apps", "minutes", "ga_on_pitch_per90", "clean_sheets", "clean_sheet_pct", "votes", "sen_minutes", "borrowed_apps", "team_ladder_pos"];
const cols = role === "GK" ? gkCols : outfieldCols;
const hdr = {...iconHeaders(cols), shown_rank: "#"};
const gemScoreCell = (v, i) => {
  const wrap = document.createElement("span");
  wrap.className = "gem-tip";
  wrap.tabIndex = 0;
  wrap.append(fmt("gem_score", v));
  const clauses = String(rows[i].why_flagged ?? "").split("; ").filter(Boolean);
  if (clauses.length) {
    const pop = document.createElement("div");
    pop.className = "gem-tip-pop";
    const title = document.createElement("div");
    title.className = "gem-tip-title";
    title.textContent = "Why flagged";
    const ul = document.createElement("ul");
    ul.append(...clauses.map((c) => { const li = document.createElement("li"); li.textContent = c; return li; }));
    pop.append(title, ul);
    wrap.append(pop);
  }
  return wrap;
};
const fmts = {...formats(cols), shown_rank: (v) => v, league: shortLeagueOnly, gem_score: gemScoreCell, minutes: (v, i) => fmt("minutes", v) + (rows[i].minutes_est_apps > 0 ? "*" : ""), player_name: (v, i) => html`<a href="./player?id=${rows[i].player_id}&team=${rows[i].team_id}">${v}</a>`,
};
```

<div class="card">
  <h2>${role === "GK" ? "Goalkeepers" : "Outfield players"} <span class="muted">— ${rows.length} shown</span></h2>
  ${Inputs.table(rows, {columns: cols, header: hdr, format: fmts, rows: 25, select: false, width: {player_name: 140, club: 120}, layout: "auto"})}
  <p class="muted">Click a name to open the player's profile. Hover the gem score for why they're flagged. * marks estimated minutes — sub minutes weren't recorded for that player, mostly U18.</p>
</div>

<div class="card">
  <h2>How the score is built</h2>
  ${notes.filter((n) => ["Shortlist score", "Pathway", "Votes", "Borrowed", "Minutes estimated"].includes(n.topic)).map((n) => html`<p><b>${n.topic}.</b> ${n.note}</p>`)}
</div>

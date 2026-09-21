---
title: Player shortlist
toc: false
---

# Player shortlist

```js
import {fmt, iconHeaders, formats, shortLeagueOnly, GRADES} from "./components/labels.js";
const shortlist = await FileAttachment("./data/shortlist.csv").csv({typed: true});
const leagues = await FileAttachment("./data/leagues.json").json();
const notes = await FileAttachment("./data/notes.json").json();
```

<p class="muted">Players with at least 450 minutes and 5 appearances, ranked within role by <b>gem score</b> — a league-adjusted composite of non-penalty goals per 90, best-on-ground votes, on-pitch goal difference, and share of team goals and minutes.</p>
<p class="muted">Bonus for no senior minutes and for being a U18 player. Rates are shrunk toward the league average so short bursts don't dominate — details on the <a href="./about">About</a> page.</p>

<div class="section">
  <div>

```js
const role = view(Inputs.radio(["Outfield", "GK"], {value: "Outfield", label: "Role"}));
const gemsOnly = view(Inputs.toggle({label: "Hidden gems only", value: true}));
const u18Only = view(Inputs.toggle({label: "U18 players only", value: false}));
```
  </div>
  <div>

```js
const sortBy = view(Inputs.radio(["Gem score", "Sofascore rating", "xG / 90"], {value: "Gem score", label: "Rank by"}));
const topN = view(Inputs.range([10, 400], {value: 50, step: 10, label: "Show top N"}));
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
const leagueChoices = new Map(leagues.filter((l) => !l.is_finals && division.includes(l.division) && gradeSel.includes(l.grade)).map((l) => [l.short, l.league]));
const leagueSel = view(Inputs.select(leagueChoices, {multiple: true, size: Math.min(leagueChoices.size, 9) || 1, value: [...leagueChoices.values()], label: "Leagues"}));
```
  </div>
  <div>

```js
const clubs = ["(all)", ...new Set(shortlist.map((d) => d.club).sort())];
const club = view(Inputs.select(clubs, {value: "(all)", label: "Club"}));
```
  </div>
</div>
</details>

```js
const sortKey = sortBy === "Sofascore rating" ? "sofascore_rating" : sortBy === "xG / 90" ? "xg_p90" : "gem_score";
const rows = shortlist.filter((d) => d.role === role && division.includes(d.division) && gradeSel.includes(d.grade) && leagueSel.includes(d.league) &&
  (!gemsOnly || d.hidden_gem) && (!u18Only || d.u18_player) && (club === "(all)" || d.club === club) && (sortKey === "gem_score" || (d[sortKey] != null && d[sortKey] > 0)))
  .sort((a, b) => d3.descending(a[sortKey] ?? -999, b[sortKey] ?? -999)).slice(0, topN).map((d, i) => ({...d, shown_rank: i + 1}));
```

```js
const outfieldCols = ["shown_rank", "player_name", "club", "league", "grade", "age", "gem_score", "sofascore_rating", "xg_p90", "xa_p90", "duel_win_pct", "apps", "minutes", "npg_per90", "team_goal_share_pct", "goals_go_ahead", "goals_winner", "votes_per_app", "gd_on_pitch_vs_team", "borrowed_apps", "team_ladder_pos"];
const gkCols = ["shown_rank", "player_name", "club", "league", "grade", "age", "gem_score", "sofascore_rating", "apps", "minutes", "ga_on_pitch_per90", "clean_sheets", "clean_sheet_pct", "votes_per_app", "borrowed_apps", "team_ladder_pos"];
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
const ratingPill = (v) => v != null && v > 0
  ? html`<span class="rating-badge ${v >= 7.5 ? 'hi' : v >= 6.8 ? 'mid' : 'low'}">${v.toFixed(1)}</span>`
  : "–";
const fmts = {...formats(cols), shown_rank: (v) => v, league: shortLeagueOnly, gem_score: gemScoreCell, sofascore_rating: ratingPill, minutes: (v, i) => fmt("minutes", v) + (rows[i].minutes_est_apps > 0 ? "*" : ""), player_name: (v, i) => html`<a href="./player?id=${rows[i].player_id}&team=${rows[i].team_id}">${v}</a>`,
};
```

<div class="card">
  <h2>${role === "GK" ? "Goalkeepers" : "Outfield players"} <span class="muted">— ${rows.length} shown</span></h2>
  ${Inputs.table(rows, {columns: cols, header: hdr, format: fmts, rows: 25, select: false, width: {player_name: 140, club: 120}, layout: "auto"})}
  <p class="muted">Click a name to open the player's profile. Hover the gem score for why they're flagged. * marks estimated minutes — sub minutes weren't recorded for that player, mostly U18.</p>
</div>

<div class="card">
  <h2>How the score is built</h2>
  <div class="notes-cols">${notes.filter((n) => ["Shortlist score", "Pathway", "Votes", "Borrowed", "Minutes estimated"].includes(n.topic)).map((n) => html`<p><b>${n.topic}.</b> ${n.note}</p>`)}</div>
</div>

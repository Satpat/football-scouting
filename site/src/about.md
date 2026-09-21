---
title: About the data
toc: true
---

# About the data

```js
const notes = await FileAttachment("./data/notes.json").json();
const meta = await FileAttachment("./data/meta.json").json();
```

<p class="muted">
Source: DRIBL match centres for two SA governing bodies — Football SA (fsa.dribl.com: State League 1, State League 2, and the RAA National Premier League, across Seniors, Reserves, U18s and finals) and SAASL (saasl.dribl.com: Home and Away regular season across all Saturday and Sunday grades) — enriched with optical and event-level match tracking from Sofascore.
</p>
<p class="muted">
Extracted ${meta.extracted_at?.slice(0, 10)}: ${meta.matches.toLocaleString()} completed matches, ${meta.appearances.toLocaleString()} appearances, ${meta.players.toLocaleString()} unique players across ${meta.teams} teams.
</p>

## The data layers

The platform combines two distinct data streams to provide both broad competition coverage and elite-tier analytical depth:

<div class="grid grid-cols-2" style="gap: 1.25rem; margin: 1.25rem 0;">
  <div class="card">
    <h3>1. DRIBL administrative match data</h3>
    <p class="muted"><b>Universal baseline across all 39 leagues</b></p>
    <p>DRIBL is the official competition management platform used by Football SA and SAASL. Across all four divisions and 39 leagues, DRIBL records:</p>
    <ul>
      <li><b>Match participation:</b> Official team sheets, starters, substitutes, and exact substitution minutes.</li>
      <li><b>Scoring &amp; Discipline:</b> Goals (with penalty and own-goal flags), yellow and red cards, and captaincy.</li>
      <li><b>Match events &amp; timeline:</b> Minute-by-minute goal sequences (used to compute equaliser, go-ahead, winner, and late goals).</li>
      <li><b>Official 3-2-1 votes:</b> Best-on-ground referee/official votes per match.</li>
      <li><b>Squad movement:</b> "Borrowed" player flags indicating players playing up or down between grades within their club.</li>
    </ul>
  </div>

  <div class="card">
    <h3>2. Sofascore advanced event tracking</h3>
    <p class="muted"><b>Elite tiers &amp; Senior NPL</b></p>
    <p>To capture on-ball actions unavailable in standard administrative scorecards, matches across 7 South Australian tournaments (including Senior NPL and State League 1) are enriched with detailed event data:</p>
    <ul>
      <li><b>Expected metrics:</b> Expected Goals ($xG$), Expected Assists ($xA$), and $xG$ per shot.</li>
      <li><b>Passing &amp; Creativity:</b> Accurate passes, passing accuracy %, key passes, big chances created, and long ball completion %.</li>
      <li><b>Duels &amp; Defending:</b> Ground duels, aerial duels, duel win rate %, tackles, interceptions, recoveries, and clearances.</li>
      <li><b>Goalkeeping:</b> Saves, saves from inside the box, and save success rate.</li>
      <li><b>Algorithmic match ratings:</b> Objective 0–10 performance ratings calculated from match events.</li>
      <li><b>Physical profiles:</b> Verified dates of birth, age, height (cm), player tactical positions, and official player headshots.</li>
    </ul>
    <p class="muted" style="margin-top: 8px; font-size: 12px; border-top: 1px solid var(--theme-foreground-faintest); padding-top: 6px;">
      <b>Coverage across leagues:</b> Advanced optical tracking covers Senior NPL and tracked leagues. Unmeasured divisions (SL2, SAASL) cleanly retain null (–) rather than zero so league rankings and scatter plots remain unbiased.
    </p>
  </div>
</div>

---

## Scouting archetypes & tags

To assist recruiters and analysts in identifying different player profiles, the platform highlights three distinct scouting archetypes:

<div class="grid grid-cols-3" style="grid-auto-rows: auto; gap: 1rem; margin: 1.5rem 0;">
  <div class="card" style="border-left: 4px solid var(--gem);">
    <h3>💎 Hidden Gem</h3>
    <p class="muted"><b>Unpromoted talent in lower grades</b></p>
    <p>A player active in <b>Reserves</b> or <b>Under 18s</b> who has logged <b>zero senior minutes</b> all season.</p>
    <p class="muted">Flags young or unpromoted players who are dominating youth/reserves competition and deserve consideration for senior promotion.</p>
  </div>
  <div class="card" style="border-left: 4px solid #0284c7;">
    <h3>⚡ Emerging Senior</h3>
    <p class="muted"><b>U21 standout at the top level</b></p>
    <p>A U21 player (<code>age &le; 21</code> or recorded in U18) competing in <b>Senior NPL</b> who achieves a <b>Sofascore rating &ge; 7.0</b> OR <b>$(xG/90 + xA/90) &ge; 0.40$</b>.</p>
    <p class="muted">Highlights young talents who have broken into the highest state division and are already delivering top-tier senior production.</p>
  </div>
  <div class="card" style="border-left: 4px solid #7c3aed;">
    <h3>🎯 Undervalued Performer</h3>
    <p class="muted"><b>Efficiency in tough team contexts</b></p>
    <p>A player on a <b>bottom-half NPL team</b> (ladder position &gt; half of teams, min. 450 minutes) recording a <b>duel win rate &ge; 60%</b> OR <b>passing accuracy &ge; 80%</b>.</p>
    <p class="muted">Surfaces high-quality contributors whose individual efficiency is masked by poor team results or lower possession sides.</p>
  </div>
</div>

---

## Method notes

<div class="notes-cols">${notes.map((n) => html`<p><b>${n.topic}.</b> ${n.note}</p>`)}</div>

---

## Reading the numbers responsibly

- **Sample size matters**: A regular season consists of at most 22 rounds. Per-90 rates built on small samples are naturally volatile; the shortlist shrinks them toward the league average, but treat anything under ~900 minutes as a scouting lead rather than a final verdict.
- **League context is paramount**: Competition difficulty varies significantly between grades. A goal in State League 2 Reserves is not equivalent to an NPL Senior goal. Scores and percentiles are adjusted strictly within each individual league, never pooled across grades.
- **Process vs outcome ($xG$ & $xA$)**: Finishing streaks fluctuate with variance. Expected goals ($xG$) and expected assists ($xA$) reflect the underlying quality of chances created and conceded, offering a more stable indicator of future performance.
- **Data origins**: Administrative match records are entered by club volunteers; optical event metrics are tracked algorithmically. Expect occasional volunteer attribution errors in sub minutes or card assignments.
- **Data informs, the eye decides**: Statistical indicators are designed to help scouts and clubs identify *who* to go watch in person and where to focus attention. They complement scouting workflows rather than replacing match evaluation.


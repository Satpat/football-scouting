---
title: About the data
toc: true
---

# About the data

```js
const notes = await FileAttachment("./data/notes.json").json();
const meta = await FileAttachment("./data/meta.json").json();
```

Source: Football SA's DRIBL match centre (fsa.dribl.com), 2026 season, HPG Homes State League 1 and State League 2 — Seniors, Reserves and Under 18s plus the finals series. Extracted ${meta.extracted_at?.slice(0, 10)}: ${meta.matches.toLocaleString()} completed matches, ${meta.appearances.toLocaleString()} appearances, ${meta.players.toLocaleString()} players across ${meta.teams} teams.

## What DRIBL records — and what it doesn't

DRIBL lineups carry: who was named, who started, substitution minutes, goals (with penalty and own-goal flags), cards, captain and goalkeeper flags, a per-match "borrowed from another team" flag, and 3-2-1 votes. That is the whole on-ball picture.

There are **no assists, shots, expected goals, passes, tackles, positions or ages**. Positions and formations exist as fields but are essentially never filled in for these leagues, so the only role split is goalkeeper vs outfield.

## Method notes

<div class="notes-cols">${notes.map((n) => html`<p><b>${n.topic}.</b> ${n.note}</p>`)}</div>

## Reading the numbers responsibly

- A season is at most 22 rounds. Rates built on a handful of games are noisy; the shortlist shrinks them toward the league average, but treat anything under ~900 minutes as a lead, not a verdict.
- A goal in SL2 South Reserves is not an SL1 goal. Scores are adjusted within each league, never across leagues.
- Playing time is a coach's opinion mixed with availability and injury, not a measure of ability.
- Everything is entered by club volunteers after the match. Expect some misattributed goals, missing subs and unflagged goalkeepers.
- The numbers build a list of players to go and watch. They don't replace watching.

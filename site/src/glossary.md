---
title: Stat glossary
toc: true
---

# Stat glossary

Every number shown anywhere on this site — in the Explorer table and chart, the shortlist, team ladders, match-by-match lists, and player profiles — is explained here in plain English, grouped the same way the app itself groups them (e.g. in the Explorer's axis dropdowns).

A few conventions that apply throughout:

- **"Per 90"** means the number is scaled to a full 90-minute match. A substitute who plays 30 minutes and a starter who plays the full 90 can't be compared fairly on raw totals, so per-90 numbers divide out the minutes and let you compare "if they'd played a whole match."
- **"–"** in any table means the data isn't available for that row, not that the value is zero. Most commonly this is because advanced Sofascore tracking (xG, passing, duels, etc.) only covers Senior NPL and a handful of other leagues — see [About the data](./about) for exactly which competitions are covered.
- **Percentages and rates** are always calculated over the relevant total for that row (e.g. pass accuracy is completed passes ÷ attempted passes for that player), not against the whole league.
- For the full story on where this data comes from and how it's collected, see [About the data](./about). This page only explains what each number *means*.

## Playing time & availability

<div class="card">
<ul>
<li><b>Appearances</b> — matches the player actually took part in, whether they started or came off the bench.</li>
<li><b>Starts</b> — matches where the player was in the starting eleven.</li>
<li><b>Sub appearances</b> — matches where the player came on as a substitute rather than starting.</li>
<li><b>Bench (unused)</b> — matches where the player was named in the squad but never got on the field.</li>
<li><b>Squad selections</b> — every time the player was named in a matchday squad, whether they played or not (appearances + bench unused).</li>
<li><b>Minutes played</b> — total minutes on the field this season, worked out from when they started, came on, went off, or were sent off. Some U18 minutes are estimated rather than exact, because substitution times aren't always recorded at that level — the shortlist and season tables mark these with an asterisk (*).</li>
<li><b>Apps with estimated minutes</b> — how many of the player's appearances used an estimate rather than a recorded exact minute count. A high number here means their minutes-based stats (per-90s, minutes played) are approximate.</li>
<li><b>Share of team minutes</b> — the percentage of all the minutes their team could theoretically give to one outfield position that this player actually played. A high number means they were a fixture in the team; a low number means they were fringe or missed a lot of the season.</li>
<li><b>Availability</b> — the percentage of the team's matches this player was named in the squad for at all (whether picked to play or not). Low availability usually points to injury, suspension, or being out of favour.</li>
<li><b>Start rate</b> — of the matches they actually appeared in, what percentage were starts rather than sub appearances. A player who's always a starter will be near 100%; a rotation/impact substitute will be much lower.</li>
<li><b>Finals appearances</b> — how many of their appearances came in finals matches specifically, separate from the regular season.</li>
</ul>
</div>

## Goals & attacking output

<div class="card">
<ul>
<li><b>Goals</b> — goals scored, not counting own goals.</li>
<li><b>Non-penalty goals</b> — goals scored from open play, excluding both penalties and own goals. This is often a fairer way to compare finishers, since penalty-takers can inflate a raw goal count.</li>
<li><b>Penalty goals</b> — goals scored specifically from the penalty spot.</li>
<li><b>Own goals</b> — goals accidentally credited to the opposition off this player.</li>
<li><b>Goals per 90</b> — goals scaled to a full match's worth of minutes, so heavy-minute players and occasional starters can be compared fairly.</li>
<li><b>Non-penalty goals per 90</b> — the same idea, but using non-penalty goals — usually the best single number for "how good a finisher is this player, minute for minute."</li>
<li><b>Share of team goals</b> — what percentage of all the goals their team scored this season came from this player. A high share means the team leans heavily on them for goals.</li>
<li><b>Equalisers</b> — goals that brought the scoreline level (from behind or a draw stayed a draw).</li>
<li><b>Go-ahead goals</b> — goals that put their team in the lead for the first time in that match.</li>
<li><b>Winning goals</b> — go-ahead goals in a match their team went on to win without ever falling level again — i.e. goals that decided the result.</li>
<li><b>Late goals (75'+)</b> — goals scored from the 75th minute onward, when games are often being won or lost.</li>
<li><b>Consolation goals</b> — goals scored while already two or more behind, when the result is effectively settled.</li>
<li><b>Away goals</b> — goals scored in matches played away from home.</li>
<li><b>Goals vs top-half teams</b> — goals scored against opponents who finished in the top half of their ladder — a rough proxy for scoring against tougher opposition.</li>
<li><b>Goals as substitute</b> — goals scored specifically after coming on from the bench.</li>
<li><b>Goals per 90 as substitute</b> — goals-as-substitute scaled to 90 minutes of substitute appearances, which highlights "impact sub" profiles who score a lot relative to their (often short) time on the field.</li>
</ul>
</div>

## Advanced attacking metrics (Sofascore & xG)

<div class="card">
<p class="muted">Everything in this section comes from Sofascore's optical/event tracking, which only covers Senior NPL and a handful of other tracked leagues — see <a href="./about">About the data</a>. Rows outside those leagues show "–" rather than a misleading zero.</p>
<ul>
<li><b>Sofascore rating</b> — Sofascore's own algorithmic match rating (roughly 0–10), averaged across the player's matches. It blends many on-ball actions into one overall performance score.</li>
<li><b>Expected goals (xG)</b> — a single number representing how many goals a player "should" have scored, based on the quality (location, angle, pressure) of every shot they took. A player scoring well above their xG is finishing better than the average player would from the same chances; well below suggests they're missing gilt-edged opportunities or having bad luck.</li>
<li><b>xG / 90</b> — expected goals scaled to a full match, for comparing players with different amounts of playing time.</li>
<li><b>Expected assists (xA)</b> — the same idea as xG, but for passes: how many assists a player "should" have recorded based on the quality of the chances they created for teammates.</li>
<li><b>xA / 90</b> — expected assists scaled to a full match.</li>
<li><b>Assists</b> — passes (or other actions) that directly led to a teammate's goal.</li>
<li><b>Assists / 90</b> — assists scaled to a full match.</li>
<li><b>Goal involvements</b> — goals plus assists combined — a simple "how often were they directly involved in a goal" count.</li>
<li><b>G+A / 90</b> — goal involvements scaled to a full match.</li>
<li><b>Finishing delta (Goals − xG)</b> — actual goals minus expected goals. A positive number means they're outscoring the quality of chances they get (over-performing, which can mean genuine finishing skill or can mean it's unlikely to continue); a negative number means they're scoring less than the chances suggest they should.</li>
<li><b>Assist delta (Assists − xA)</b> — the same comparison for assists: actual assists minus expected assists.</li>
<li><b>Total shots</b> — every shot attempted, on or off target.</li>
<li><b>Shots on target</b> — shots that would have gone in without a save or a block by a defender on the line.</li>
<li><b>Shots / 90</b> — total shots scaled to a full match — a proxy for how involved a player is in a team's attacking chances, separate from finishing quality.</li>
<li><b>Shot accuracy</b> — the percentage of shots that were on target.</li>
<li><b>xG per shot</b> — the average quality of each shot the player takes, on a scale where higher means better-quality chances (closer range, better angle) rather than just "more shots." A player can have a low shot count but a high xG per shot if they only shoot from good positions.</li>
</ul>
</div>

## Creation & passing (Sofascore)

<div class="card">
<ul>
<li><b>Key passes</b> — passes that directly led to a teammate having a shot (whether or not it went in). Also called chances created.</li>
<li><b>Key passes / 90</b> — key passes scaled to a full match.</li>
<li><b>Big chances created</b> — passes or plays that gave a teammate a clear, high-probability scoring opportunity — a stricter version of a key pass.</li>
<li><b>Big chances missed</b> — the flip side: clear scoring chances the player themself created for but that went to waste (missed by them or a teammate, depending on tracking).</li>
<li><b>Total passes</b> — every pass attempted, successful or not.</li>
<li><b>Accurate passes</b> — passes that successfully reached a teammate.</li>
<li><b>Passes / 90</b> — total passes attempted, scaled to a full match — a rough measure of how involved a player is in build-up play.</li>
<li><b>Pass accuracy</b> — the percentage of attempted passes that found a teammate.</li>
<li><b>Total long balls</b> — long/lofted passes attempted, as opposed to short ground passes.</li>
<li><b>Accurate long balls</b> — long balls that successfully reached a teammate.</li>
<li><b>Long balls / 90</b> — long balls attempted, scaled to a full match.</li>
<li><b>Long ball accuracy</b> — the percentage of long balls that found a teammate — long passes are inherently harder to complete than short ones, so this is usually lower than overall pass accuracy.</li>
</ul>
</div>

## Duels & defending (Sofascore)

<div class="card">
<ul>
<li><b>Duels won</b> — one-on-one contests for the ball (ground tackles, shoulder challenges, 50/50s — anything that isn't specifically an aerial duel) that the player won.</li>
<li><b>Total duels</b> — every one-on-one contest the player was involved in, won or lost.</li>
<li><b>Duels / 90</b> — total duels contested, scaled to a full match — how often a player gets physically involved in contests for the ball.</li>
<li><b>Duel win rate</b> — the percentage of duels the player won. A good indicator of physical/positional battles, separate from how often they get involved.</li>
<li><b>Aerial duels won</b> — headers and jumping contests won specifically.</li>
<li><b>Total aerial duels</b> — every aerial contest the player was involved in.</li>
<li><b>Aerials / 90</b> — aerial duels contested, scaled to a full match.</li>
<li><b>Aerial duel win rate</b> — the percentage of aerial contests won — a key number for centre-backs and target-man strikers.</li>
<li><b>Tackles</b> — attempts to win the ball off an opponent by challenging for it at their feet.</li>
<li><b>Tackles / 90</b> — tackles scaled to a full match.</li>
<li><b>Interceptions</b> — times the player read and cut out an opponent's pass before it reached its target.</li>
<li><b>Interceptions / 90</b> — interceptions scaled to a full match.</li>
<li><b>Ball recoveries</b> — times the player picked up a loose ball (not a tackle or interception — just a ball nobody had clear possession of).</li>
<li><b>Recoveries / 90</b> — ball recoveries scaled to a full match.</li>
<li><b>Clearances</b> — times the player kicked, headed, or otherwise knocked the ball away from danger near their own goal, with no specific intent to keep possession.</li>
<li><b>Clearances / 90</b> — clearances scaled to a full match.</li>
<li><b>Defensive actions</b> — tackles and interceptions added together, as a simple combined defensive-workload number.</li>
<li><b>Defensive actions / 90</b> — defensive actions scaled to a full match.</li>
<li><b>Dribbles completed</b> — times the player beat an opponent one-on-one while running with the ball.</li>
<li><b>Total dribbles</b> — every attempt to dribble past an opponent, successful or not.</li>
<li><b>Dribbles / 90</b> — completed dribbles scaled to a full match.</li>
<li><b>Dribble success rate</b> — the percentage of dribble attempts that came off.</li>
<li><b>Touches</b> — every time the player made contact with the ball, of any kind (pass, shot, dribble, tackle, etc.) — a general measure of overall involvement in the game.</li>
<li><b>Touches / 90</b> — touches scaled to a full match.</li>
<li><b>Dispossessed</b> — times the player lost the ball to an opponent's tackle while in possession.</li>
</ul>
</div>

## On-pitch defensive impact

<div class="card">
<p class="muted">These compare what happens for the whole team while a specific player is on the field — they capture team-level effect, not just individual actions, so they work for every position, not just defenders and goalkeepers.</p>
<ul>
<li><b>Team goals while on pitch</b> — goals the team scored in matches/minutes this player was on the field for.</li>
<li><b>Goals conceded while on pitch</b> — goals the team conceded while this player was on the field.</li>
<li><b>Team goal difference per 90 on pitch</b> — the team's (goals for minus goals against) per 90 minutes, counted only for the time this player was on the field.</li>
<li><b>On-pitch goal difference vs team</b> — takes the number above and subtracts the team's overall regular-season goal difference per match, so a positive number means the team does <i>better</i> defensively/overall with this player on than their season average, and a negative number means the team does worse.</li>
<li><b>Goals conceded per 90 on pitch</b> — goals conceded per 90 minutes, counted only while this player was on the field.</li>
<li><b>Goals conceded vs team average</b> — the number above, minus the team's overall goals-conceded-per-match average — so a negative number means fewer goals go in with this player on the pitch than the team's average, which is a good sign for a defender or goalkeeper.</li>
</ul>
</div>

## Goalkeeping

<div class="card">
<ul>
<li><b>Clean sheets</b> — full matches where the team didn't concede a goal while this player was on the field. Shown for goalkeepers and outfield players alike.</li>
<li><b>Full matches</b> — matches the player played from start to finish, with no substitution either way.</li>
<li><b>Clean sheet rate</b> — clean sheets as a percentage of full matches played.</li>
<li><b>Saves</b> — shots the goalkeeper stopped from going in.</li>
<li><b>Saves / 90</b> — saves scaled to a full match.</li>
<li><b>Saves inside box</b> — saves made from shots taken inside the penalty area, generally the higher-danger, harder saves to make.</li>
</ul>
</div>

## Discipline

<div class="card">
<ul>
<li><b>Yellow cards</b> — cautions received.</li>
<li><b>Red cards</b> — dismissals (straight reds and second yellows).</li>
<li><b>Yellow cards per 90</b> — yellow cards scaled to a full match, so a player who's only played a handful of games isn't unfairly compared to one who's played all season.</li>
</ul>
</div>

## Recognition & votes

<div class="card">
<p class="muted">DRIBL records an official 3-2-1 best-on-ground vote after every match, similar to league MVP voting elsewhere.</p>
<ul>
<li><b>Best-on-ground votes</b> — total 3-2-1 votes earned across the season (3 votes for best afield, 2 for second-best, 1 for third).</li>
<li><b>Best-on-ground (3 votes)</b> — how many matches the player was awarded the maximum 3 votes (i.e. named best afield).</li>
<li><b>Votes per appearance</b> — total votes divided by appearances — a rate that rewards players who are consistently among the best on the field, not just ones who play a lot of matches.</li>
<li><b>Captain appearances</b> — matches the player captained their team.</li>
<li><b>Borrowed appearances</b> — matches flagged by DRIBL as the player being "borrowed" — i.e. playing up or down a grade for a different team within the same club than their usual one, often to fill a squad shortage.</li>
</ul>
</div>

## Team context

<div class="card">
<p class="muted">These describe the team the player plays for, not the player individually — useful for judging a player's numbers in context (e.g. a striker's stats mean something different on a title-winning team vs a bottom-of-the-table one).</p>
<ul>
<li><b>Team points per game when playing</b> — the team's average points-per-game in matches this specific player took part in.</li>
<li><b>Team PPG: starts vs not</b> — the team's points-per-game when this player starts, minus their points-per-game when he doesn't (minimum 3 matches each way to qualify) — a rough signal of how much the team's results depend on this player starting.</li>
<li><b>Team ladder position</b> — where the player's team finished on the regular-season ladder.</li>
<li><b>Team points per game</b> — the team's overall regular-season points-per-game.</li>
<li><b>Team xG per match</b> — the team's average expected goals created per match across the regular season (see Expected goals above).</li>
<li><b>Team xGA per match</b> — the team's average expected goals conceded per match.</li>
<li><b>Team xGD per match</b> — the team's expected goal difference per match (xG created minus xG conceded) — a measure of overall attacking-minus-defensive quality that tends to be a better predictor of future results than actual goal difference.</li>
<li><b>Average possession</b> — the team's average share of ball possession across the regular season.</li>
</ul>
</div>

## Career totals (all teams, all grades)

<div class="card">
<p class="muted">Unlike the stats above, which are usually shown per player-per-team-per-season, these add up everything a player has done <i>this season across every grade and every team</i> they played for (e.g. a player borrowed between Seniors and Reserves).</p>
<ul>
<li><b>Senior minutes (all teams)</b> — total minutes played at Senior grade, combined across every team the player turned out for.</li>
<li><b>Reserves minutes (all teams)</b> — total minutes played at Reserves grade, combined across every team.</li>
<li><b>U18 minutes (all teams)</b> — total minutes played at Under-18s grade, combined across every team.</li>
<li><b>Senior appearances</b> — total appearances at Senior grade across every team.</li>
<li><b>Teams played for</b> — the number of distinct teams the player turned out for this season (more than one usually means they were borrowed, moved clubs, or play across multiple grades).</li>
<li><b>Borrowed appearances (all teams)</b> — total appearances flagged as "borrowed," combined across every team.</li>
<li><b>Age</b> — the player's age as recorded on their DRIBL member profile at the time the data was extracted.</li>
<li><b>Height (cm)</b> — player height, where available from Sofascore.</li>
<li><b>Grades played</b> — every grade (Seniors, Reserves, U18s) the player appeared in at all this season.</li>
<li><b>Highest grade</b> — the most senior grade the player appeared in this season.</li>
</ul>
</div>

## Match & ladder basics

<div class="card">
<p class="muted">Simple, self-explanatory fields that appear on the match-by-match list and the team ladders.</p>
<ul>
<li><b>Date</b> — the match's kick-off date, in Adelaide local time.</li>
<li><b>Round</b> — the round label for that match (e.g. "R5").</li>
<li><b>Opponent</b> — the team played against.</li>
<li><b>H/A</b> — whether the match was played at home or away.</li>
<li><b>Result</b> — win, draw, or loss for the player's team.</li>
<li><b>Score</b> — the full-time score, home team first.</li>
<li><b>Team goals / Team conceded</b> — how many goals the player's team scored and conceded in that specific match.</li>
<li><b>Started</b> — whether the player started that particular match, rather than coming off the bench.</li>
<li><b>Played</b>, <b>Won</b>, <b>Drawn</b>, <b>Lost</b> — a team's regular-season match count and results, as shown on the ladder.</li>
<li><b>Goals for</b> / <b>Goals against</b> — total goals a team has scored and conceded across the season.</li>
<li><b>Goal difference</b> — goals for minus goals against, the classic ladder tiebreaker.</li>
<li><b>Points</b> — ladder points (typically 3 for a win, 1 for a draw, 0 for a loss).</li>
<li><b>Ladder position</b> — the team's rank in its league.</li>
</ul>
</div>

## Scouting flags & shortlist scoring

<div class="card">
<p class="muted">These are this site's own derived tags and scores, not raw match data — they exist to help surface interesting players. Full methodology is on the <a href="./about">About the data</a> page; this is the short version.</p>
<ul>
<li><b>Hidden gem 💎</b> — a Reserves or U18 player who has played zero senior minutes all season, flagged so strong junior/reserve performers who haven't been given a senior look don't get overlooked.</li>
<li><b>Emerging senior ⚡</b> — an Under-21 player who's already performing well at Senior NPL level (Sofascore rating of 7.0+, or a combined xG+xA per 90 of 0.40+) — young players punching above their grade.</li>
<li><b>Undervalued performer 🎯</b> — a player on a bottom-half NPL team (with at least 450 minutes played) who still posts strong underlying numbers — 60%+ duel win rate or 80%+ pass accuracy — despite their team's results, i.e. a good player whose output might be masked by a struggling team around them.</li>
<li><b>Gem score</b> — the shortlist's overall ranking score: a blend of performance metrics with bonus weighting added for the "no senior minutes" and "U18" flags above, so promising unproven players rank alongside established performers rather than being buried under raw stat totals. Hover or tap a gem score in the shortlist to see exactly which factors contributed for that player.</li>
<li><b>Market value (€)</b> — an estimated transfer/market value in Euros, sourced from Sofascore, shown only where Sofascore provides one.</li>
<li><b>Borrowed</b> — DRIBL's own flag that this player was borrowed from their usual team for this specific match (see "Borrowed appearances" above).</li>
</ul>
</div>

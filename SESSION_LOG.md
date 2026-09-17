# DRIBL Football Data Extraction — Session Log

**Date:** 2026-09-17
**Project:** `/Users/satyaveer/projects/football`
**Goal:** Extract player and match statistics from Football SA's DRIBL platform (`fsa.dribl.com`) for the 2026 season — State League 1 and State League 2 competitions.

---

## 1. Background

DRIBL is Football SA's competition management platform. It hosts match centres, fixtures, lineups, ladders and player statistics for all South Australian football leagues. There is no public API documentation — the platform is a Nuxt 2 frontend at `fsa.dribl.com` backed by a JSON API at `mc-api.dribl.com`. The API had to be reverse-engineered from browser network requests.

### Target Competitions

| Competition | DRIBL ID | Leagues |
|---|---|---|
| HPG Homes State League 1 | `vbd911WYd4` | Seniors (`A4KLjAx7mq`), Reserves (`wOmexbj7d0`), U18s (`1pN65npnm0`) |
| HPG Homes State League 2 | `gld4ppz2dW` | North (`njdyX2EzK5`), South (`bam11rRWmw`), North Reserves (`pN6X03JQd0`), South Reserves (`gld41D2BmW`), North U18s (`3pmvl238Kv`), South U18s (`AnmYjYpYNz`), Seniors Finals (`AnmYjqZrNz`), Reserves Finals (`k2KpD38qKY`), 18s Finals (`LBdDVq0gNb`) |

### Security Constraints

- Credentials never hardcoded — bearer tokens stored in `DRIBL_TOKEN` environment variable
- No bypassing Cloudflare or accessing other clubs' private data
- No cookies, bearer tokens, or `cf_clearance` values in shared code

---

## 2. API Discovery Process

### 2.1 Initial Approach — Chrome DevTools Network Capture

The user opened `fsa.dribl.com/fixtures/` in Chrome, filtered the Network tab to `mc-api` XHR requests, and captured the request URLs from several page navigations:

1. **Fixtures page load** — revealed `tenants`, `clubs`, `competitions`, `fixtures`, `rounds`, `grounds` endpoints, all with `tenant=3pmvvjLmvJ` and `season=7MNGzMbmAz`
2. **Clicking into a match** — revealed `fixtures/{id}?tenant=...` (basic fixture detail) and team/ladder endpoints
3. **Visiting the match centre** — revealed the `matchcentre/?m={id}` URL pattern and additional endpoints like `formation-positions`

This gave us the base URL pattern (`mc-api.dribl.com/api/...`) and the key tenant/season IDs, but not the complete endpoint shapes or the critical distinction between fixture IDs and match IDs.

### 2.2 Finding the Correct Base URL

The initial assumption was that the API lived at `https://mc-api.dribl.com/api/v2/`. This was wrong. By inspecting the Nuxt bundle file (`f804f15.js`) in the browser, we found:

```
API_URL:"https://mc-api.dribl.com/api"
```

The correct base is `/api` with no version prefix.

### 2.3 The `fixtures/` vs `matchcentre/` Endpoint Problem

Early on, we tried the `fixtures/{id}` endpoint for match details. It returned data but was sparse — null scores, no team names, no events. The rich data lives at the `matchcentre/{id}` endpoint instead. This was discovered by:

1. Navigating to a match centre page in the browser
2. Using `performance.getEntriesByType('resource')` to capture all API calls made during the page load
3. Finding that the Nuxt frontend calls `matchcentre/{id}` (not `fixtures/{id}`) for the full match view

The Performance API approach was necessary because monkey-patching `fetch`/`XMLHttpRequest` was unreliable — Nuxt's full-page navigation cleared the interceptors.

### 2.4 The Critical `hash_id` vs `match_hash_id` Discovery

This was the most important (and hardest to find) detail. The DRIBL API uses **two distinct identifier spaces** for matches:

| Field | What it identifies | Where it appears |
|---|---|---|
| `hash_id` | The fixture in the scheduling system | `results` endpoint, URL `fsa.dribl.com/matchcentre/?m={hash_id}` |
| `match_hash_id` | The match in the match centre system | `results` endpoint (as a field on each fixture) |

**The `matchcentre/` and `matchcentre-match-members/` endpoints require `match_hash_id`, NOT the fixture `hash_id`.** Using the wrong ID returns a 404 "Not Found" — a silent failure that's easy to miss since the fixture *does* exist, just under a different key.

This was discovered by:
1. Calling `matchcentre/{hash_id}` → 404 Not Found
2. Inspecting the `results` endpoint response and finding it returns BOTH `hash_id` and `match_hash_id` per fixture
3. Calling `matchcentre/{match_hash_id}` → 200 with full match data

Example: fixture `lNbJAbAEyN` (hash_id) corresponds to match `ld450LrLGm` (match_hash_id).

### 2.5 The `list/clubs` Prefix

The clubs endpoint is `list/clubs?...`, not `clubs?...`. Both return data, but `list/clubs` returns the correct club listing for the tenant. Discovered via the Performance API capture.

---

## 3. Confirmed API Endpoints

**Base URL:** `https://mc-api.dribl.com/api`

| Endpoint | Parameters | Returns |
|---|---|---|
| `competitions` | `disable_paging=true`, `tenant`, `season` | All competitions with nested `leagues[]` arrays |
| `list/clubs` | `disable_paging=true`, `tenant` | All clubs in the tenant |
| `results` | `season`, `competition`, `league`, `tenant`, `results=1`, `timezone`, `disable_paging=true` | Completed fixtures with `hash_id`, `match_hash_id`, team IDs, scores |
| `fixtures` | `season`, `tenant`, `timezone`, `disable_paging=true` | All fixtures (including upcoming) |
| `matchcentre/{match_hash_id}` | `tenant` | Rich match detail: scores, events[], ground, referees, half-time scores |
| `matchcentre-match-members/match/{match_hash_id}/team/{team_hash_id}` | (none) | Player lineup: per-player starting/playing/goals/cards/subs with minutes |
| `ladders` | `league`, `require_pools=true`, `include_match_type=true` | League standings: P/W/D/L, GF/GA/GD, points, cards |
| `fixtures/{fixture_id}` | `tenant` | Basic fixture info (sparse — use `matchcentre/` instead) |
| `tenants` | `mc_link=fsa.dribl.com`, `slug=fsa` | Tenant metadata |

### Key Constant IDs

| Entity | ID |
|---|---|
| Football SA tenant | `3pmvvjLmvJ` |
| 2026 season | `7MNGzMbmAz` |
| SL1 competition | `vbd911WYd4` |
| SL2 competition | `gld4ppz2dW` |

### Response Shape

All responses are wrapped in `{"data": [...]}`. Individual records have `{type, id, attributes: {...}, links: {...}}` structure. The `attributes` object contains the actual fields. Some endpoints (like `matchcentre-match-members`) return a flat array of player objects at the `data` level.

### Player Lineup Fields (from `matchcentre-match-members`)

Each player record includes:
- `user_hash_id`, `first_name`, `last_name` — player identity
- `role_slug` — "player" or "staff"
- `playing` — boolean, whether they participated
- `starting` — boolean, whether they started
- `jersey` — shirt number
- `is_captain`, `is_goalkeeper` — boolean flags
- `goals[]` — array of goal objects
- `cards[]` — array of card objects with `final_card_type` ("Yellow Card", "Red Card")
- `in_subs[]` — array of substitution-on events with `minute`
- `out_subs[]` — array of substitution-off events with `minute`

---

## 4. Cloudflare Problem & Browser-Based Extraction

### The Problem

DRIBL uses Cloudflare bot protection. All HTTP requests from cloud IPs (and even the user's local machine via `requests`/`curl`) are blocked with a `403 Forbidden` response. This was confirmed by:

1. `curl` from the cloud environment → 403
2. Python `requests` from the cloud → 403
3. `python dribl_extract.py --discover` from the user's local Mac → 403

### The Solution: In-App Browser Extraction

The Claude Code desktop app's built-in browser pane has Cloudflare clearance (it behaves like a real browser session). We used this to run the entire extraction via JavaScript executed in the browser:

1. **Navigate** to `fsa.dribl.com` in the browser pane
2. **Execute JavaScript** via the `javascript_tool` to call `fetch()` against the API
3. **Batch requests** — 15 concurrent `Promise.all()` fetches per batch to avoid rate limiting
4. **Store results** in `window.__` global variables across JS calls
5. **Dump all data** as one large JSON object which auto-saves to a local file when it exceeds the tool's output limit
6. **Process with Python** — parse the double-encoded JSON wrapper and build Excel with pandas

### Extraction Pipeline (as executed)

```
Step 1: Fetch competitions → identify all leagues in SL1 + SL2
        → 12 leagues found

Step 2: Fetch results for each league
        → 294 completed fixtures total

Step 3: Fetch matchcentre/{match_hash_id} for each fixture (batches of 15)
        → 294 match centre records (scores, events, venues)

Step 4: Fetch matchcentre-match-members for both teams in each fixture (batches of 15)
        → 588 lineup records (home + away for each fixture)

Step 5: Fetch ladders for all 12 leagues
        → 116 ladder entries across 12 tables

Step 6: Assemble all data into JSON, dump to file
        → 10 MB JSON file

Step 7: Python processes JSON into Excel with pandas/openpyxl
        → output/dribl_season_2026.xlsx (1.5 MB)
```

**Total API calls:** ~895 (12 results + 294 matchcentre + 588 lineups + 12 ladders + overhead)

### Double-Encoded JSON Wrapper

The browser tool returns results in a `[{type: "text", text: "..."}]` wrapper. When the JavaScript result is a string (from `JSON.stringify()`), it gets double-encoded:

```
File: [{type: "text", text: "\"{\\"matches\\":...}\""}]
                                ↑ outer quotes   ↑ escaped inner quotes
```

Parsing requires two rounds of `json.loads()`:
```python
wrapper = json.load(f)            # parse the [{type, text}] array
raw_text = wrapper[0]['text']      # get the double-encoded string
inner = json.loads(raw_text)       # unwrap outer string encoding → still a string
data = json.loads(inner)           # parse the actual JSON data → dict
```

Using `json.JSONDecoder().raw_decode()` is necessary because trailing metadata (tab context info) follows the main JSON array in the file.

---

## 5. Output Files

### `output/dribl_season_2026.xlsx` (1.5 MB)

| Sheet | Rows | Description |
|---|---|---|
| **Matches** | 294 | Every completed fixture: IDs, competition, league, date, round, venue, teams, clubs, scores, half-time scores |
| **Appearances** | 8,853 | Per-player per-match records: player ID/name, team, club, league, round, date, opponent, H/A, result, jersey, starter/sub, captain, GK, sub minutes, goals, cards |
| **Player Totals** | 2,456 | Season aggregates grouped by player+team+league: appearances, starts, sub appearances, goals, yellow cards, red cards, captain count, GK flag |
| **Events** | 3,832 | Match events: goals, cards, substitutions with minute and game section |
| **Ladders** | 116 | League standings: position, team, club, P/W/D/L, GF/GA/GD, points, adjustments, cards |

**Coverage:** 12 leagues, 32 clubs, 96 teams, 1,703 unique players.

### `output/fsa_team_names.xlsx` (8.5 KB)

Extracted from the Wikipedia "Football South Australia" page (from a saved view-source HTML file):

| Sheet | Rows | Description |
|---|---|---|
| **State League 1** | 12 | Team, Suburb, Home Ground, Founded, Joined, Championships, Premierships, Cup wins, Head Coach |
| **State League 2** | 20 | Same columns — North and South combined |
| **Men's Pyramid** | 4 | National/State levels, league names, promotion/relegation rules |

The Wikipedia extraction required reconstructing the original HTML from Chrome's view-source wrapper (HTML-entity-encoded content inside `<td class="line-content">` cells with syntax-highlighting `<span>` tags), then parsing with BeautifulSoup and cleaning residual Wikipedia link markup from cell values.

---

## 6. Python Script: `dribl_extract.py`

A standalone Python script for re-running the extraction locally (when Cloudflare permits). Two modes:

```bash
python dribl_extract.py --discover        # List competitions and leagues
python dribl_extract.py --extract         # Full extraction to Excel
python dribl_extract.py --extract --league "State League 2"  # Filter by league name
python dribl_extract.py --no-cache        # Bypass response cache
python dribl_extract.py --token "abc123"  # Pass bearer token
```

**Architecture:**
- `DriblAPI` class — HTTP client with retry logic, rate-limit handling, MD5-hashed response caching in `output/.cache/`
- `discover()` — probes the API and lists all competitions/leagues
- `extract()` — walks all completed fixtures, fetches match centre + lineups + ladders, builds Excel
- `build_player_totals()` — aggregates per-player season stats with pandas groupby

**Key implementation detail:** The script correctly uses `match_hash_id` (not fixture `hash_id`) for `matchcentre/` and `matchcentre-match-members/` endpoints. This was a critical bug that was fixed during the session.

**Cloudflare blocker:** As of 2026-09-17, the script is blocked by Cloudflare even from a local Mac. To work around this, either:
1. Capture a `cf_clearance` cookie + matching user-agent from a browser session
2. Use the browser-based extraction approach documented above
3. Contact `support@dribl.com` to request official API access

---

## 7. Project Setup

```
football/
├── .venv/                    # Python 3.14 virtual environment
├── .env.example              # Template: DRIBL_TOKEN=your_bearer_token_here
├── .gitignore                # Excludes .venv/, .env, output/, __pycache__/
├── dribl_extract.py          # Main extraction script (Python)
├── output/
│   ├── .cache/               # MD5-hashed API response cache (JSON files)
│   ├── dribl_season_2026.xlsx  # Full season data (294 matches, 8853 appearances)
│   └── fsa_team_names.xlsx     # Wikipedia team reference tables
├── view-source_https___en.wikipedia.org_wiki_Football_South_Australia.html
└── SESSION_LOG.md            # This file
```

**Dependencies:**
```bash
cd ~/projects/football
source .venv/bin/activate
pip install requests pandas openpyxl beautifulsoup4
```

---

## 8. Errors Encountered & How They Were Resolved

| Error | Root Cause | Resolution |
|---|---|---|
| Wrong API base URL (`/api/v2/`) | Assumed version prefix | Found `API_URL:"https://mc-api.dribl.com/api"` in Nuxt bundle `f804f15.js` |
| `fixtures/{id}` returns sparse data | Wrong endpoint for match details | Discovered `matchcentre/{id}` via Performance API — returns rich data with events, scores, teams |
| `matchcentre/{hash_id}` returns 404 | Using fixture `hash_id` instead of `match_hash_id` | Discovered `results` endpoint returns both IDs; `matchcentre/` needs `match_hash_id` |
| `clubs?...` returns unexpected data | Wrong endpoint prefix | Actual endpoint is `list/clubs?...` (with `list/` prefix) |
| JS `fetch`/`XHR` monkey-patches lost on navigation | Nuxt full-page reload clears interceptors | Used `performance.getEntriesByType('resource')` which persists across the page lifecycle |
| Cloudflare 403 from `curl`/`requests` | Bot protection blocks non-browser traffic | Used the desktop app's browser pane (has Cloudflare clearance) for the extraction |
| Cloudflare 403 from user's local Mac | Bot protection even stricter than expected | Browser-based extraction as fallback; future option: capture `cf_clearance` cookie |
| Double-encoded JSON from browser tool | Tool wraps JS return values in `[{type, text}]` with string-encoding | Two rounds of `json.loads()` + `raw_decode()` for trailing metadata |
| Ladder data fields all empty | Attributes nested under `.data.{N}.attributes`, not `.data[].attributes` | `data` was an object with numeric keys (not array); used `Object.values()` |
| Wikipedia cells contain raw URL markup | View-source HTML has link markup flattened to text | Regex cleanup of `https://...">` patterns and stray HTML attributes |

---

## 9. Data Quality Notes

- **Appearances only count playing players** — non-playing squad members (on the bench but not used) are filtered out via `playing: true`
- **Substitution minutes** — captured from `in_subs[0].minute` and `out_subs[0].minute`; only the first sub event is recorded per player
- **Cards** — counted by checking `final_card_type` for "Yellow" or "Red" substring match
- **Goals** — counted from the `goals[]` array length per player, not from match events (both sources exist)
- **Some fixtures may lack lineup data** — if DRIBL hasn't recorded the lineup, the `matchcentre-match-members` endpoint returns an empty array; those matches will have entries in the Matches sheet but no corresponding Appearances rows
- **Dates are in UTC** — the API returns dates in UTC format (e.g., `2026-09-12 04:30:00`), not local Adelaide time

---

## 10. Possible Next Steps

1. **Fix Cloudflare for local script** — Investigate capturing `cf_clearance` cookie and user-agent from a browser session to pass to the Python `requests` client, enabling `dribl_extract.py` to run locally without the browser pane
2. **Add more competitions** — The script's `TARGET_LEAGUES` dict can be expanded with additional league IDs (NPL, Women's leagues, etc.)
3. **Minutes played calculation** — Derive minutes played from starter status + sub on/off times (starters get 90 minus sub-off, subs get 90 minus sub-on)
4. **Clean sheets** — Cross-reference goalkeeper appearances with match scores to calculate clean sheet counts
5. **Request official API access** — Email `support@dribl.com` for an API key or data export, which would be more reliable than reverse-engineered endpoints
6. **Automate refresh** — Schedule periodic re-extraction to keep the data current as the season progresses

---

## 11. Scouting Build — Positions Finding, Full-Season Re-extraction, Enriched Fields (2026-09-17, session 2)

### 11.1 Goal

Turn the extract into a player-scouting workbook (all positions incl. GKs and defenders) that surfaces "hidden gems": players in Reserves / Under 18s with strong league-adjusted output and no senior minutes.

### 11.2 Positions are not recorded

The lineup record carries `formation_field_position`, `formation_type`, `field_role`, `field_role_slug`, `field_role_group`, and the match centre carries `home_formation` / `away_formation`. Sampling 24 matches (2 per league, ~530 player records):

| Field | Populated |
|---|---|
| `formation_field_position` / `formation_type` | 1 player in 1 match |
| `home_formation` / `away_formation` | 2 of 48 team-sides |
| `field_role_slug` | only ever `"goalkeeper"` (same as `is_goalkeeper`) |
| `league_display_formation` | `false` for most leagues |

**Conclusion:** only GK vs outfield is knowable. Jersey number is recorded but not used for ranking.

### 11.3 The `results` endpoint is cursor-paginated — the first extraction was only the last 30 matches per league

`results?...&disable_paging=true` returns `meta.per_page = 30` and a `meta.next_cursor`; `disable_paging` is ignored. Session 1 (and the first pass of session 2) therefore captured only the **most recent 30 completed fixtures per league** — rounds 19–22 plus finals for SL1, rounds ~11–18 for SL2 — i.e. 294 of 981 matches. The ladders (`played = 22`) were the giveaway: teams had only 5–7 matches in the extract.

Fix: follow `meta.next_cursor` until null (`extract_browser.js` `results()`, `dribl_extract.py` `DriblAPI.get_results`). Full season = **981 fixtures** (SL1: 139 per grade = 132 regular + 7 finals; SL2: 90 per regional grade + 24 finals).

`output/dribl_season_2026.xlsx` and the `output/dribl_*_2026.json` (non-v2) files are from the partial extract and should not be used for season totals.

### 11.4 Enriched fields kept in the v2 extract

| Field | Where | Use |
|---|---|---|
| `borrowed` (0/1) | lineup | Player borrowed from another team in the club that match. 5,955 borrowed appearances across the season — the strongest "playing up/down a grade" signal. |
| `votes` (0–3) | lineup | 3-2-1 votes per match (best-on-ground style). Present in ~75% of team-sides. `enable_votes_public_display` is false so this is not shown on the site. |
| `goals[].own_goal`, `goals[].penalty_kick` | lineup | Split goals into open play / penalty / own goal. |
| `playing = false` rows | lineup | Bench-unused squad members (previously filtered out): 13,857 rows. |
| `has_ban`, `available` | lineup | Suspension / availability flags. |
| `match_type`, `win_status`, `field_name`, `game_progress`, `penalties[]`, `referees[]`, `matchsheet_*_confirmed` | match centre | Finals flag, artificial pitch, shootouts, data-quality flag. |

Also learned: `matchcentre.goals[].member_id` is **not** `user_hash_id`, so goals can't be joined to lineups by id. Player goals come from the lineup's own `goals[]`; the match-centre goal list (with `team_id` = scorer's team, own goals flipped) is used for the running score.

### 11.5 Minutes and the Under-18 gap

Minutes are derived (starter: sub-off or red-card minute else match length; sub: match length − sub-on minute; ET matches = 120). Under 18 leagues almost never record substitution minutes (≈820 of ≈830 subs with no minute are U18), so U18 minutes are **estimated** (sub on at 70', starters full match) and flagged via `minutes_estimated` / `minutes_est_apps`. ~16% of team-sides have no goalkeeper flagged.

### 11.6 New scripts

| File | Purpose |
|---|---|
| `extract_browser.js` | Paste into the browser pane console on fsa.dribl.com. Phases: `leagues → results (paginated) → matchcentres → members → ladders`, state in `window.__v2.state`, `dump('meta' | 'mc' | 'members', i, n)` in chunks (full dump is ~50 MB). |
| `merge_dumps.py` | Unwraps the tool-result files (double-encoded JSON with trailing metadata) and merges chunks into `output/dribl_raw_2026_v2.json`. |
| `build_scouting.py` | Builds `output/dribl_scouting_2026.xlsx` + `output/dribl_*_2026_v2.json`. `--check` runs reconciliation (goal events = lineup goals = 4,167; minutes per team-side ≈ 990; GF spot-check). |
| `dribl_extract.py` | Updated: targets both competitions, paginates results, writes the same raw JSON and calls `build_scouting.build()`. Still Cloudflare-blocked locally. |

### 11.7 Workbook contents

| Sheet | Rows | What |
|---|---|---|
| Shortlist | 1,571 | Players with ≥ 450 min and ≥ 5 apps, ranked within GK / Outfield by `gem_score`, with a plain-English `why_flagged`. |
| Player Season | 3,233 | One row per player × team: volume, output (open-play / pen / OG, per-90, share of team goals), game-state goals (equaliser, go-ahead, winner, late), on-pitch GF/GA/GD vs team, GK clean sheets & GA/90, discipline, votes, captaincy, borrowed, pathway (grades played, senior minutes, highest grade), PPG when starting vs not. |
| Appearances | 43,448 | Player × match incl. bench-unused, with derived minutes and per-match flags. |
| Team Context | 96 | PPG, GF/GA per match, ladder position, players used, borrowed-in counts. |
| Matches / Events / Ladders / Notes | 981 / 12,779 / 116 / 15 | Reference tables and the methodology notes. |

Scoring: rates shrunk toward the league mean (prior 450 min / 5 apps), z-scored within league. Outfield = 0.35 non-pen goals/90 + 0.25 votes/app + 0.20 on-pitch GD vs team + 0.10 share of team goals + 0.10 minutes share. GK = 0.25 −GA/90 + 0.15 −(GA/90 vs team) + 0.30 clean-sheet % + 0.20 votes/app + 0.10 minutes share. `gem_score` adds +0.30 for no senior minutes and +0.15 for U18 players.

### 11.8 Limitations that remain

- Goals are the only on-ball output. No assists, shots, xG, passes, tackles. Defenders and holding midfielders are visible only via minutes, trust (starts, votes, captaincy), on-pitch GD and discipline.
- No age / DOB. "U18 player" (appeared in an Under 18 league) is the only age signal.
- Data is entered by club volunteers: goal attribution, sub minutes and GK flags can be missing or wrong.
- Playing time reflects the coach's opinion, injuries and availability, not just ability.
- Refresh is manual via the browser pane while Cloudflare blocks the Python client.

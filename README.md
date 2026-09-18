# SA State League Scouting 2026

Player and team statistics for Football SA's **HPG Homes State League 1 and 2** (Seniors, Reserves, Under 18s and finals), extracted from the DRIBL match centre and turned into a scouting workbook and an interactive site.

**Live site:** https://satpat.github.io/football-scouting/

New here? [ARCHITECTURE.md](ARCHITECTURE.md) explains how the pieces fit, what is generated, and how to ship a change.

## What is here

| Path | Purpose |
|---|---|
| `extract_browser.js` | Extraction script. DRIBL sits behind Cloudflare, so this runs inside a real browser tab on `fsa.dribl.com` (paste into the console; phases documented at the top of the file). Follows the cursor-paginated `results` endpoint and dumps match centres + lineups in chunks. |
| `extract_profiles.js` | Second browser script: member profiles (age, nationality, headshot, club colours), per-season careers and every match incl. cups for each player. |
| `merge_dumps.py` | Merges the chunked dumps into `output/dribl_raw_2026_v2.json` (and `-o output/dribl_profiles_2026.json` for the profile parts). |
| `download_crests.py` | Downloads the 32 club crests into `site/src/assets/crests/` and generates `site/src/components/crests.js`. |
| `build_scouting.py` | Builds every derived table (minutes, per-90 rates, game-state goals, on-pitch goal difference, clean sheets, votes, pathway, league-adjusted shortlist) → `output/dribl_scouting_2026.xlsx` and split JSON. `--check` runs reconciliation. |
| `build_site_data.py` | Exports compact CSV/JSON for the site into `site/src/data/`, including `labels.json` (friendly column names) — the only place column labels are defined. |
| `dribl_extract.py` | Local-Python equivalent of the browser extraction (currently blocked by Cloudflare). |
| `site/` | [Observable Framework](https://observablehq.com/framework/) project: Explorer (any-metric scatter with league/grade toggles and a SQL-backed match-by-match view), Shortlist, Player profile (FotMob-style, `player?id=…`), Teams & ladders, Ask the data (natural-language chat), About. |
| `chat-worker/` | Stateless Cloudflare Worker behind the **Ask the data** page: holds the OpenAI key, turns questions into DuckDB SQL. Deploys to Cloudflare, not Pages — see [chat-worker/README.md](chat-worker/README.md). |
| `SESSION_LOG.md` | Full working notes: API discovery, the `hash_id`/`match_hash_id` trap, pagination, what DRIBL does and doesn't record. |

`output/` (raw dumps, workbook) is git-ignored; only the small site data files are committed.

## Refresh the data

```bash
# 1. In a browser tab on https://fsa.dribl.com, paste extract_browser.js and run the phases,
#    then save each __v2.dump(...) result to a file. Do the same with extract_profiles.js
#    (set window.__p.ids to the unique player_id values from site/src/data/players.csv).
# 2. Merge, build, export:
source .venv/bin/activate
python merge_dumps.py <match dump files...>
python merge_dumps.py <profile dump files...> -o output/dribl_profiles_2026.json
python build_scouting.py --check
python download_crests.py
python build_site_data.py
# 3. Commit site/src/data and push — GitHub Actions rebuilds the site.
```

Python deps: `pip install pandas openpyxl requests pyarrow fonttools brotli`.

`fonttools`/`brotli` are only needed by `build_fonts.py`, which regenerates the subsetted
Aptos webfont in `site/src/fonts.css` from a local Microsoft Office install. The generated
file is committed, so you only need this if the headings font changes:

```bash
source .venv/bin/activate
python build_fonts.py
```

## Run the site locally

```bash
cd site && npm install && npm run dev
```

The **Ask the data** page also needs the chat Worker, in a second terminal:

```bash
cd chat-worker && npm install && npm run dev
```

Copy `chat-worker/.dev.vars.example` to `.dev.vars` first. Leaving `CHAT_MOCK="1"` in it
exercises the whole chat loop with **no OpenAI spend**; swap in a real `OPENAI_API_KEY` for
live answers. The page picks its endpoint by hostname, so no configuration is needed.

## Data caveats (short version)

DRIBL records who played, minutes (via subs), goals with penalty/own-goal flags, cards, captain/GK flags, a "borrowed from another team" flag and 3-2-1 votes. Member profiles add age, nationality and a season-by-season career. It records **no** assists, shots or positions. Under 18 leagues rarely record sub minutes, so U18 minutes are estimated and flagged. Everything is entered by club volunteers. See the site's *About* page.

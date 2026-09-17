# SA State League Scouting 2026

Player and team statistics for Football SA's **HPG Homes State League 1 and 2** (Seniors, Reserves, Under 18s and finals), extracted from the DRIBL match centre and turned into a scouting workbook and an interactive site.

**Live site:** https://satpat.github.io/football-scouting/

## What is here

| Path | Purpose |
|---|---|
| `extract_browser.js` | Extraction script. DRIBL sits behind Cloudflare, so this runs inside a real browser tab on `fsa.dribl.com` (paste into the console; phases documented at the top of the file). Follows the cursor-paginated `results` endpoint and dumps match centres + lineups in chunks. |
| `merge_dumps.py` | Merges the chunked dumps into `output/dribl_raw_2026_v2.json`. |
| `build_scouting.py` | Builds every derived table (minutes, per-90 rates, game-state goals, on-pitch goal difference, clean sheets, votes, pathway, league-adjusted shortlist) → `output/dribl_scouting_2026.xlsx` and split JSON. `--check` runs reconciliation. |
| `build_site_data.py` | Exports compact CSV/JSON for the site into `site/src/data/`, including `labels.json` (friendly column names) — the only place column labels are defined. |
| `dribl_extract.py` | Local-Python equivalent of the browser extraction (currently blocked by Cloudflare). |
| `site/` | [Observable Framework](https://observablehq.com/framework/) project: Explorer (any-metric scatter with league/grade toggles and a SQL-backed match-by-match view), Shortlist, Teams & ladders, About. |
| `SESSION_LOG.md` | Full working notes: API discovery, the `hash_id`/`match_hash_id` trap, pagination, what DRIBL does and doesn't record. |

`output/` (raw dumps, workbook) is git-ignored; only the small site data files are committed.

## Refresh the data

```bash
# 1. In a browser tab on https://fsa.dribl.com, paste extract_browser.js and run the phases,
#    then save each __v2.dump(...) result to a file.
# 2. Merge, build, export:
source .venv/bin/activate
python merge_dumps.py <dump files...>
python build_scouting.py --check
python build_site_data.py
# 3. Commit site/src/data and push — GitHub Actions rebuilds the site.
```

Python deps: `pip install pandas openpyxl requests`.

## Run the site locally

```bash
cd site && npm install && npm run dev
```

## Data caveats (short version)

DRIBL records who played, minutes (via subs), goals with penalty/own-goal flags, cards, captain/GK flags, a "borrowed from another team" flag and 3-2-1 votes. It records **no** assists, shots, positions or ages. Under 18 leagues rarely record sub minutes, so U18 minutes are estimated and flagged. Everything is entered by club volunteers. See the site's *About* page.

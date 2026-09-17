#!/usr/bin/env python3
"""
DRIBL Football Data Extractor for Football SA

Extracts player and match statistics from the DRIBL Match Centre API
for State League 1 and State League 2 (all grades, 2026 season).

Usage:
    python dribl_extract.py --discover        # Probe API and show competitions/leagues
    python dribl_extract.py --extract         # Full extraction -> output/dribl_raw_2026_v2.json + scouting workbook
    python dribl_extract.py --extract --league "Reserves"  # Only leagues whose name contains this

The extraction writes the same raw JSON structure as extract_browser.js, then hands it to
build_scouting.build() for the workbook. NB: as of 2026-09-17 Cloudflare blocks this script
(403); use extract_browser.js in the desktop app's browser pane instead, then merge_dumps.py.

Requires: requests, pandas, openpyxl
    pip install requests pandas openpyxl
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# DRIBL API constants — discovered from Chrome DevTools + Performance API
# ---------------------------------------------------------------------------
BASE_URL = "https://mc-api.dribl.com/api"
TENANT_ID = "3pmvvjLmvJ"   # Football SA
SEASON_ID = "7MNGzMbmAz"   # 2026 season
TIMEZONE = "Australia/Adelaide"

# Target competitions: every league inside these is extracted (use --league to narrow further)
TARGET_COMPETITIONS = {
    "vbd911WYd4": "HPG Homes State League 1",
    "gld4ppz2dW": "HPG Homes State League 2",
}

OUTPUT_DIR = Path("output")
CACHE_DIR = Path("output/.cache")

MAX_RETRIES = 3
RETRY_DELAY = 2
REQUEST_DELAY = 0.4


class DriblAPI:
    """Client for the DRIBL Match Centre API."""

    def __init__(self, token=None, use_cache=True):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Origin": "https://fsa.dribl.com",
            "Referer": "https://fsa.dribl.com/",
        })
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        self.use_cache = use_cache
        if use_cache:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, endpoint, params):
        import hashlib
        raw = f"{endpoint}|{json.dumps(params, sort_keys=True)}"
        return CACHE_DIR / (hashlib.md5(raw.encode()).hexdigest() + ".json")

    def get(self, endpoint, params=None, label=None):
        params = params or {}
        cache_file = self._cache_path(endpoint, params)

        if self.use_cache and cache_file.exists():
            return json.loads(cache_file.read_text())

        url = f"{BASE_URL}/{endpoint}"
        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self.session.get(url, params=params, timeout=30)
                if resp.status_code == 429:
                    wait = int(resp.headers.get("Retry-After", RETRY_DELAY * attempt))
                    print(f"  Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                if self.use_cache:
                    cache_file.write_text(json.dumps(data, indent=2))
                time.sleep(REQUEST_DELAY)
                return data
            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)

        tag = label or endpoint
        print(f"  ERROR fetching {tag}: {last_error}")
        return None

    # ----- Endpoint wrappers -----

    def get_competitions(self):
        return self.get("competitions", {
            "disable_paging": "true",
            "tenant": TENANT_ID,
            "season": SEASON_ID,
        }, label="competitions")

    def get_clubs(self):
        return self.get("list/clubs", {
            "disable_paging": "true",
            "tenant": TENANT_ID,
        }, label="clubs")

    def get_results(self, competition_id, league_id):
        """Fetch ALL completed fixtures for a competition/league.

        The endpoint is cursor-paginated at 30 per page and ignores disable_paging,
        so follow meta.next_cursor until it is null. Returns a flat list of records.
        """
        records, cursor, pages = [], None, 0
        while pages < 100:
            params = {
                "season": SEASON_ID,
                "competition": competition_id,
                "league": league_id,
                "tenant": TENANT_ID,
                "results": "1",
                "timezone": TIMEZONE,
            }
            if cursor:
                params["cursor"] = cursor
            body = self.get("results", params, label=f"results/{league_id}/p{pages + 1}")
            if not body:
                break
            records.extend(extract_list(body))
            cursor = (body.get("meta") or {}).get("next_cursor") if isinstance(body, dict) else None
            pages += 1
            if not cursor:
                break
        return records

    def get_fixtures(self, competition_id=None, league_id=None):
        """Fetch all fixtures (including upcoming) for a competition/league."""
        params = {
            "season": SEASON_ID,
            "tenant": TENANT_ID,
            "timezone": TIMEZONE,
            "disable_paging": "true",
        }
        if competition_id:
            params["competition"] = competition_id
        if league_id:
            params["league"] = league_id
        return self.get("fixtures", params, label="fixtures")

    def get_matchcentre(self, match_hash_id):
        """Fetch rich match detail: scores, events, referees, ground.
        NB: requires match_hash_id (not fixture hash_id) from the results endpoint."""
        return self.get(f"matchcentre/{match_hash_id}", {
            "tenant": TENANT_ID,
        }, label=f"mc/{match_hash_id}")

    def get_match_members(self, match_hash_id, team_id):
        """Fetch lineup and player stats for one team in a match.
        NB: requires match_hash_id (not fixture hash_id) from the results endpoint."""
        return self.get(
            f"matchcentre-match-members/match/{match_hash_id}/team/{team_id}",
            label=f"members/{match_hash_id}/{team_id}",
        )

    def get_ladder(self, league_id):
        return self.get("ladders", {
            "league": league_id,
            "require_pools": "true",
            "include_match_type": "true",
        }, label=f"ladder/{league_id}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_list(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        inner = data.get("data")
        if isinstance(inner, list):
            return inner
        if isinstance(inner, dict):
            nested = inner.get("data")
            if isinstance(nested, list):
                return nested
            return [inner]
    return []


def attr(record, key, default=None):
    """Get a field from either record.attributes.key or record.key."""
    if isinstance(record, dict):
        attrs = record.get("attributes", {})
        if isinstance(attrs, dict) and key in attrs:
            return attrs[key]
        return record.get(key, default)
    return default


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def discover(api):
    print("=" * 60)
    print("DRIBL API Discovery — Football SA 2026")
    print("=" * 60)

    comp_data = api.get_competitions()
    if not comp_data:
        print("\nFAILED — Cloudflare is likely blocking. Run from your home network.")
        return

    competitions = extract_list(comp_data)
    print(f"\nFound {len(competitions)} competitions:\n")

    for c in competitions:
        cid = c.get("id", c.get("hash_id", "?"))
        name = attr(c, "name", "?")
        leagues = attr(c, "leagues", [])
        if not leagues:
            continue
        print(f"[{cid}] {name}")
        for lg in leagues:
            lgid = lg.get("id", "?")
            lgname = lg.get("name", "?")
            marker = " <-- TARGET" if lgid in TARGET_LEAGUES else ""
            print(f"  [{lgid}] {lgname}{marker}")

    clubs_data = api.get_clubs()
    if clubs_data:
        clubs = extract_list(clubs_data)
        print(f"\n{len(clubs)} clubs registered")
        for c in clubs[:5]:
            print(f"  [{c.get('id')}] {attr(c, 'name')}")
        print("  ...")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "discovery.json").write_text(json.dumps(comp_data, indent=2))
    print(f"\nFull competition data saved to {OUTPUT_DIR / 'discovery.json'}")


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def extract(api, league_filter=None, raw_out=OUTPUT_DIR / "dribl_raw_2026_v2.json"):
    """Walk every completed fixture and write the raw dump in the extract_browser.js structure."""
    print("=" * 60)
    print("DRIBL Data Extraction — Football SA 2026")
    print("=" * 60)

    comp_data = api.get_competitions()
    if not comp_data:
        print("ERROR: Could not fetch competitions.")
        sys.exit(1)

    leagues = []
    for c in extract_list(comp_data):
        comp_id = c.get("hash_id", c.get("id"))
        if comp_id not in TARGET_COMPETITIONS:
            continue
        for lg in attr(c, "leagues", []):
            la = lg.get("attributes", lg)
            name = la.get("name", "")
            if league_filter and league_filter.lower() not in name.lower():
                continue
            leagues.append({"competition_id": comp_id, "competition": attr(c, "name"),
                            "league_id": lg.get("hash_id", la.get("hash_id", lg.get("id"))), "league": name})
    if not leagues:
        print("No matching leagues found.")
        sys.exit(1)
    print(f"\nTargets: {len(leagues)} league(s)")

    raw = {"extracted_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "tenant": TENANT_ID, "season": SEASON_ID,
           "leagues": leagues, "fixtures": [], "mc": {}, "members": {}, "ladders": {}, "errors": []}

    for lg in leagues:
        print(f"\n== {lg['league']}")
        for f in api.get_results(lg["competition_id"], lg["league_id"]):
            a = f.get("attributes", f)
            if a.get("status") != "complete":
                continue
            raw["fixtures"].append({**lg, "hash_id": f.get("hash_id") or a.get("hash_id") or f.get("id"),
                                    "match_hash_id": a.get("match_hash_id"), "home_team_hash_id": a.get("home_team_hash_id"),
                                    "away_team_hash_id": a.get("away_team_hash_id"), "date": a.get("date"), "name": a.get("name"),
                                    "round": a.get("round_label") or a.get("round")})
        ladder = api.get_ladder(lg["league_id"])
        if ladder:
            raw["ladders"][lg["league_id"]] = [e.get("attributes", e) for e in extract_list(ladder)]
        print(f"  {sum(1 for x in raw['fixtures'] if x['league_id'] == lg['league_id'])} completed fixtures")

    for i, f in enumerate(raw["fixtures"], 1):
        mid = f["match_hash_id"]
        if not mid:
            continue
        mc = api.get_matchcentre(mid)
        if not mc:
            raw["errors"].append({"item": mid, "error": "matchcentre"})
            continue
        a = mc.get("data", mc)
        a = a.get("attributes", a)
        for k in ("home_logo", "away_logo", "body_logo"):
            a.pop(k, None)
        raw["mc"][mid] = a
        for side in ("home", "away"):
            team = a.get(f"{side}_team_hash_id") or f.get(f"{side}_team_hash_id")
            members = api.get_match_members(mid, team) if team else None
            if members is None:
                raw["errors"].append({"item": f"{mid}:{side}", "error": "members"})
                continue
            raw["members"][f"{mid}:{side}"] = [{k: v for k, v in p.items() if k != "image"} for p in extract_list(members)]
        if i % 25 == 0:
            print(f"  {i}/{len(raw['fixtures'])} fixtures...")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_out.write_text(json.dumps(raw))
    print(f"\nRaw dump: {raw_out} ({raw_out.stat().st_size / 1e6:.1f} MB), errors: {len(raw['errors'])}")

    import build_scouting
    build_scouting.build(raw_out, check=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="DRIBL Football Data Extractor — Football SA 2026"
    )
    parser.add_argument("--discover", action="store_true",
                        help="Probe API and show available competitions/leagues")
    parser.add_argument("--extract", action="store_true",
                        help="Full extraction -> raw JSON + scouting workbook")
    parser.add_argument("--league", type=str,
                        help="Filter to leagues matching this substring")
    parser.add_argument("--no-cache", action="store_true",
                        help="Ignore cached API responses")
    parser.add_argument("--token", type=str,
                        help="Bearer token (or set DRIBL_TOKEN env var)")
    args = parser.parse_args()

    if not args.discover and not args.extract:
        parser.print_help()
        print("\nStart with:  python dribl_extract.py --discover")
        print("Then:        python dribl_extract.py --extract")
        sys.exit(0)

    token = args.token or os.environ.get("DRIBL_TOKEN")
    api = DriblAPI(token=token, use_cache=not args.no_cache)

    if args.discover:
        discover(api)
    elif args.extract:
        extract(api, league_filter=args.league)


if __name__ == "__main__":
    main()

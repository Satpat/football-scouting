#!/usr/bin/env python3
"""
Reconcile and merge Sofascore data with DRIBL data.

    python enrich_sofascore.py                          # writes output/sofascore_enriched_2026.json
    python enrich_sofascore.py --audit                  # prints reconciliation match rates

Inputs:
    output/dribl_raw_2026_v2.json      (DRIBL raw data)
    output/sofascore_raw_2026.json     (extracted by extract_sofascore.js)

Outputs:
    output/sofascore_enriched_2026.json
"""
import argparse
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

DRIBL_PATH = Path("output/dribl_raw_2026_v2.json")
SOFASCORE_PATH = Path("output/sofascore_raw_2026.json")
ENRICHED_OUT = Path("output/sofascore_enriched_2026.json")

# Tournament ID -> matching DRIBL league names to avoid cross-tier mismatch
LEAGUE_MAPPING = {
    1258: ["RAA NPL"],
    26016: ["HPG Homes State League 1"],
    32070: ["HPG Homes State League 2 North", "HPG Homes State League 2 South"],
    32103: ["HPG Homes State League 2 North - Reserves", "HPG Homes State League 2 South - Reserves"],
    27357: ["HPG Homes State League 2 South"],
    34182: ["Sportal Saturday Division Two"],
    32825: ["Sportal Saturday Premier A"],
}

# Canonical team dictionary for South Australian clubs
CANONICAL_CLUBS = {
    # NPL
    "adelaide city": "adelaide city",
    "adelaide comets": "adelaide comets",
    "adelaide united youth": "adelaide united",
    "adelaide united": "adelaide united",
    "campbelltown city": "campbelltown city",
    "croydon fc": "croydon",
    "croydon": "croydon",
    "fk beograd": "fk beograd",
    "north eastern metrostars": "metrostars",
    "metrostars": "metrostars",
    "para hills": "para hills",
    "para hills knights": "para hills",
    "playford city": "playford city",
    "playford": "playford city",
    "sturt lions": "sturt lions",
    "west adelaide sc": "west adelaide",
    "west adelaide": "west adelaide",
    "west torrens birkalla": "wt birkalla",
    "wt birkalla": "wt birkalla",
    # SL1
    "adelaide blue eagles": "adelaide blue eagles",
    "adelaide cobras": "adelaide cobras",
    "adelaide cobras fc": "adelaide cobras",
    "adelaide croatia raiders": "adelaide croatia raiders",
    "adelaide olympic": "adelaide olympic",
    "adelaide victory": "adelaide victory",
    "adelaide atletico": "adelaide victory",
    "adelaide atletico vsc": "adelaide victory",
    "the cove fc": "cove",
    "the cove": "cove",
    "cove fc": "cove",
    "cove": "cove",
    "cumberland united": "cumberland united",
    "eastern united": "eastern united",
    "fulham united": "fulham united",
    "modbury jets": "modbury jets",
    "salisbury united": "salisbury united",
    "south adelaide panthers": "south adelaide",
    "south adelaide": "south adelaide",
    # SL2 & Lower
    "adelaide hills": "adelaide hills",
    "adelaide titans": "adelaide titans",
    "adelaide titans fc": "adelaide titans",
    "adelaide university sc": "adelaide university",
    "adelaide university": "adelaide university",
    "adelaide vipers fc": "adelaide vipers",
    "adelaide vipers": "adelaide vipers",
    "angle vale": "angle vale",
    "barossa united": "barossa united",
    "elizabeth downs sc": "elizabeth downs",
    "elizabeth downs": "elizabeth downs",
    "elizabeth grove": "elizabeth grove",
    "gawler eagles fc": "gawler eagles",
    "gawler eagles": "gawler eagles",
    "ghan kilburn sc": "ghan kilburn",
    "ghan kilburn": "ghan kilburn",
    "ghan united": "ghan kilburn",
    "modbury vista": "modbury vista",
    "mt barker united soccer club": "mt barker",
    "mount barker united sc": "mt barker",
    "mt barker": "mt barker",
    "noarlunga united": "noarlunga united",
    "northern demons": "northern demons",
    "plympton fc": "plympton",
    "plympton": "plympton",
    "pontian eagles sc": "pontian eagles",
    "pontian eagles": "pontian eagles",
    "port adelaide pirates": "port adelaide",
    "port adelaide": "port adelaide",
    "salisbury inter fc": "salisbury inter",
    "salisbury international sc": "salisbury inter",
    "seaford rangers": "seaford rangers",
    "western strikers": "western strikers",
}


def normalize_text(text: Optional[str]) -> str:
    """Strip accents, lower-case, remove special characters and extra spaces."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    return " ".join(text.split())


def clean_team_name(name: Optional[str]) -> str:
    """Standardize team names across DRIBL and Sofascore."""
    t = normalize_text(name)
    if t in CANONICAL_CLUBS:
        return CANONICAL_CLUBS[t]
    # Remove league suffixes from DRIBL / Sofascore
    for suf in [
        "senior men s npl", "mens reserves npl", "senior men s sl1", "senior men s sl2",
        "mens reserves sl1", "mens reserves sl2", "senior men s", "mens reserves",
        "under 18 s", "under 18", "u18", "reserves", "reserve 2", "reserve", "fc", "sc", "knights"
    ]:
        t = re.sub(rf"\b{suf}\b", "", t)
    t = " ".join(t.split())
    return CANONICAL_CLUBS.get(t, t)


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_reconciliation(dribl_raw: dict, sofa_raw: dict, audit: bool = False):
    print("🔄 Building reconciliation between DRIBL and Sofascore...")

    sofa_events = sofa_raw.get("events", {})
    sofa_lineups = sofa_raw.get("lineups", {})
    sofa_incidents = sofa_raw.get("incidents", {})
    sofa_statistics = sofa_raw.get("statistics", {})

    print(f"  Sofascore events loaded: {len(sofa_events)}")
    print(f"  Sofascore lineups: {len(sofa_lineups)}")
    print(f"  Sofascore incidents: {len(sofa_incidents)}")

    # 1. Match DRIBL fixtures to Sofascore events (scoped by tournament league)
    dribl_fixtures = dribl_raw.get("fixtures", [])
    dribl_mc = dribl_raw.get("mc", {})
    matched_matches: Dict[str, str] = {}  # dribl_mid -> sofa_eid
    unmatched_dribl = []

    for tid, leagues in LEAGUE_MAPPING.items():
        t_events = {eid: ev for eid, ev in sofa_events.items() if ev.get("tournamentId") == tid}
        t_lookup = {}
        for eid, ev in t_events.items():
            ts = ev.get("startTimestamp")
            if not ts:
                continue
            dt_str = pd.to_datetime(ts, unit="s", utc=True).tz_convert("Australia/Adelaide").strftime("%Y-%m-%d")
            h = clean_team_name(ev.get("homeTeam", {}).get("name"))
            a = clean_team_name(ev.get("awayTeam", {}).get("name"))
            t_lookup[(dt_str, h, a)] = eid

        dribl_f = [f for f in dribl_fixtures if f.get("league") in leagues]
        for f in dribl_f:
            mid = f.get("match_hash_id")
            mc = dribl_mc.get(mid)
            if not mc or not mid:
                continue

            raw_date = mc.get("date")
            if not raw_date:
                continue
            try:
                dt_str = pd.to_datetime(raw_date, utc=True).tz_convert("Australia/Adelaide").strftime("%Y-%m-%d")
            except Exception:
                continue

            h = clean_team_name(mc.get("home_team_name") or mc.get("home_club_name"))
            a = clean_team_name(mc.get("away_team_name") or mc.get("away_club_name"))

            # Exact date match
            sofa_eid = t_lookup.get((dt_str, h, a))
            # Fallback within 2 days (rescheduled / evening time boundary)
            if not sofa_eid:
                for (s_dt, s_h, s_a), cand_id in t_lookup.items():
                    if (s_h == h or s_h in h or h in s_h) and (s_a == a or s_a in a or a in s_a):
                        if abs((pd.to_datetime(s_dt) - pd.to_datetime(dt_str)).days) <= 2:
                            sofa_eid = cand_id
                            break

            if sofa_eid:
                matched_matches[mid] = str(sofa_eid)
            else:
                if f.get("league") in ("RAA NPL", "HPG Homes State League 1"):
                    unmatched_dribl.append((f.get("league"), dt_str, h, a))

    print(f"✅ Matched {len(matched_matches)} DRIBL matches to Sofascore events.")
    if audit and unmatched_dribl:
        print(f"  Unmatched NPL/SL1 matches ({len(unmatched_dribl)}):")
        for u in unmatched_dribl[:10]:
            print(f"    - {u}")

    # 2. Match Players & Extract Statistics
    dribl_members = dribl_raw.get("members", {})  # "mid:side" -> list of member dicts
    appearance_stats = {}  # "mid:player_id" -> stats
    player_profiles = {}   # player_id -> bio/profile dict
    match_team_stats = {}  # mid -> team match stats

    matched_player_count = 0
    total_playing_appearances = 0

    for mid, sofa_eid in matched_matches.items():
        sofa_lu = sofa_lineups.get(sofa_eid)
        sofa_inc = sofa_incidents.get(sofa_eid, [])
        sofa_st = sofa_statistics.get(sofa_eid, [])

        # Process team match statistics
        if sofa_st:
            m_stat = {}
            for item_group in sofa_st:
                for group in item_group.get("groups", []):
                    for stat in group.get("statisticsItems", []):
                        k = stat.get("key")
                        hv, av = stat.get("homeValue"), stat.get("awayValue")
                        if k == "ballPossession":
                            m_stat["home_possession"] = hv
                            m_stat["away_possession"] = av
                        elif k == "expectedGoals":
                            m_stat["home_xg"] = hv
                            m_stat["away_xg"] = av
                        elif k == "totalShotsOnGoal":
                            m_stat["home_shots"] = hv
                            m_stat["away_shots"] = av
                        elif k == "shotsOnGoal":
                            m_stat["home_shots_on_target"] = hv
                            m_stat["away_shots_on_target"] = av
                        elif k == "cornerKicks":
                            m_stat["home_corners"] = hv
                            m_stat["away_corners"] = av
                        elif k == "fouls":
                            m_stat["home_fouls"] = hv
                            m_stat["away_fouls"] = av
                        elif k == "passes":
                            m_stat["home_passes"] = hv
                            m_stat["away_passes"] = av
                        elif k == "accuratePasses":
                            m_stat["home_accurate_passes"] = hv
                            m_stat["away_accurate_passes"] = av
                        elif k == "totalTackle":
                            m_stat["home_tackles"] = hv
                            m_stat["away_tackles"] = av
                        elif k == "interceptionWon":
                            m_stat["home_interceptions"] = hv
                            m_stat["away_interceptions"] = av
                        elif k == "totalClearance":
                            m_stat["home_clearances"] = hv
                            m_stat["away_clearances"] = av
                        elif k == "goalkeeperSaves":
                            m_stat["home_saves"] = hv
                            m_stat["away_saves"] = av
            match_team_stats[mid] = m_stat

        # Build assists map from incidents: sofa_player_id -> count of assists in this match
        match_assists: Dict[int, int] = {}
        for inc in sofa_inc:
            if inc.get("incidentType") == "goal":
                assist1 = inc.get("assist1")
                if assist1 and assist1.get("id"):
                    pid = assist1["id"]
                    match_assists[pid] = match_assists.get(pid, 0) + 1

        # Process lineups & players
        if sofa_lu:
            for side in ("home", "away"):
                side_players = sofa_lu.get(side, {}).get("players", [])
                dribl_side_key = f"{mid}:{side}"
                dribl_team_members = dribl_members.get(dribl_side_key, [])

                # Build lookup for Sofascore players in this match side
                sofa_side_lookup = {}
                for sp in side_players:
                    p_obj = sp.get("player", {})
                    p_name = normalize_text(p_obj.get("name"))
                    sofa_side_lookup[p_name] = sp
                    if p_obj.get("shortName"):
                        sofa_side_lookup[normalize_text(p_obj["shortName"])] = sp

                for dm in dribl_team_members:
                    mem_id = dm.get("user_hash_id") or dm.get("member_id") or dm.get("id") or dm.get("hash_id")
                    if not mem_id or dm.get("role_slug") != "player":
                        continue

                    if dm.get("playing"):
                        total_playing_appearances += 1

                    fn = dm.get("first_name", "")
                    ln = dm.get("last_name", "")
                    dm_name = normalize_text(f"{fn} {ln}".strip())
                    matched_sp = sofa_side_lookup.get(dm_name)

                    # Substring / last name fallback
                    if not matched_sp:
                        ln_norm = normalize_text(ln)
                        if ln_norm and len(ln_norm) > 2:
                            for s_name, sp in sofa_side_lookup.items():
                                if ln_norm in s_name:
                                    matched_sp = sp
                                    break

                    if matched_sp:
                        matched_player_count += 1
                        sp_player = matched_sp.get("player", {})
                        sp_stats = matched_sp.get("statistics", {})
                        sofa_pid = sp_player.get("id")

                        app_key = f"{mid}:{mem_id}"
                        n_assists = match_assists.get(sofa_pid, 0)

                        # Extract appearance-level stats
                        appearance_stats[app_key] = {
                            "sofascore_rating": sp_stats.get("rating"),
                            "assists": n_assists,
                            "xg": sp_stats.get("expectedGoals", 0.0),
                            "xa": sp_stats.get("expectedAssists", 0.0),
                            "key_passes": sp_stats.get("keyPass", 0),
                            "big_chances_created": sp_stats.get("bigChanceCreated", 0),
                            "big_chances_missed": sp_stats.get("bigChanceMissed", 0),
                            "passes_total": sp_stats.get("totalPass", 0),
                            "passes_acc": sp_stats.get("accuratePass", 0),
                            "long_balls_total": sp_stats.get("totalLongBalls", 0),
                            "long_balls_acc": sp_stats.get("accurateLongBalls", 0),
                            "crosses_total": sp_stats.get("totalCross", 0),
                            "crosses_acc": sp_stats.get("accurateCross", 0),
                            "duels_won": sp_stats.get("duelWon", 0),
                            "duels_total": (sp_stats.get("duelWon", 0) + sp_stats.get("duelLost", 0)),
                            "aerials_won": sp_stats.get("aerialWon", 0),
                            "aerials_total": (sp_stats.get("aerialWon", 0) + sp_stats.get("aerialLost", 0)),
                            "tackles": sp_stats.get("totalTackle", 0),
                            "interceptions": sp_stats.get("interceptionWon", 0),
                            "recoveries": sp_stats.get("ballRecovery", 0),
                            "clearances": sp_stats.get("totalClearance", 0),
                            "dribbles_won": sp_stats.get("wonContest", 0),
                            "dribbles_total": sp_stats.get("totalContest", 0),
                            "touches": sp_stats.get("touches", 0),
                            "dispossessed": sp_stats.get("dispossessed", 0),
                            "fouls_drawn": sp_stats.get("wasFouled", 0),
                            "fouls_committed": sp_stats.get("fouls", 0),
                            "shots_total": sp_stats.get("totalShots", 0),
                            "shots_on_target": sp_stats.get("onTargetScoringAttempt", 0),
                            "saves": sp_stats.get("saves", 0),
                            "saves_inside_box": sp_stats.get("savedShotsFromInsideTheBox", 0),
                            "high_claims": sp_stats.get("goodHighClaim", 0),
                            "keeper_sweepers": sp_stats.get("totalKeeperSweeper", 0),
                            "minutes_played": sp_stats.get("minutesPlayed"),
                        }

                        # Extract player profile / biometrics
                        if mem_id not in player_profiles:
                            dob_ts = sp_player.get("dateOfBirthTimestamp")
                            dob_str = datetime.fromtimestamp(dob_ts, timezone.utc).strftime("%Y-%m-%d") if dob_ts else None
                            slug = sp_player.get("slug")
                            sofa_url = f"https://www.sofascore.com/football/player/{slug}/{sofa_pid}" if (sofa_pid and slug) else (f"https://www.sofascore.com/player/{sofa_pid}" if sofa_pid else None)
                            mv = sp_player.get("proposedMarketValueRaw", {}).get("value") if sp_player.get("proposedMarketValueRaw") else None

                            player_profiles[mem_id] = {
                                "sofascore_id": sofa_pid,
                                "sofascore_slug": slug,
                                "sofascore_url": sofa_url,
                                "sofascore_name": sp_player.get("name"),
                                "height_cm": sp_player.get("height"),
                                "date_of_birth": dob_str,
                                "position_sofa": sp_player.get("position"),
                                "market_value_eur": mv,
                                "nationality": sp_player.get("country", {}).get("name"),
                                "country_code": sp_player.get("country", {}).get("alpha2"),
                                "sofascore_image": f"https://img.sofascore.com/api/v1/player/{sofa_pid}/image" if sofa_pid else None,
                            }

    print(f"✅ Matched {matched_player_count} player appearances across {len(player_profiles)} unique players.")

    output_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reconciliation_summary": {
            "matched_matches": len(matched_matches),
            "matched_appearances": matched_player_count,
            "unique_players_enriched": len(player_profiles),
        },
        "matches": match_team_stats,
        "appearances": appearance_stats,
        "profiles": player_profiles,
    }

    ENRICHED_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(ENRICHED_OUT, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2)
    print(f"💾 Saved enriched dataset to {ENRICHED_OUT} ({(ENRICHED_OUT.stat().st_size / 1024):.1f} KB)")
    return output_payload


def main():
    parser = argparse.ArgumentParser(description="Reconcile DRIBL and Sofascore data")
    parser.add_argument("--audit", action="store_true", help="Print detailed match rate audit")
    args = parser.parse_args()

    if not DRIBL_PATH.exists():
        print(f"❌ Error: {DRIBL_PATH} does not exist.")
        return

    if not SOFASCORE_PATH.exists():
        print(f"ℹ️ {SOFASCORE_PATH} not found.")
        print("Run `extract_sofascore.js` in your browser console on sofascore.com to download it.")
        return

    dribl = load_json(DRIBL_PATH)
    sofa = load_json(SOFASCORE_PATH)
    build_reconciliation(dribl, sofa, audit=args.audit)


if __name__ == "__main__":
    main()

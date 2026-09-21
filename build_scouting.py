#!/usr/bin/env python3
"""
Build the scouting workbook from the enriched DRIBL dump.

    python build_scouting.py                # reads output/dribl_raw_2026_v2.json
    python build_scouting.py --check        # also run reconciliation checks

Input : output/dribl_raw_2026_v2.json  (produced by extract_browser.js)
Output: output/dribl_scouting_2026.xlsx + split JSON files (output/dribl_*_2026_v2.json)

Sheets
  Shortlist      ranked players with >= MIN_MINUTES, league-adjusted, GK and outfield separated
  Player Season  one row per player x team, every derived metric
  Appearances    one row per player x match (bench-unused included), with derived minutes
  Team Context   per-team strength/usage context
  Matches, Events, Ladders, Notes
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path("output/dribl_raw_2026_v2.json")
SOFA_ENRICHED = Path("output/sofascore_enriched_2026.json")
OUT = Path("output/dribl_scouting_2026.xlsx")
SPLIT_DIR = Path("output")

MIN_MINUTES = 450            # floor for the shortlist
MIN_APPS = 5                 # and at least this many appearances
PRIOR_MINUTES = 450          # shrinkage: rates are pulled toward the league mean with this much "prior" playing time
PRIOR_APPS = 5               # same idea for per-appearance rates (votes)
HIDDEN_GEM_BONUS = 0.30      # added to gem_score when the player has no senior minutes
U18_BONUS = 0.15             # added to gem_score for U18-eligible players
DEFAULT_SUB_ON = 70          # median recorded sub-on minute; used when a sub has no recorded minute
LATE_MINUTE = 75
SECTION_ORDER = {"ft-first-half": 0, "ft-second-half": 1, "et-first-half": 2, "et-second-half": 3, "penalties": 4}
GRADE_RANK = {"U18": 0, "RES": 1, "SEN": 2}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def grade_of(league: str) -> str:
    if "Under 18" in league or "(18s)" in league:
        return "U18"
    if "Reserve" in league:
        return "RES"
    return "SEN"


DIVISION_BY_COMPETITION = {
    "HPG Homes State League 1": "SL1",
    "HPG Homes State League 2": "SL2",
    "RAA National Premier League": "NPL",
    "Home and Away": "SAASL",  # SAASL's (saasl.dribl.com) regular season competition
}


def division_of(competition: str) -> str:
    return DIVISION_BY_COMPETITION.get(competition, competition)


def to_int(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def zscore(s: pd.Series) -> pd.Series:
    sd = s.std(ddof=0)
    if not sd or np.isnan(sd):
        return pd.Series(0.0, index=s.index)
    return (s - s.mean()) / sd


def pct_rank(s: pd.Series) -> pd.Series:
    return s.rank(pct=True) * 100


def ordinal(x) -> str:
    n = int(round(x))
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


# ---------------------------------------------------------------------------
# load + matches
# ---------------------------------------------------------------------------

def load_raw(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def load_sofascore(path: Path = SOFA_ENRICHED) -> dict:
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: could not load {path}: {e}")
            return {}
    return {}


def build_matches(raw: dict, sofa: dict = None) -> pd.DataFrame:
    sofa_m = (sofa or {}).get("matches", {})
    rows = []
    for f in raw["fixtures"]:
        m = raw["mc"].get(f["match_hash_id"])
        if not m:
            continue
        has_et = m.get("game_progress") == "pen" or any(
            str(e.get("game_section", "")).startswith("et") for e in m.get("match_events", [])
        )
        match_len = 120 if has_et else 90
        dt_utc = pd.to_datetime(m["date"], utc=True)
        sm = sofa_m.get(f["match_hash_id"], {})
        rows.append({
            "match_hash_id": f["match_hash_id"],
            "fixture_id": f["hash_id"],
            "competition": f["competition"],
            "division": division_of(f["competition"]),
            "league": f["league"],
            "league_id": f["league_id"],
            "grade": grade_of(f["league"]),
            "match_type": m.get("match_type"),
            "is_finals": m.get("match_type") == "finals",
            "date_utc": dt_utc.tz_convert(None),
            "date_local": dt_utc.tz_convert("Australia/Adelaide").tz_localize(None),
            "round": m.get("round_label") or m.get("display_round_number"),
            "round_number": m.get("round_number"),
            "venue": m.get("ground_name"),
            "field": m.get("field_name"),
            "artificial_pitch": "artificial" in str(m.get("field_name", "")).lower(),
            "home_team_id": m["home_team_hash_id"],
            "away_team_id": m["away_team_hash_id"],
            "home_team": m.get("home_team_name"),
            "away_team": m.get("away_team_name"),
            "home_club": m.get("home_club_name"),
            "away_club": m.get("away_club_name"),
            "home_score": m.get("home_score"),
            "away_score": m.get("away_score"),
            "home_score_ht": m.get("home_score_ht"),
            "away_score_ht": m.get("away_score_ht"),
            "home_score_pens": m.get("home_score_penalty"),
            "away_score_pens": m.get("away_score_penalty"),
            "win_status": m.get("win_status"),
            "match_len": match_len,
            "home_formation": m.get("home_formation"),
            "away_formation": m.get("away_formation"),
            "matchsheet_confirmed": bool(m.get("matchsheet_home_team_confirmed") and m.get("matchsheet_away_team_confirmed")),
            "n_events": len(m.get("match_events", [])),
            "referee": next((r.get("name") for r in m.get("referees", []) if r.get("role") == "cr"), None),
            "home_possession": sm.get("home_possession") or sm.get("home_ballPossession"),
            "away_possession": sm.get("away_possession") or sm.get("away_ballPossession"),
            "home_xg": sm.get("home_xg") or sm.get("home_expectedGoals"),
            "away_xg": sm.get("away_xg") or sm.get("away_expectedGoals"),
            "home_shots": sm.get("home_shots") or sm.get("home_totalShotsOnGoal"),
            "away_shots": sm.get("away_shots") or sm.get("away_totalShotsOnGoal"),
            "home_shots_on_target": sm.get("home_shots_on_target"),
            "away_shots_on_target": sm.get("away_shots_on_target"),
            "home_corners": sm.get("home_corners"),
            "away_corners": sm.get("away_corners"),
            "home_fouls": sm.get("home_fouls"),
            "away_fouls": sm.get("away_fouls"),
            "home_passes": sm.get("home_passes"),
            "away_passes": sm.get("away_passes"),
            "home_accurate_passes": sm.get("home_accurate_passes"),
            "away_accurate_passes": sm.get("away_accurate_passes"),
        })
    df = pd.DataFrame(rows)
    return df.sort_values(["league", "date_utc"]).reset_index(drop=True)


def build_events(raw: dict, matches: pd.DataFrame) -> pd.DataFrame:
    meta = matches.set_index("match_hash_id")
    rows = []
    for mid, m in raw["mc"].items():
        if mid not in meta.index:
            continue
        mm = meta.loc[mid]
        for e in m.get("match_events", []):
            rows.append({
                "match_hash_id": mid, "league": mm["league"], "date_local": mm["date_local"], "round": mm["round"],
                "home_team": mm["home_team"], "away_team": mm["away_team"],
                "event_type": e.get("type"), "minute": to_int(e.get("minute")), "game_section": e.get("game_section"),
                "team_id": e.get("team_id"), "player": e.get("name", ""), "jersey": e.get("jersey", ""),
                "card_type": e.get("final_card_type", ""), "card_code": e.get("final_card_code", ""),
                "sub_in": e.get("in_name", ""), "sub_out": e.get("out_name", ""),
                "own_goal": e.get("own_goal"), "penalty_kick": e.get("penalty_kick"),
            })
    return pd.DataFrame(rows)


def build_ladders(raw: dict) -> pd.DataFrame:
    rows = []
    for lg in raw["leagues"]:
        for e in raw["ladders"].get(lg["league_id"], []):
            rows.append({
                "league": lg["league"], "league_id": lg["league_id"], "grade": grade_of(lg["league"]),
                "division": division_of(lg["competition"]), "is_finals": "Final" in lg["league"],
                "position": e.get("position"), "team_id": e.get("team_hash_id"), "team": e.get("team_name"),
                "club": e.get("club_name"), "club_code": e.get("club_code"),
                "played": e.get("played"), "won": e.get("won"), "drawn": e.get("drawn"), "lost": e.get("lost"),
                "goals_for": e.get("goals_for"), "goals_against": e.get("goals_against"),
                "goal_difference": e.get("goal_difference"), "points": e.get("points"),
                "points_per_game": e.get("points_per_game"), "point_adjustment": e.get("point_adjustment"),
                "yellow_cards": e.get("yellow_cards"), "red_cards": e.get("red_cards"),
            })
    df = pd.DataFrame(rows)
    df["n_teams"] = df.groupby("league_id")["team_id"].transform("count")
    df["top_half"] = df["position"] <= df["n_teams"] / 2
    return df.sort_values(["league", "position"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# goal timeline (game state)
# ---------------------------------------------------------------------------

def goal_timeline(m: dict, match_len: int) -> list:
    """Ordered list of goals with running score and a game-state class for the benefiting team."""
    home, away = m["home_team_hash_id"], m["away_team_hash_id"]
    goals = sorted(
        (g for g in m.get("goals", []) if g.get("game_section") != "penalties"),
        key=lambda g: (SECTION_ORDER.get(g.get("game_section"), 9), to_int(g.get("minute")) or 0),
    )
    score = {home: 0, away: 0}
    out = []
    for g in goals:
        scorer_team = g["team_id"]
        ben = scorer_team if not g.get("own_goal") else (away if scorer_team == home else home)
        opp = away if ben == home else home
        diff = score[ben] - score[opp]
        cls = "equaliser" if diff == -1 else "go_ahead" if diff == 0 else "extend" if diff > 0 else "consolation"
        score[ben] += 1
        minute = to_int(g.get("minute")) or 0
        out.append({
            "scorer_team": scorer_team, "ben_team": ben, "minute": minute, "abs_minute": min(minute, match_len),
            "section": g.get("game_section"), "own_goal": bool(g.get("own_goal")), "penalty": bool(g.get("penalty_kick")),
            "state": cls, "late": minute >= LATE_MINUTE and g.get("game_section") != "ft-first-half",
            "score_after": dict(score),
        })
    # winning goal: the go-ahead goal after which the team never fell back to level, in a match it won
    final = score
    for team in (home, away):
        if final[team] <= final[away if team == home else home]:
            continue
        opp = away if team == home else home
        for i, g in enumerate(out):
            if g["ben_team"] != team or g["state"] != "go_ahead":
                continue
            never_level = all(o["score_after"][team] > o["score_after"][opp] for o in out[i:])
            if never_level:
                g["winner"] = True
                break
    return out


# ---------------------------------------------------------------------------
# appearances
# ---------------------------------------------------------------------------

def build_appearances(raw: dict, matches: pd.DataFrame, ladders: pd.DataFrame, sofa: dict = None) -> pd.DataFrame:
    meta = matches.set_index("match_hash_id")
    reg = ladders[~ladders["is_finals"]].set_index("team_id")
    timelines = {mid: goal_timeline(raw["mc"][mid], int(meta.loc[mid, "match_len"])) for mid in meta.index}
    sofa_apps = (sofa or {}).get("appearances", {})

    rows = []
    for key, players in raw["members"].items():
        mid, side = key.split(":")
        if mid not in meta.index:
            continue
        mm = meta.loc[mid]
        m = raw["mc"][mid]
        team = m[f"{side}_team_hash_id"]
        opp_side = "away" if side == "home" else "home"
        opp = m[f"{opp_side}_team_hash_id"]
        match_len = int(mm["match_len"])
        gf, ga = m[f"{side}_score"], m[f"{opp_side}_score"]
        points = 3 if gf > ga else 1 if gf == ga else 0
        tl = timelines[mid]
        players = [p for p in players if p.get("role_slug") == "player"]
        team_recorded_subs = any(p.get("in_subs") or p.get("out_subs") for p in players)
        # copy of per-goal state classes so each player goal consumes one timeline entry
        pool = defaultdict(list)
        for g in tl:
            pool[(g["scorer_team"], g["section"], g["minute"], g["own_goal"], g["penalty"])].append(g)

        for p in players:
            playing = bool(p.get("playing"))
            starting = bool(p.get("starting")) and playing
            in_subs, out_subs = p.get("in_subs") or [], p.get("out_subs") or []
            sub_on = to_int(in_subs[0].get("minute")) if (in_subs and not starting) else None
            sub_off = to_int(out_subs[0].get("minute")) if out_subs else None
            cards = p.get("cards") or []
            red_min = min((to_int(c.get("minute")) or match_len for c in cards if "Red" in str(c.get("final_card_type"))), default=None)
            yellows = sum(1 for c in cards if "Yellow" in str(c.get("final_card_type")))
            reds = sum(1 for c in cards if "Red" in str(c.get("final_card_type")))

            minutes, start, end, estimated = 0, None, None, False
            if playing:
                if starting:
                    start = 0
                elif sub_on is not None:
                    start = min(sub_on, match_len - 1)
                else:
                    start, estimated = DEFAULT_SUB_ON, True
                ends = [x for x in (sub_off, red_min) if x is not None]
                end = min(min(ends), match_len) if ends else match_len
                if end <= start:
                    end = min(start + 1, match_len)
                minutes = end - start
                if not team_recorded_subs:
                    estimated = True   # this team-side logged no subs at all; sub-off minutes are unknown

            goals = p.get("goals") or []
            g_total = len(goals)
            g_og = sum(1 for g in goals if g.get("own_goal"))
            g_pen = sum(1 for g in goals if g.get("penalty_kick") and not g.get("own_goal"))
            g_open = g_total - g_og - g_pen
            st = {"equaliser": 0, "go_ahead": 0, "extend": 0, "consolation": 0, "late": 0, "winner": 0}
            for g in goals:
                if g.get("own_goal"):
                    continue
                k = (team, g.get("game_section"), to_int(g.get("minute")) or 0, False, bool(g.get("penalty_kick")))
                if pool[k]:
                    e = pool[k].pop(0)
                    st[e["state"]] += 1
                    st["late"] += int(e["late"])
                    st["winner"] += int(e.get("winner", False))

            gf_on = ga_on = 0
            if playing:
                for g in tl:
                    if start <= g["abs_minute"] < end or (g["abs_minute"] == end == match_len and end > start):
                        if g["ben_team"] == team:
                            gf_on += 1
                        elif g["ben_team"] == opp:
                            ga_on += 1
            full_match = playing and start == 0 and end == match_len

            opp_lad = reg.loc[opp] if opp in reg.index else None
            sa = sofa_apps.get(f"{mid}:{p['user_hash_id']}", {})
            rows.append({
                "player_id": p["user_hash_id"],
                "player_name": f"{p.get('first_name', '')} {p.get('last_name', '')}".strip(),
                "team_id": team, "team": m[f"{side}_team_name"], "club": m[f"{side}_club_name"],
                "league": mm["league"], "grade": mm["grade"], "division": mm["division"], "is_finals": mm["is_finals"],
                "match_hash_id": mid, "fixture_id": mm["fixture_id"], "date_local": mm["date_local"], "round": mm["round"],
                "opponent": m[f"{opp_side}_team_name"], "opponent_id": opp, "home_away": "H" if side == "home" else "A",
                "team_gf": gf, "team_ga": ga, "result": "W" if points == 3 else "D" if points == 1 else "L", "points": points,
                "opp_ladder_pos": None if opp_lad is None else opp_lad["position"],
                "opp_top_half": None if opp_lad is None else bool(opp_lad["top_half"]),
                "jersey": p.get("jersey"), "available": bool(p.get("available")),
                "playing": playing, "starting": starting, "bench_unused": not playing,
                "borrowed": bool(p.get("borrowed")), "is_captain": bool(p.get("is_captain")),
                "is_goalkeeper": bool(p.get("is_goalkeeper")), "votes": to_int(p.get("votes")) or 0,
                "has_ban": bool(p.get("has_ban")),
                "sub_on_min": sub_on, "sub_off_min": sub_off, "red_card_min": red_min,
                "minutes": minutes, "minutes_estimated": bool(estimated), "full_match": bool(full_match),
                "match_len": match_len,
                "goals": g_total - g_og, "goals_open_play": g_open, "goals_penalty": g_pen, "own_goals": g_og,
                "goals_equaliser": st["equaliser"], "goals_go_ahead": st["go_ahead"], "goals_extend": st["extend"],
                "goals_consolation": st["consolation"], "goals_late": st["late"], "goals_winner": st["winner"],
                "gf_on_pitch": gf_on, "ga_on_pitch": ga_on,
                "clean_sheet": bool(full_match and ga_on == 0),
                "yellow_cards": yellows, "red_cards": reds,
                "sofascore_rating": sa.get("sofascore_rating"),
                "assists": sa.get("assists", 0),
                "xg": sa.get("xg", 0.0),
                "xa": sa.get("xa", 0.0),
                "key_passes": sa.get("key_passes", 0),
                "big_chances_created": sa.get("big_chances_created", 0),
                "big_chances_missed": sa.get("big_chances_missed", 0),
                "passes_total": sa.get("passes_total", 0),
                "passes_acc": sa.get("passes_acc", 0),
                "pass_acc_pct": round(sa.get("passes_acc", 0) / sa["passes_total"] * 100, 1) if sa.get("passes_total", 0) > 0 else None,
                "long_balls_total": sa.get("long_balls_total", 0),
                "long_balls_acc": sa.get("long_balls_acc", 0),
                "duels_won": sa.get("duels_won", 0),
                "duels_total": sa.get("duels_total", 0),
                "duel_win_pct": round(sa.get("duels_won", 0) / sa["duels_total"] * 100, 1) if sa.get("duels_total", 0) > 0 else None,
                "aerials_won": sa.get("aerials_won", 0),
                "aerials_total": sa.get("aerials_total", 0),
                "aerial_win_pct": round(sa.get("aerials_won", 0) / sa["aerials_total"] * 100, 1) if sa.get("aerials_total", 0) > 0 else None,
                "tackles": sa.get("tackles", 0),
                "interceptions": sa.get("interceptions", 0),
                "recoveries": sa.get("recoveries", 0),
                "clearances": sa.get("clearances", 0),
                "defensive_actions": sa.get("tackles", 0) + sa.get("interceptions", 0),
                "dribbles_won": sa.get("dribbles_won", 0),
                "dribbles_total": sa.get("dribbles_total", 0),
                "dribble_success_pct": round(sa.get("dribbles_won", 0) / sa["dribbles_total"] * 100, 1) if sa.get("dribbles_total", 0) > 0 else None,
                "touches": sa.get("touches", 0),
                "dispossessed": sa.get("dispossessed", 0),
                "shots_total": sa.get("shots_total", 0),
                "shots_on_target": sa.get("shots_on_target", 0),
                "saves": sa.get("saves", 0),
                "saves_inside_box": sa.get("saves_inside_box", 0),
                "has_sofascore": bool(sa.get("sofascore_rating") is not None or sa.get("passes_total", 0) > 0 or sa.get("duels_total", 0) > 0),
            })
    df = pd.DataFrame(rows)
    return df.sort_values(["league", "team", "date_local", "player_name"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# team context
# ---------------------------------------------------------------------------

def build_team_context(matches: pd.DataFrame, app: pd.DataFrame, ladders: pd.DataFrame) -> pd.DataFrame:
    sides = []
    for side, opp in (("home", "away"), ("away", "home")):
        s = matches[["match_hash_id", "league", "grade", "division", "is_finals", "match_len",
                     f"{side}_team_id", f"{side}_team", f"{side}_club", f"{side}_score", f"{opp}_score",
                     f"{side}_possession", f"{side}_xg", f"{opp}_xg"]].copy()
        s.columns = ["match_hash_id", "league", "grade", "division", "is_finals", "match_len",
                     "team_id", "team", "club", "gf", "ga", "possession", "xg", "xga"]
        sides.append(s)
    tm = pd.concat(sides, ignore_index=True)
    tm["points"] = np.select([tm.gf > tm.ga, tm.gf == tm.ga], [3, 1], 0)

    rr = tm[~tm.is_finals]
    primary = rr.groupby("team_id")["league"].agg(lambda x: x.mode().iat[0]).rename("primary_league")
    ctx = tm.groupby("team_id").agg(
        team=("team", "first"), club=("club", "first"), grade=("grade", "first"), division=("division", "first"),
        matches=("match_hash_id", "count"), finals_matches=("is_finals", "sum"),
        possible_minutes=("match_len", "sum"), gf=("gf", "sum"), ga=("ga", "sum"),
    )
    rr_stats = rr.groupby("team_id").agg(
        rr_matches=("match_hash_id", "count"), rr_points=("points", "sum"),
        rr_gf=("gf", "sum"), rr_ga=("ga", "sum"),
        avg_possession_pct=("possession", lambda x: round(float(x.dropna().mean()), 1) if len(x.dropna()) else np.nan),
        rr_xg=("xg", lambda x: round(float(x.dropna().sum()), 2) if len(x.dropna()) else np.nan),
        rr_xga=("xga", lambda x: round(float(x.dropna().sum()), 2) if len(x.dropna()) else np.nan),
    )
    ctx = ctx.join(primary).join(rr_stats)
    ctx["ppg"] = ctx.rr_points / ctx.rr_matches
    ctx["gf_per_match"] = ctx.rr_gf / ctx.rr_matches
    ctx["ga_per_match"] = ctx.rr_ga / ctx.rr_matches
    ctx["gd_per_match"] = ctx.gf_per_match - ctx.ga_per_match
    ctx["team_xg_per_match"] = np.where(ctx.rr_xg.notna(), round(ctx.rr_xg / ctx.rr_matches, 2), np.nan)
    ctx["team_xga_per_match"] = np.where(ctx.rr_xga.notna(), round(ctx.rr_xga / ctx.rr_matches, 2), np.nan)
    ctx["team_xgd_per_match"] = np.where(ctx.team_xg_per_match.notna() & ctx.team_xga_per_match.notna(),
                                         round(ctx.team_xg_per_match - ctx.team_xga_per_match, 2), np.nan)

    reg = ladders[~ladders.is_finals].set_index("team_id")[["position", "n_teams", "top_half", "points"]]
    reg.columns = ["ladder_pos", "ladder_teams", "ladder_top_half", "ladder_points"]
    ctx = ctx.join(reg)

    usage = app.groupby("team_id").agg(
        players_used=("player_id", lambda x: x[app.loc[x.index, "playing"]].nunique()),
        squad_named=("player_id", "nunique"),
        borrowed_in_apps=("borrowed", lambda x: int((x & app.loc[x.index, "playing"]).sum())),
        borrowed_in_players=("player_id", lambda x: x[app.loc[x.index, "borrowed"] & app.loc[x.index, "playing"]].nunique()),
        team_goals_from_lineups=("goals", "sum"),
        minutes_estimated_apps=("minutes_estimated", "sum"),
    )
    ctx = ctx.join(usage).reset_index()
    return ctx.sort_values(["division", "grade", "primary_league", "ladder_pos"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# player season
# ---------------------------------------------------------------------------

def build_player_season(app: pd.DataFrame, ctx: pd.DataFrame, matches: pd.DataFrame, sofa: dict = None) -> pd.DataFrame:
    played = app[app.playing]
    g = app.groupby(["player_id", "team_id"])
    season = g.agg(
        player_name=("player_name", "first"), team=("team", "first"), club=("club", "first"),
        grade=("grade", "first"), division=("division", "first"),
        squad_named=("match_hash_id", "count"), bench_unused=("bench_unused", "sum"),
        jersey=("jersey", lambda x: x.mode().iat[0] if len(x.mode()) else None),
    ).reset_index()

    pg = played.groupby(["player_id", "team_id"]).agg(
        apps=("match_hash_id", "count"), starts=("starting", "sum"), finals_apps=("is_finals", "sum"),
        minutes=("minutes", "sum"), minutes_est_apps=("minutes_estimated", "sum"), full_matches=("full_match", "sum"),
        borrowed_apps=("borrowed", "sum"), captain_apps=("is_captain", "sum"), is_goalkeeper=("is_goalkeeper", "max"),
        gk_apps=("is_goalkeeper", "sum"), votes=("votes", "sum"), votes_3=("votes", lambda x: int((x == 3).sum())),
        goals=("goals", "sum"), goals_open_play=("goals_open_play", "sum"), goals_penalty=("goals_penalty", "sum"),
        own_goals=("own_goals", "sum"), goals_equaliser=("goals_equaliser", "sum"), goals_go_ahead=("goals_go_ahead", "sum"),
        goals_winner=("goals_winner", "sum"), goals_late=("goals_late", "sum"), goals_consolation=("goals_consolation", "sum"),
        goals_away=("goals", lambda x: int(x[played.loc[x.index, "home_away"] == "A"].sum())),
        goals_vs_top_half=("goals", lambda x: int(x[played.loc[x.index, "opp_top_half"] == True].sum())),
        goals_as_sub=("goals", lambda x: int(x[~played.loc[x.index, "starting"]].sum())),
        sub_minutes=("minutes", lambda x: int(x[~played.loc[x.index, "starting"]].sum())),
        avg_sub_off=("sub_off_min", lambda x: x[played.loc[x.index, "starting"]].mean()),
        gf_on_pitch=("gf_on_pitch", "sum"), ga_on_pitch=("ga_on_pitch", "sum"), clean_sheets=("clean_sheet", "sum"),
        yellow_cards=("yellow_cards", "sum"), red_cards=("red_cards", "sum"), ban_apps=("has_ban", "sum"),
        wins=("points", lambda x: int((x == 3).sum())), points_when_playing=("points", "sum"),
        team_goals_in_apps=("team_gf", "sum"), team_ga_in_apps=("team_ga", "sum"),
        assists=("assists", "sum"),
        xg=("xg", "sum"),
        xa=("xa", "sum"),
        key_passes=("key_passes", "sum"),
        big_chances_created=("big_chances_created", "sum"),
        big_chances_missed=("big_chances_missed", "sum"),
        passes_total=("passes_total", "sum"),
        passes_acc=("passes_acc", "sum"),
        long_balls_total=("long_balls_total", "sum"),
        long_balls_acc=("long_balls_acc", "sum"),
        duels_won=("duels_won", "sum"),
        duels_total=("duels_total", "sum"),
        aerials_won=("aerials_won", "sum"),
        aerials_total=("aerials_total", "sum"),
        tackles=("tackles", "sum"),
        interceptions=("interceptions", "sum"),
        recoveries=("recoveries", "sum"),
        clearances=("clearances", "sum"),
        dribbles_won=("dribbles_won", "sum"),
        dribbles_total=("dribbles_total", "sum"),
        touches=("touches", "sum"),
        dispossessed=("dispossessed", "sum"),
        shots_total=("shots_total", "sum"),
        shots_on_target=("shots_on_target", "sum"),
        saves=("saves", "sum"),
        saves_inside_box=("saves_inside_box", "sum"),
        sofascore_apps=("has_sofascore", "sum"),
        sofascore_rating=("sofascore_rating", lambda x: round(float(x.dropna().mean()), 2) if len(x.dropna()) else np.nan),
    ).reset_index()
    season = season.merge(pg, on=["player_id", "team_id"], how="left")
    for c in pg.columns:
        if c not in ("player_id", "team_id", "sofascore_rating") and season[c].dtype.kind in "fi":
            season[c] = season[c].fillna(0)

    # team context
    tc = ctx.set_index("team_id")[["primary_league", "matches", "possible_minutes", "ppg", "gf_per_match", "ga_per_match",
                                    "gd_per_match", "ladder_pos", "ladder_teams", "gf", "ga", "rr_matches"]]
    tc.columns = ["league", "team_matches", "team_possible_minutes", "team_ppg", "team_gf_per_match", "team_ga_per_match",
                  "team_gd_per_match", "team_ladder_pos", "ladder_teams", "team_goals", "team_goals_against", "team_rr_matches"]
    season = season.merge(tc, left_on="team_id", right_index=True, how="left").copy()

    per90 = lambda n: np.where(season.minutes > 0, n / season.minutes * 90, np.nan)
    pct = lambda num, den: np.where(den > 0, np.round(num / den * 100, 1), np.nan)

    season["sub_apps"] = season.apps - season.starts
    season["availability_pct"] = season.squad_named / season.team_matches * 100
    season["minutes_share_pct"] = season.minutes / season.team_possible_minutes * 100
    season["start_rate_pct"] = np.where(season.apps > 0, season.starts / season.apps * 100, np.nan)
    season["goals_per90"] = per90(season.goals)
    season["npg_per90"] = per90(season.goals_open_play)
    season["assists_p90"] = per90(season.assists)
    season["xg_p90"] = per90(season.xg)
    season["xa_p90"] = per90(season.xa)
    season["key_passes_p90"] = per90(season.key_passes)
    season["goal_involvements"] = season.goals + season.assists
    season["goal_involvements_p90"] = per90(season.goal_involvements)
    season["finishing_delta"] = np.where(season.xg > 0, np.round(season.goals - season.xg, 2), np.nan)
    season["assist_delta"] = np.where(season.xa > 0, np.round(season.assists - season.xa, 2), np.nan)

    # Passing & Distribution
    season["passes_p90"] = per90(season.passes_total)
    season["pass_acc_pct"] = pct(season.passes_acc, season.passes_total)
    season["long_balls_p90"] = per90(season.long_balls_total)
    season["long_ball_acc_pct"] = pct(season.long_balls_acc, season.long_balls_total)

    # Duels & Physicality
    season["duels_p90"] = per90(season.duels_total)
    season["duel_win_pct"] = pct(season.duels_won, season.duels_total)
    season["aerials_p90"] = per90(season.aerials_total)
    season["aerial_win_pct"] = pct(season.aerials_won, season.aerials_total)

    # Defending & Ball Winning
    season["tackles_p90"] = per90(season.tackles)
    season["interceptions_p90"] = per90(season.interceptions)
    season["recoveries_p90"] = per90(season.recoveries)
    season["clearances_p90"] = per90(season.clearances)
    season["defensive_actions"] = season.tackles + season.interceptions
    season["defensive_actions_p90"] = per90(season.defensive_actions)

    # Dribbling & Ball Carrying
    season["dribbles_p90"] = per90(season.dribbles_won)
    season["dribble_success_pct"] = pct(season.dribbles_won, season.dribbles_total)
    season["touches_p90"] = per90(season.touches)

    # Shooting
    season["shots_p90"] = per90(season.shots_total)
    season["shot_acc_pct"] = pct(season.shots_on_target, season.shots_total)
    season["xg_per_shot"] = np.where(season.shots_total > 0, np.round(season.xg / season.shots_total, 2), np.nan)

    # Goalkeeping
    season["saves_p90"] = per90(season.saves)

    has_sofa = season.sofascore_apps > 0
    # For players without Sofascore data, keep Sofascore-specific metrics as np.nan
    sofa_rate_cols = [
        "assists", "assists_p90",
        "xg", "xg_p90", "xa", "xa_p90", "key_passes", "key_passes_p90",
        "big_chances_created", "big_chances_missed",
        "passes_total", "passes_acc", "passes_p90", "pass_acc_pct",
        "long_balls_total", "long_balls_acc", "long_balls_p90", "long_ball_acc_pct",
        "duels_won", "duels_total", "duels_p90", "duel_win_pct",
        "aerials_won", "aerials_total", "aerials_p90", "aerial_win_pct",
        "tackles", "tackles_p90", "interceptions", "interceptions_p90",
        "recoveries", "recoveries_p90", "clearances", "clearances_p90",
        "defensive_actions", "defensive_actions_p90",
        "dribbles_won", "dribbles_total", "dribbles_p90", "dribble_success_pct",
        "touches", "touches_p90", "dispossessed",
        "shots_total", "shots_on_target", "shots_p90", "shot_acc_pct", "xg_per_shot",
        "finishing_delta", "assist_delta",
    ]
    for sc in sofa_rate_cols:
        season[sc] = np.where(has_sofa, season[sc], np.nan)
    season["goal_involvements"] = np.where(has_sofa, season.goals + season.assists.fillna(0), np.nan)
    season["goal_involvements_p90"] = np.where(has_sofa, per90(season.goal_involvements), np.nan)
    season["saves"] = np.where(has_sofa & season.is_goalkeeper, season.saves, np.nan)
    season["saves_p90"] = np.where(has_sofa & season.is_goalkeeper, season.saves_p90, np.nan)
    season["saves_inside_box"] = np.where(has_sofa & season.is_goalkeeper, season.saves_inside_box, np.nan)
    season["team_goal_share_pct"] = np.where(season.team_goals > 0, season.goals / season.team_goals * 100, np.nan)
    season["goals_per_sub_90"] = np.where(season.sub_minutes > 0, season.goals_as_sub / season.sub_minutes * 90, np.nan)
    season["votes_per_app"] = np.where(season.apps > 0, season.votes / season.apps, np.nan)
    season["yellows_per90"] = per90(season.yellow_cards)
    season["gf_on_pitch_per90"] = per90(season.gf_on_pitch)
    season["ga_on_pitch_per90"] = per90(season.ga_on_pitch)
    season["gd_on_pitch_per90"] = season.gf_on_pitch_per90 - season.ga_on_pitch_per90
    season["team_gd_per90"] = season.team_gd_per_match       # matches are ~90 min
    season["gd_on_pitch_vs_team"] = season.gd_on_pitch_per90 - season.team_gd_per90
    season["ga_on_pitch_vs_team"] = season.ga_on_pitch_per90 - season.team_ga_per_match
    season["clean_sheet_pct"] = np.where(season.full_matches > 0, season.clean_sheets / season.full_matches * 100, np.nan)
    season["ppg_when_playing"] = np.where(season.apps > 0, season.points_when_playing / season.apps, np.nan)

    # team PPG when player starts vs not (regular season only, both sides need >= 3 matches)
    rr_app = played[(~played.is_finals) & played.starting][["player_id", "team_id", "match_hash_id", "points"]]
    team_rr = app[~app.is_finals].drop_duplicates(["team_id", "match_hash_id"])[["team_id", "match_hash_id", "points"]]
    starts_by = rr_app.groupby(["player_id", "team_id"])
    rows = []
    for (pid, tid), grp in starts_by:
        tm = team_rr[team_rr.team_id == tid]
        without = tm[~tm.match_hash_id.isin(grp.match_hash_id)]
        if len(grp) >= 3 and len(without) >= 3:
            rows.append({"player_id": pid, "team_id": tid, "ppg_when_starts": grp.points.mean(),
                         "ppg_when_not_starting": without.points.mean(), "n_without": len(without)})
    if rows:
        season = season.merge(pd.DataFrame(rows), on=["player_id", "team_id"], how="left")
        season["ppg_start_diff"] = season.ppg_when_starts - season.ppg_when_not_starting
    else:
        season["ppg_when_starts"] = season["ppg_when_not_starting"] = season["ppg_start_diff"] = np.nan

    # pathway across all teams for the player
    pw = played.groupby("player_id").apply(lambda d: pd.Series({
        "grades_played": "/".join(sorted(d.grade.unique(), key=lambda g: -GRADE_RANK[g])),
        "highest_grade": max(d.grade.unique(), key=lambda g: GRADE_RANK[g]),
        "n_teams": d.team_id.nunique(), "n_clubs": d.club.nunique(),
        "u18_player": bool((d.grade == "U18").any()),
        "sen_minutes": int(d.minutes[d.grade == "SEN"].sum()), "res_minutes": int(d.minutes[d.grade == "RES"].sum()),
        "u18_minutes": int(d.minutes[d.grade == "U18"].sum()),
        "sen_apps": int((d.grade == "SEN").sum()), "sen_starts": int(d.starting[d.grade == "SEN"].sum()),
        "total_minutes_all_teams": int(d.minutes.sum()), "borrowed_apps_all": int(d.borrowed.sum()),
        "total_goals_all_teams": int(d.goals.sum()), "total_votes_all_teams": int(d.votes.sum()),
    }), include_groups=False).reset_index()
    season = season.merge(pw, on="player_id", how="left")
    season["played_above_this_grade"] = season.apply(
        lambda r: GRADE_RANK.get(r.highest_grade, 0) > GRADE_RANK[r.grade] if isinstance(r.highest_grade, str) else False, axis=1)
    season["is_goalkeeper"] = season.is_goalkeeper.fillna(False).astype(bool)
    season["role"] = np.where(season.is_goalkeeper, "GK", "Outfield")

    sofa_prof = (sofa or {}).get("profiles", {})
    if sofa_prof:
        prof_rows = [{"player_id": pid,
                      "sofascore_id": info.get("sofascore_id"),
                      "sofascore_slug": info.get("sofascore_slug"),
                      "sofascore_url": info.get("sofascore_url"),
                      "market_value_eur": info.get("market_value_eur"),
                      "height_cm": info.get("height_cm"),
                      "date_of_birth": info.get("date_of_birth"),
                      "position_sofa": info.get("position_sofa")}
                     for pid, info in sofa_prof.items()]
        prof_df = pd.DataFrame(prof_rows)
        season = season.merge(prof_df, on="player_id", how="left")
    else:
        season["sofascore_id"] = None
        season["sofascore_slug"] = None
        season["sofascore_url"] = None
        season["market_value_eur"] = None
        season["height_cm"] = None
        season["date_of_birth"] = None
        season["position_sofa"] = None

    cols_first = ["player_id", "player_name", "club", "team", "league", "grade", "division", "role", "jersey",
                  "apps", "starts", "sub_apps", "bench_unused", "squad_named", "minutes", "minutes_est_apps",
                  "minutes_share_pct", "availability_pct", "start_rate_pct",
                  "goals", "goals_open_play", "goals_penalty", "own_goals", "goals_per90", "npg_per90", "team_goal_share_pct",
                  "goals_equaliser", "goals_go_ahead", "goals_winner", "goals_late", "goals_consolation", "goals_away",
                  "goals_vs_top_half", "goals_as_sub", "goals_per_sub_90", "avg_sub_off",
                  "votes", "votes_3", "votes_per_app", "captain_apps", "borrowed_apps",
                  "gf_on_pitch", "ga_on_pitch", "gd_on_pitch_per90", "gd_on_pitch_vs_team", "ga_on_pitch_per90", "ga_on_pitch_vs_team",
                  "clean_sheets", "full_matches", "clean_sheet_pct",
                  "yellow_cards", "red_cards", "yellows_per90", "ban_apps",
                  "ppg_when_playing", "ppg_when_starts", "ppg_when_not_starting", "ppg_start_diff",
                  "team_ladder_pos", "ladder_teams", "team_ppg", "team_gf_per_match", "team_ga_per_match", "team_matches",
                  "grades_played", "highest_grade", "played_above_this_grade", "u18_player", "sen_apps", "sen_starts",
                  "sen_minutes", "res_minutes", "u18_minutes", "n_teams", "n_clubs", "borrowed_apps_all",
                  "total_minutes_all_teams", "total_goals_all_teams", "total_votes_all_teams", "finals_apps", "team_id"]
    rest = [c for c in season.columns if c not in cols_first]
    return season[cols_first + rest].sort_values(["league", "team", "minutes"], ascending=[True, True, False]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# shortlist
# ---------------------------------------------------------------------------

OUTFIELD_WEIGHTS = {"npg_per90_adj": 0.35, "votes_per_app_adj": 0.25, "gd_on_pitch_vs_team": 0.20, "team_goal_share_pct": 0.10, "minutes_share_pct": 0.10}
GK_WEIGHTS = {"ga_abs_neg": 0.25, "ga_rel_neg": 0.15, "clean_sheet_pct": 0.30, "votes_per_app_adj": 0.20, "minutes_share_pct": 0.10}

# Plain-English labels for the weight keys above, used only when rendering the "Shortlist score" note.
WEIGHT_LABELS = {
    "npg_per90_adj": "non-penalty goals/90", "votes_per_app_adj": "votes/app",
    "gd_on_pitch_vs_team": "on-pitch goal difference", "team_goal_share_pct": "share of team goals",
    "minutes_share_pct": "share of team minutes", "ga_abs_neg": "goals conceded/90 (inverted)",
    "ga_rel_neg": "goals conceded vs team rate (inverted)", "clean_sheet_pct": "clean sheet rate",
}


def _weights_str(weights):
    return ", ".join(f"{WEIGHT_LABELS.get(k, k)} {v:.0%}" for k, v in weights.items())


def shrink_rate(events: pd.Series, exposure: pd.Series, prior_rate: float, prior_exposure: float) -> pd.Series:
    """Bayesian-style shrinkage: (events + prior) / (exposure + prior_exposure). Small samples move toward the league rate."""
    return (events + prior_rate * prior_exposure) / (exposure + prior_exposure)


def build_shortlist(season: pd.DataFrame) -> pd.DataFrame:
    pool = season[(season.minutes >= MIN_MINUTES) & (season.apps >= MIN_APPS)].copy()
    pool["ga_abs_neg"] = -pool.ga_on_pitch_per90
    pool["ga_rel_neg"] = -pool.ga_on_pitch_vs_team
    pool["scout_score"] = 0.0
    pool["npg_per90_adj"] = pool["votes_per_app_adj"] = np.nan
    for c in ("pct_npg90", "pct_votes", "pct_gd", "pct_share", "pct_ga", "pct_cs"):
        pool[c] = np.nan

    for role, weights in (("Outfield", OUTFIELD_WEIGHTS), ("GK", GK_WEIGHTS)):
        mask = pool.role == role
        for lg, idx in pool[mask].groupby("league").groups.items():
            sub = pool.loc[idx]
            lg_npg = sub.goals_open_play.sum() / sub.minutes.sum() * 90
            lg_votes = sub.votes.sum() / sub.apps.sum()
            pool.loc[idx, "npg_per90_adj"] = shrink_rate(sub.goals_open_play, sub.minutes / 90, lg_npg, PRIOR_MINUTES / 90)
            pool.loc[idx, "votes_per_app_adj"] = shrink_rate(sub.votes, sub.apps, lg_votes, PRIOR_APPS)
            sub = pool.loc[idx]
            score = pd.Series(0.0, index=idx)
            for col, w in weights.items():
                score += w * zscore(sub[col].fillna(sub[col].median())).fillna(0)
            pool.loc[idx, "scout_score"] = score
            pool.loc[idx, "pct_npg90"] = pct_rank(sub.npg_per90_adj)
            pool.loc[idx, "pct_votes"] = pct_rank(sub.votes_per_app_adj)
            pool.loc[idx, "pct_gd"] = pct_rank(sub.gd_on_pitch_vs_team)
            pool.loc[idx, "pct_share"] = pct_rank(sub.team_goal_share_pct)
            pool.loc[idx, "pct_ga"] = pct_rank(sub.ga_abs_neg)
            pool.loc[idx, "pct_cs"] = pct_rank(sub.clean_sheet_pct)

    pool["hidden_gem"] = (pool.grade != "SEN") & (pool.sen_minutes == 0)
    pool["gem_score"] = pool.scout_score + HIDDEN_GEM_BONUS * pool.hidden_gem + U18_BONUS * pool.u18_player.astype(bool)

    def why(r):
        bits = []
        if r.role == "GK":
            bits.append(f"{r.ga_on_pitch_per90:.2f} GA/90 on pitch ({r.ga_on_pitch_vs_team:+.2f} vs team, {ordinal(r.pct_ga)} pct of league GKs)")
            bits.append(f"{r.clean_sheets:.0f} clean sheets in {r.full_matches:.0f} full matches")
        else:
            if r.pct_npg90 >= 75:
                bits.append(f"{r.goals_open_play:.0f} non-pen goals, {r.npg_per90:.2f}/90 ({ordinal(r.pct_npg90)} pct of league)")
            if r.pct_share >= 75 and r.goals >= 4:
                bits.append(f"{r.team_goal_share_pct:.0f}% of team goals")
            if r.pct_gd >= 75:
                bits.append(f"team GD {r.gd_on_pitch_vs_team:+.2f}/90 better with them on")
            if r.goals_winner + r.goals_go_ahead >= 3:
                bits.append(f"{r.goals_go_ahead:.0f} go-ahead goals, {r.goals_winner:.0f} winners")
            if r.goals_per_sub_90 and r.sub_minutes >= 90 and r.goals_per_sub_90 > max(r.npg_per90 or 0, 0.5):
                bits.append(f"super-sub: {r.goals_as_sub:.0f} goals in {r.sub_minutes:.0f} sub mins")
        if r.pct_votes >= 75 and r.votes >= 3:
            bits.append(f"{r.votes:.0f} BOG votes in {r.apps:.0f} apps ({ordinal(r.pct_votes)} pct)")
        if r.captain_apps >= 3:
            bits.append(f"captain x{r.captain_apps:.0f}")
        if r.team_ladder_pos and r.ladder_teams and r.team_ladder_pos > r.ladder_teams / 2:
            bits.append(f"on a bottom-half side ({r.team_ladder_pos:.0f}/{r.ladder_teams:.0f})")
        if r.hidden_gem:
            bits.append("no senior minutes")
        elif r.grade != "SEN" and r.sen_minutes > 0:
            bits.append(f"{r.sen_minutes:.0f} senior mins already")
        if r.u18_player and r.grade != "U18":
            bits.append("U18-eligible playing up")
        if r.borrowed_apps >= 3:
            bits.append(f"borrowed x{r.borrowed_apps:.0f}")
        if r.minutes_est_apps >= r.apps / 2:
            bits.append("minutes estimated (subs not recorded)")
        if pd.notna(r.get("finishing_delta")) and r.get("finishing_delta") >= 3.0:
            bits.append(f"+{r.finishing_delta:.1f} xG overperformance")
        if pd.notna(r.get("sofascore_rating")) and r.get("sofascore_rating") >= 7.4:
            bits.append(f"avg Sofascore rating {r.sofascore_rating:.2f}")
        if pd.notna(r.get("duel_win_pct")) and r.get("duel_win_pct") >= 65 and r.get("duels_total", 0) >= 30:
            bits.append(f"{r.duel_win_pct:.0f}% duels won")
        if pd.notna(r.get("key_passes_p90")) and r.get("key_passes_p90") >= 2.0:
            bits.append(f"{r.key_passes_p90:.1f} key passes/90")
        return "; ".join(bits)

    pool["why_flagged"] = pool.apply(why, axis=1)
    pool = pool.sort_values(["role", "gem_score"], ascending=[False, False])
    pool["rank_in_role"] = pool.groupby("role").cumcount() + 1
    cols = ["rank_in_role", "role", "player_name", "club", "team", "league", "grade", "division", "u18_player", "highest_grade",
            "hidden_gem", "gem_score", "scout_score", "why_flagged",
            "apps", "starts", "minutes", "minutes_share_pct", "goals", "goals_open_play", "npg_per90", "npg_per90_adj", "team_goal_share_pct",
            "goals_go_ahead", "goals_winner", "goals_late", "votes", "votes_per_app", "votes_per_app_adj", "gd_on_pitch_vs_team",
            "ga_on_pitch_per90", "clean_sheets", "clean_sheet_pct", "yellow_cards", "red_cards",
            "sen_minutes", "borrowed_apps", "team_ladder_pos", "ladder_teams", "minutes_est_apps",
            "sofascore_rating", "xg", "xg_p90", "xa", "xa_p90", "key_passes_p90", "duel_win_pct",
            "sofascore_id", "sofascore_slug", "sofascore_url", "market_value_eur",
            "player_id", "team_id"]
    return pool[[c for c in cols if c in pool.columns]]


# ---------------------------------------------------------------------------
# notes + excel
# ---------------------------------------------------------------------------

NOTES = [
    ("Source", "DRIBL match centres (Football SA SL1/SL2/NPL and SAASL) merged with detailed event-level tracking and physical bios from Sofascore across 7 South Australian tournaments."),
    ("Positions", "DRIBL does not record tactical positions or formations. Player positions (e.g. Center Back, Winger) and physical bios (DOB, height) are enriched from Sofascore profiles where available."),
    ("Sofascore stats", "Advanced event metrics (xG, xA, key passes, duels, passing accuracy, tackles, interceptions, and ratings) cover Senior NPL and tracked leagues. Unmeasured leagues cleanly retain null so rankings remain unbiased."),
    ("Minutes", "Starters: sub-off minute (or red card) else match length. Subs: match length minus sub-on minute. Bench unused: 0."),
    ("Minutes estimated", "U18 leagues rarely record sub minutes. When missing, we assume a sub came on at 70', and a starter on a "
                          "side with no recorded subs played the full match. Flagged in minutes_estimated / minutes_est_apps."),
    ("Goals", "From the lineup goals list. Own goals excluded from 'goals'; penalties split out. Non-pen goals per 90 = goals_open_play / minutes * 90."),
    ("Game state", "Reconstructed from the match-centre goal timeline. equaliser = level after; go_ahead = takes lead; winner = go-ahead goal after which the team never fell level, in a match it won; late = 75'+. "
                   "About 28% of SAASL matches have no goal timeline at all (lineup goal totals are still recorded) — game-state and the Events sheet undercount there; Football SA (SL1/SL2/NPL) timelines are essentially complete."),
    ("On-pitch GD", "Goals for/against while the player was on (using the minute window). gd_on_pitch_vs_team subtracts the team's regular-season GD per match."),
    ("Votes", "Per-match 3-2-1 votes from DRIBL, likely best-on-ground — not shown publicly elsewhere. Recorded for about 249 of 294 matches."),
    ("Borrowed", "DRIBL's flag for a player borrowed from another team in the club that match — a direct playing up/down signal."),
    ("Pathway", "Senior, reserves and U18 minutes summed across all the player's teams. A hidden gem is a non-senior row with zero senior minutes all season."),
    ("Shortlist score", f"Eligible: {MIN_MINUTES}+ minutes and {MIN_APPS}+ apps. Rates are shrunk toward the league mean, as if starting from "
                        f"{PRIOR_MINUTES} minutes / {PRIOR_APPS} apps, so short bursts don't top the list — then compared as z-scores within league. "
                        f"Outfield weights: {_weights_str(OUTFIELD_WEIGHTS)}. Goalkeeper weights: {_weights_str(GK_WEIGHTS)}. "
                        f"Hidden gems get +{HIDDEN_GEM_BONUS:g}, U18 players +{U18_BONUS:g}."),
    ("Ladder / opponent strength", "Regular-season ladders only. opp_top_half = opponent finished in the top half of its league."),
    ("PPG with/without", "Regular season only, only when the player started >= 3 and missed >= 3. Small samples: treat as a flag, not evidence."),
    ("Dates", "date_local is Australia/Adelaide. Raw API dates are UTC."),
    ("Emerging Senior", "U21 player in Senior NPL with a Sofascore rating >= 7.0 or xG+xA per 90 >= 0.40."),
    ("Undervalued Performer", "Player on a bottom-half NPL team (min 450 minutes) with a duel win rate >= 60% or pass accuracy >= 80%."),
]


def write_excel(path: Path, sheets: dict):
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        for name, df in sheets.items():
            df.to_excel(xw, sheet_name=name, index=False)
            ws = xw.sheets[name]
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            for i, col in enumerate(df.columns, start=1):
                sample = df[col].astype(str).str.len().quantile(0.9) if len(df) else 0
                width = min(max(len(str(col)), float(sample) if not np.isnan(sample) else 0) + 2, 60)
                ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = width
    print(f"wrote {path} ({path.stat().st_size / 1024:.0f} KB)")


def run_checks(raw, matches, app, season, events):
    print("\n== checks ==")
    n_goal_events = int((events.event_type == "goal").sum())
    n_lineup_goals = int(app.goals.sum() + app.own_goals.sum())
    print(f"goal events {n_goal_events} vs lineup goals incl. OG {n_lineup_goals}: {'OK' if n_goal_events == n_lineup_goals else 'MISMATCH'}")
    ts = app[app.playing & ~app.minutes_estimated].groupby(["match_hash_id", "team_id"]).agg(mins=("minutes", "sum"), ml=("match_len", "first"))
    off = ts[(ts.mins - 11 * ts.ml).abs() > 30]
    print(f"team-sides with recorded subs: {len(ts)}; minutes off from 11x match_len by >30: {len(off)}")
    if len(off):
        print(off.head())
    gk = app[app.playing & app.is_goalkeeper]
    print(f"GK appearances {len(gk)}, clean sheets {int(gk.clean_sheet.sum())}, GK full matches {int(gk.full_match.sum())}")
    sides = app[app.playing].groupby(["match_hash_id", "team_id"]).is_goalkeeper.sum()
    print(f"team-sides: {len(sides)}; with >1 GK playing: {int((sides > 1).sum())}, with 0 GK flagged: {int((sides == 0).sum())}")
    gf = matches.set_index("match_hash_id")
    m = raw["mc"]["am14zEVajd"]
    r = app[(app.match_hash_id == "am14zEVajd") & (app.player_name == "Charlie Linardakis")].iloc[0]
    print(f"GF spot-check: pens {gf.loc['am14zEVajd', 'home_score_pens']}-{gf.loc['am14zEVajd', 'away_score_pens']}, match_len {gf.loc['am14zEVajd', 'match_len']}, "
          f"Linardakis captain={r.is_captain} minutes={r.minutes}; Parobiec goal: {[ (g['minute'], g['penalty_kick'], g['own_goal']) for g in m['goals'] if g['first_name']=='Jayden'][:1]}")
    print(f"season rows {len(season)}, shortlist-eligible {(season.minutes >= MIN_MINUTES).sum()}, hidden gems eligible "
          f"{((season.minutes >= MIN_MINUTES) & (season.grade != 'SEN') & (season.sen_minutes == 0)).sum()}")


def compute(raw_path: Path = RAW, sofa_path: Path = SOFA_ENRICHED) -> dict:
    """Build every table from the raw dump and return them (no files written)."""
    raw = load_raw(raw_path)
    sofa = load_sofascore(sofa_path)
    if sofa:
        print(f"Loaded Sofascore enrichment from {sofa_path}")
    matches = build_matches(raw, sofa)
    ladders = build_ladders(raw)
    events = build_events(raw, matches)
    app = build_appearances(raw, matches, ladders, sofa)
    ctx = build_team_context(matches, app, ladders)
    season = build_player_season(app, ctx, matches, sofa)
    shortlist = build_shortlist(season)
    print(f"matches {len(matches)}, appearances {len(app)} (playing {int(app.playing.sum())}), events {len(events)}, "
          f"ladders {len(ladders)}, teams {len(ctx)}, player-seasons {len(season)}, shortlist {len(shortlist)}")
    notes = pd.DataFrame(NOTES, columns=["topic", "note"])
    return {"raw": raw, "Shortlist": shortlist, "Player Season": season, "Appearances": app, "Team Context": ctx,
            "Matches": matches, "Events": events, "Ladders": ladders, "Notes": notes}


def build(raw_path: Path = RAW, out_path: Path = OUT, check: bool = False) -> dict:
    """compute() + write the workbook and split JSON files."""
    tables = compute(raw_path)
    raw = tables.pop("raw")
    write_excel(out_path, tables)
    for name, key in (("matches", "Matches"), ("appearances", "Appearances"), ("events", "Events"), ("ladders", "Ladders"),
                      ("player_season", "Player Season"), ("shortlist", "Shortlist"), ("team_context", "Team Context")):
        tables[key].to_json(SPLIT_DIR / f"dribl_{name}_2026_v2.json", orient="records", date_format="iso", indent=None)
    print("split JSON written to output/dribl_*_2026_v2.json")
    if check:
        run_checks(raw, tables["Matches"], tables["Appearances"], tables["Player Season"], tables["Events"])
    return tables


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", type=Path, default=RAW)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--check", action="store_true", help="run reconciliation checks after building")
    args = ap.parse_args()
    build(args.raw, args.out, args.check)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Export the scouting tables as compact static files for the Observable Framework site.

    python build_site_data.py            # output/dribl_raw_2026_v2.json -> site/src/data/*

Writes players.csv, shortlist.csv, appearances.csv, matches.csv, teams.csv, ladders.csv,
labels.json (friendly column names), leagues.json (toggle order) and notes.json.
Every exported column must have a LABELS entry; the script asserts it.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

import build_scouting

SITE_DATA = Path("site/src/data")
PROFILES = Path("output/dribl_profiles_2026.json")
CLUBS_CSV = SITE_DATA / "clubs.csv"
DRIBL_PROFILE = "https://fsa.dribl.com/memberprofile?date_range=default&m={id}&season=7MNGzMbmAz&timezone=Australia%2FAdelaide"

# column -> (label, short axis label, description, fmt, higher_is_better, offer as chart metric)
# fmt: int | dec | pct | str | bool | date
LABELS = {
    # identity / context
    "player_id": ("Player ID", "Player ID", "DRIBL user hash id", "str", None, False),
    "player_name": ("Player", "Player", "Player name as recorded in DRIBL", "str", None, False),
    "club": ("Club", "Club", "Club", "str", None, False),
    "team": ("Team", "Team", "Team (club + grade)", "str", None, False),
    "team_id": ("Team ID", "Team ID", "DRIBL team hash id", "str", None, False),
    "league": ("League", "League", "League the row belongs to", "str", None, False),
    "primary_league": ("League", "League", "Regular-season league", "str", None, False),
    "grade": ("Grade", "Grade", "SEN = Seniors, RES = Reserves, U18 = Under 18s", "str", None, False),
    "division": ("Division", "Division", "SL1 = State League 1, SL2 = State League 2", "str", None, False),
    "role": ("Role", "Role", "Goalkeeper or outfield (DRIBL records no other positions)", "str", None, False),
    "jersey": ("Jersey", "#", "Most common shirt number", "str", None, False),
    "is_finals": ("Finals", "Finals", "Finals-series match", "bool", None, False),
    "match_hash_id": ("Match ID", "Match ID", "DRIBL match hash id", "str", None, False),
    "date_local": ("Date", "Date", "Kick-off (Adelaide time)", "date", None, False),
    "round": ("Round", "Round", "Round label", "str", None, False),
    "venue": ("Venue", "Venue", "Ground", "str", None, False),
    "opponent": ("Opponent", "Opponent", "Opposing team", "str", None, False),
    "home_away": ("H/A", "H/A", "Home or away", "str", None, False),
    "result": ("Result", "Result", "W / D / L for the player's team", "str", None, False),
    "team_gf": ("Team goals", "Team GF", "Goals the player's team scored in the match", "int", True, False),
    "team_ga": ("Team conceded", "Team GA", "Goals the player's team conceded in the match", "int", False, False),
    "home_team": ("Home team", "Home", "Home team", "str", None, False),
    "away_team": ("Away team", "Away", "Away team", "str", None, False),
    "home_club": ("Home club", "Home club", "Home club", "str", None, False),
    "away_club": ("Away club", "Away club", "Away club", "str", None, False),
    "home_score": ("Home score", "Home", "Full-time home score", "int", None, False),
    "away_score": ("Away score", "Away", "Full-time away score", "int", None, False),
    "home_score_ht": ("Home HT", "Home HT", "Half-time home score", "int", None, False),
    "away_score_ht": ("Away HT", "Away HT", "Half-time away score", "int", None, False),
    "home_score_pens": ("Home pens", "Home pens", "Penalty shootout score (home)", "int", None, False),
    "away_score_pens": ("Away pens", "Away pens", "Penalty shootout score (away)", "int", None, False),
    "win_status": ("Outcome", "Outcome", "home-win / away-win / draw", "str", None, False),
    "match_len": ("Match length", "Length", "90, or 120 with extra time", "int", None, False),
    "position": ("Ladder position", "Pos", "League ladder position", "int", False, False),
    "played": ("Played", "P", "Matches played", "int", None, False),
    "won": ("Won", "W", "Wins", "int", True, False),
    "drawn": ("Drawn", "D", "Draws", "int", None, False),
    "lost": ("Lost", "L", "Losses", "int", False, False),
    "goals_for": ("Goals for", "GF", "Goals scored", "int", True, False),
    "goals_against": ("Goals against", "GA", "Goals conceded", "int", False, False),
    "goal_difference": ("Goal difference", "GD", "Goals for minus against", "int", True, False),
    "points": ("Points", "Pts", "Ladder points", "int", True, False),
    # volume
    "apps": ("Appearances", "Apps", "Matches actually played", "int", True, True),
    "starts": ("Starts", "Starts", "Matches started", "int", True, True),
    "sub_apps": ("Sub appearances", "Sub apps", "Matches entered from the bench", "int", None, True),
    "bench_unused": ("Bench (unused)", "Unused", "Named in the squad but did not play", "int", False, True),
    "squad_named": ("Squad selections", "Named", "Matches named in the squad (played or not)", "int", True, False),
    "minutes": ("Minutes played", "Minutes", "Derived from start/sub/red-card minutes; U18 minutes are often estimated", "int", True, True),
    "minutes_est_apps": ("Apps with estimated minutes", "Est. apps", "Appearances where sub minutes were not recorded (mostly U18)", "int", False, False),
    "minutes_estimated": ("Minutes estimated", "Est.", "Minutes for this match are estimated (subs not recorded)", "bool", None, False),
    "minutes_share_pct": ("Share of team minutes", "Min share %", "Player minutes as % of all minutes the team could have given one player", "pct", True, True),
    "availability_pct": ("Availability", "Avail %", "Squad selections as % of team matches", "pct", True, True),
    "start_rate_pct": ("Start rate", "Start %", "Starts as % of appearances", "pct", True, True),
    "finals_apps": ("Finals appearances", "Finals apps", "Appearances in finals matches", "int", True, False),
    "starting": ("Started", "Start", "Started the match", "bool", None, False),
    "sub_on_min": ("Sub on", "On", "Minute substituted on", "int", None, False),
    "sub_off_min": ("Sub off", "Off", "Minute substituted off", "int", None, False),
    # output
    "goals": ("Goals", "Goals", "Goals scored (own goals excluded)", "int", True, True),
    "goals_open_play": ("Non-penalty goals", "NP goals", "Goals excluding penalties and own goals", "int", True, True),
    "goals_penalty": ("Penalty goals", "Pens", "Goals from penalty kicks", "int", None, True),
    "own_goals": ("Own goals", "OG", "Own goals conceded", "int", False, True),
    "goals_per90": ("Goals per 90", "Goals/90", "Goals per 90 minutes", "dec", True, True),
    "npg_per90": ("Non-penalty goals per 90", "NP goals/90", "Non-penalty goals per 90 minutes", "dec", True, True),
    "npg_per90_adj": ("Non-penalty goals per 90 (adjusted)", "NP goals/90 adj", "Shrunk toward the league average to discount short bursts", "dec", True, True),
    "team_goal_share_pct": ("Share of team goals", "Team goal %", "Player goals as % of all goals the team scored", "pct", True, True),
    "goals_equaliser": ("Equalisers", "Equalisers", "Goals that levelled the match", "int", True, True),
    "goals_go_ahead": ("Go-ahead goals", "Go-ahead", "Goals that put the team in front", "int", True, True),
    "goals_winner": ("Winning goals", "Winners", "Go-ahead goals after which the team never fell level, in a win", "int", True, True),
    "goals_late": ("Late goals (75'+)", "Late goals", "Goals from the 75th minute on", "int", True, True),
    "goals_consolation": ("Consolation goals", "Consolation", "Goals scored while two or more behind", "int", None, True),
    "goals_away": ("Away goals", "Away goals", "Goals scored away from home", "int", True, True),
    "goals_vs_top_half": ("Goals vs top-half teams", "Goals vs top half", "Goals against opponents that finished in the top half", "int", True, True),
    "goals_as_sub": ("Goals as substitute", "Sub goals", "Goals scored after coming off the bench", "int", True, True),
    "goals_per_sub_90": ("Goals per 90 as substitute", "Sub goals/90", "Goals per 90 minutes of substitute time", "dec", True, True),
    # trust / votes
    "votes": ("Best-on-ground votes", "Votes", "3-2-1 votes recorded per match in DRIBL", "int", True, True),
    "votes_3": ("Best-on-ground (3 votes)", "3-vote games", "Matches with the maximum 3 votes", "int", True, True),
    "votes_per_app": ("Votes per appearance", "Votes/app", "Best-on-ground votes per appearance", "dec", True, True),
    "votes_per_app_adj": ("Votes per appearance (adjusted)", "Votes/app adj", "Shrunk toward the league average", "dec", True, True),
    "captain_apps": ("Captain appearances", "Captain", "Matches as captain", "int", True, True),
    "borrowed_apps": ("Borrowed appearances", "Borrowed", "Matches flagged as borrowed from another team in the club", "int", None, True),
    "borrowed": ("Borrowed", "Borrowed", "Borrowed from another team in the club for this match", "bool", None, False),
    "is_captain": ("Captain", "Capt", "Captain in this match", "bool", None, False),
    "is_goalkeeper": ("Goalkeeper", "GK", "Played as goalkeeper", "bool", None, False),
    # on-pitch
    "gf_on_pitch": ("Team goals while on pitch", "GF on", "Goals the team scored while the player was on", "int", True, True),
    "ga_on_pitch": ("Goals conceded while on pitch", "GA on", "Goals the team conceded while the player was on", "int", False, True),
    "gd_on_pitch_per90": ("Team goal difference per 90 on pitch", "GD/90 on", "Team goal difference per 90 while the player was on", "dec", True, True),
    "gd_on_pitch_vs_team": ("On-pitch goal difference vs team", "GD vs team", "GD/90 with the player on, minus the team's regular-season GD per match", "dec", True, True),
    "ga_on_pitch_per90": ("Goals conceded per 90 on pitch", "GA/90 on", "Goals conceded per 90 while on", "dec", False, True),
    "ga_on_pitch_vs_team": ("Goals conceded vs team average", "GA vs team", "GA/90 with the player on, minus the team's GA per match", "dec", False, True),
    "clean_sheets": ("Clean sheets", "Clean sheets", "Full matches with no goal conceded while on (GK and outfield)", "int", True, True),
    "clean_sheet": ("Clean sheet", "CS", "No goals conceded while on, full match", "bool", None, False),
    "full_matches": ("Full matches", "Full", "Matches played start to finish", "int", True, True),
    "clean_sheet_pct": ("Clean sheet rate", "CS %", "Clean sheets as % of full matches", "pct", True, True),
    # discipline
    "yellow_cards": ("Yellow cards", "Yellows", "Yellow cards", "int", False, True),
    "red_cards": ("Red cards", "Reds", "Red cards", "int", False, True),
    "yellows_per90": ("Yellow cards per 90", "Yellows/90", "Yellow cards per 90 minutes", "dec", False, True),
    # team effect
    "ppg_when_playing": ("Team points per game when playing", "PPG playing", "Team points per game in matches the player played", "dec", True, True),
    "ppg_start_diff": ("Team PPG: starts vs not", "PPG diff", "Team points per game when the player starts minus when they don't (regular season, min 3 each)", "dec", True, True),
    "team_ladder_pos": ("Team ladder position", "Team pos", "Team's regular-season ladder position", "int", False, True),
    "ladder_teams": ("Teams in league", "Teams", "Number of teams in the league", "int", None, False),
    "team_ppg": ("Team points per game", "Team PPG", "Team's regular-season points per game", "dec", True, True),
    "team_matches": ("Team matches", "Team matches", "Matches the team played", "int", None, False),
    # pathway
    "grades_played": ("Grades played", "Grades", "All grades the player appeared in this season", "str", None, False),
    "highest_grade": ("Highest grade", "Highest", "Highest grade played this season", "str", None, False),
    "u18_player": ("U18 player", "U18", "Appeared in an Under 18 league (only age signal available)", "bool", None, False),
    "hidden_gem": ("Hidden gem", "Gem", "Reserves/U18 row with zero senior minutes all season", "bool", None, False),
    "sen_minutes": ("Senior minutes (all teams)", "Senior min", "Minutes at senior grade across all teams", "int", True, True),
    "res_minutes": ("Reserves minutes (all teams)", "Res min", "Minutes at reserves grade across all teams", "int", None, True),
    "u18_minutes": ("U18 minutes (all teams)", "U18 min", "Minutes at U18 grade across all teams", "int", None, True),
    "sen_apps": ("Senior appearances", "Senior apps", "Appearances at senior grade", "int", True, True),
    "n_teams": ("Teams played for", "Teams", "Distinct teams this season", "int", None, True),
    "borrowed_apps_all": ("Borrowed appearances (all teams)", "Borrowed all", "Borrowed flags across all teams", "int", None, True),
    # profile
    "age": ("Age", "Age", "Age as shown on the DRIBL member profile at extraction time", "int", None, True),
    "nationality": ("Nationality", "Nat.", "Nationality recorded in DRIBL", "str", None, False),
    "flag": ("Flag", "Flag", "Flag emoji for the recorded nationality", "str", None, False),
    "borrowed_side": ("Borrowed", "Borrowed", "DRIBL listed the player as borrowed for this match", "bool", None, False),
    "headshot": ("Photo", "Photo", "DRIBL profile photo URL", "str", None, False),
    "dribl_url": ("DRIBL profile", "DRIBL", "Link to the player's public DRIBL member profile", "str", None, False),
    "club_slug": ("Club key", "Club key", "Crest file key", "str", None, False),
    "club_color": ("Club colour", "Colour", "Primary club colour from DRIBL", "str", None, False),
    "club_accent": ("Club accent", "Accent", "Accent club colour from DRIBL", "str", None, False),
    "season": ("Season", "Season", "Season name", "str", None, False),
    "clubs": ("Clubs", "Clubs", "Clubs that season", "str", None, False),
    "leagues": ("Leagues", "Leagues", "Leagues / competitions that season", "str", None, False),
    "started": ("Started", "Started", "Matches started", "int", True, False),
    "was_goalkeeper": ("Goalkeeper", "GK", "Played as goalkeeper that season", "bool", None, False),
    "date": ("Date", "Date", "Match date (Adelaide)", "date", None, False),
    "comp": ("Competition", "Comp", "Competition name", "str", None, False),
    "full_round": ("Round", "Round", "Round label", "str", None, False),
    "side": ("Side", "Side", "home or away", "str", None, False),
    "score": ("Score", "Score", "Home – away full-time score", "str", None, False),
    "did_play": ("Played", "Played", "Took part in the match", "bool", None, False),
    "in_dataset": ("In SL dataset", "In SL", "Match is one of the SL1/SL2 fixtures in this site's dataset", "bool", None, False),
    "code": ("Club code", "Code", "DRIBL club code", "str", None, False),
    "slug": ("Club key", "Key", "Crest file key", "str", None, False),
    "crest": ("Crest", "Crest", "Crest image path", "str", None, False),
    "logo_url": ("Crest URL", "Crest URL", "Source crest URL on DRIBL", "str", None, False),
    # shortlist
    "rank_in_role": ("Rank", "Rank", "Rank within role by gem score", "int", False, False),
    "gem_score": ("Gem score", "Gem score", "Scout score plus bonuses for no senior minutes and U18", "dec", True, True),
    "scout_score": ("Scout score", "Scout score", "League-adjusted composite of output, votes, on-pitch effect and minutes", "dec", True, True),
    "why_flagged": ("Why flagged", "Why", "Plain-English reasons this player stands out", "str", None, False),
    # teams
    "matches": ("Matches", "Matches", "Matches played (incl. finals)", "int", None, False),
    "rr_matches": ("Regular-season matches", "RR matches", "Regular-season matches", "int", None, False),
    "ppg": ("Points per game", "PPG", "Regular-season points per game", "dec", True, True),
    "gf_per_match": ("Goals for per match", "GF/match", "Regular-season goals scored per match", "dec", True, True),
    "ga_per_match": ("Goals against per match", "GA/match", "Regular-season goals conceded per match", "dec", False, True),
    "gd_per_match": ("Goal difference per match", "GD/match", "Regular-season goal difference per match", "dec", True, True),
    "ladder_pos": ("Ladder position", "Pos", "Regular-season ladder position", "int", False, True),
    "players_used": ("Players used", "Used", "Distinct players who played", "int", None, True),
    "borrowed_in_apps": ("Borrowed-in appearances", "Borrowed in", "Appearances by players borrowed from other teams in the club", "int", None, True),
    "borrowed_in_players": ("Borrowed-in players", "Borrowed players", "Distinct borrowed players", "int", None, True),
    "gf": ("Goals for", "GF", "Goals scored (all matches)", "int", True, False),
    "ga": ("Goals against", "GA", "Goals conceded (all matches)", "int", False, False),
}

PLAYER_COLS = ["player_id", "player_name", "club", "team", "team_id", "league", "grade", "division", "role", "jersey",
               "apps", "starts", "sub_apps", "bench_unused", "squad_named", "minutes", "minutes_est_apps", "minutes_share_pct",
               "availability_pct", "start_rate_pct", "finals_apps",
               "goals", "goals_open_play", "goals_penalty", "own_goals", "goals_per90", "npg_per90", "team_goal_share_pct",
               "goals_equaliser", "goals_go_ahead", "goals_winner", "goals_late", "goals_consolation", "goals_away",
               "goals_vs_top_half", "goals_as_sub", "goals_per_sub_90",
               "votes", "votes_3", "votes_per_app", "captain_apps", "borrowed_apps",
               "gf_on_pitch", "ga_on_pitch", "gd_on_pitch_per90", "gd_on_pitch_vs_team", "ga_on_pitch_per90", "ga_on_pitch_vs_team",
               "clean_sheets", "full_matches", "clean_sheet_pct", "yellow_cards", "red_cards", "yellows_per90",
               "ppg_when_playing", "ppg_start_diff", "team_ladder_pos", "ladder_teams", "team_ppg", "team_matches",
               "grades_played", "highest_grade", "u18_player", "hidden_gem", "sen_minutes", "res_minutes", "u18_minutes",
               "sen_apps", "n_teams", "borrowed_apps_all",
               "age", "nationality", "flag", "headshot", "dribl_url", "club_slug", "club_color", "club_accent"]
CAREER_COLS = ["player_id", "season", "clubs", "leagues", "played", "started", "minutes", "goals", "yellow_cards", "red_cards",
               "votes", "clean_sheets", "was_goalkeeper"]
MEMBER_MATCH_COLS = ["player_id", "date", "comp", "league", "full_round", "home_team", "away_team", "home_club", "away_club",
                     "home_score", "away_score", "score", "side", "result", "borrowed_side", "did_play", "starting", "minutes", "goals",
                     "yellow_cards", "red_cards", "votes", "is_captain", "is_goalkeeper", "clean_sheet", "match_hash_id", "in_dataset"]
SHORTLIST_COLS = ["rank_in_role", "role", "player_id", "team_id", "player_name", "club", "team", "league", "grade", "division",
                  "u18_player", "highest_grade", "hidden_gem", "gem_score", "scout_score", "why_flagged", "age",
                  "apps", "starts", "minutes", "minutes_share_pct", "goals", "goals_open_play", "npg_per90", "npg_per90_adj",
                  "team_goal_share_pct", "goals_go_ahead", "goals_winner", "goals_late", "votes", "votes_per_app",
                  "votes_per_app_adj", "gd_on_pitch_vs_team", "ga_on_pitch_per90", "clean_sheets", "clean_sheet_pct",
                  "yellow_cards", "red_cards", "sen_minutes", "borrowed_apps", "team_ladder_pos", "ladder_teams", "minutes_est_apps"]
APPEARANCE_COLS = ["player_id", "team_id", "match_hash_id", "date_local", "round", "league", "is_finals", "opponent", "home_away",
                   "result", "team_gf", "team_ga", "starting", "sub_on_min", "sub_off_min", "minutes", "minutes_estimated",
                   "goals", "goals_open_play", "goals_penalty", "own_goals", "votes", "yellow_cards", "red_cards", "borrowed",
                   "is_captain", "is_goalkeeper", "gf_on_pitch", "ga_on_pitch", "clean_sheet"]
MATCH_COLS = ["match_hash_id", "league", "grade", "division", "is_finals", "date_local", "round", "venue", "home_team", "away_team",
              "home_club", "away_club", "home_score", "away_score", "home_score_ht", "away_score_ht", "home_score_pens",
              "away_score_pens", "win_status", "match_len"]
TEAM_COLS = ["team_id", "team", "club", "primary_league", "grade", "division", "matches", "rr_matches", "ppg", "gf_per_match",
             "ga_per_match", "gd_per_match", "ladder_pos", "ladder_teams", "players_used", "borrowed_in_apps", "borrowed_in_players",
             "gf", "ga"]
LADDER_COLS = ["league", "grade", "division", "is_finals", "position", "team_id", "team", "club", "played", "won", "drawn", "lost",
               "goals_for", "goals_against", "goal_difference", "points"]

GRADE_ORDER = {"SEN": 0, "RES": 1, "U18": 2}


def tidy(df: pd.DataFrame, cols: list, bool_as_text: bool = True) -> pd.DataFrame:
    out = df[cols].copy()
    for c in out.columns:
        if out[c].dtype == bool or LABELS.get(c, (None,) * 4)[3] == "bool":
            if not bool_as_text:
                out[c] = out[c].map(lambda v: None if v is None or (isinstance(v, float) and np.isnan(v)) else bool(v))
                continue
            out[c] = out[c].map(lambda v: "" if v is None or (isinstance(v, float) and np.isnan(v)) else ("true" if v else "false"))
            continue
        if out[c].dtype.kind == "f":
            fmt = LABELS[c][3]
            if fmt == "int":
                out[c] = out[c].round().astype("Int64")
            else:
                out[c] = out[c].round(2)
        if "date" in c and out[c].dtype.kind in "M":
            out[c] = out[c].dt.strftime("%Y-%m-%d %H:%M")
    return out


def league_order(leagues: pd.DataFrame) -> list:
    rows = []
    for _, r in leagues.iterrows():
        name = r["league"]
        region = "North" if "North" in name else "South" if "South" in name else ""
        rows.append({"league": name, "division": r["division"], "grade": r["grade"], "region": region,
                     "is_finals": bool(r["is_finals"]),
                     "short": name.replace("HPG Homes State League ", "SL").replace(" - ", " ").replace("Under 18's", "U18")
                                  .replace("Finals Series", "Finals").replace("Final Series", "Finals")})
    rows.sort(key=lambda r: (r["is_finals"], r["division"], r["region"], GRADE_ORDER[r["grade"]]))
    return rows


DEMONYM_ISO = {
    "australian": "AU", "australia": "AU", "afghan": "AF", "british, uk": "GB", "british": "GB", "english": "GB", "scottish": "GB",
    "welsh": "GB", "italian": "IT", "greek, hellenic": "GR", "greek": "GR", "burundian": "BI", "congolese": "CD", "japanese": "JP",
    "liberian": "LR", "south sudanese": "SS", "new zealand, nz": "NZ", "new zealander": "NZ", "albanian": "AL", "south korean": "KR",
    "korean": "KR", "nepali, nepalese": "NP", "nepalese": "NP", "nigerian": "NG", "lebanese": "LB", "burmese": "MM", "sudanese": "SD",
    "syrian": "SY", "american": "US", "iranian, persian": "IR", "iranian": "IR", "brazilian": "BR", "zimbabwean": "ZW", "ethiopian": "ET",
    "serbian": "RS", "vietnamese": "VN", "iraqi": "IQ", "argentine": "AR", "argentinian": "AR", "south african": "ZA", "croatian": "HR",
    "tanzanian": "TZ", "pakistani": "PK", "indian": "IN", "somali, somalian": "SO", "somali": "SO", "ni-vanuatu, vanuatuan": "VU",
    "eritrean": "ER", "irish": "IE", "ukrainian": "UA", "indonesian": "ID", "guinean": "GN", "ghanaian": "GH", "kenyan": "KE",
    "bosnian or herzegovinian": "BA", "bosnian": "BA", "canadian": "CA", "palestinian": "PS", "cambodian": "KH", "russian": "RU",
    "philippine, filipino": "PH", "filipino": "PH", "cypriot": "CY", "polish": "PL", "german": "DE", "malaysian": "MY", "chilean": "CL",
    "spanish": "ES", "egyptian": "EG", "dutch, netherlandic": "NL", "dutch": "NL", "french": "FR", "portuguese": "PT", "turkish": "TR",
    "macedonian": "MK", "hungarian": "HU", "romanian": "RO", "bulgarian": "BG", "colombian": "CO", "mexican": "MX", "peruvian": "PE",
    "uruguayan": "UY", "venezuelan": "VE", "chinese": "CN", "thai": "TH", "sri lankan": "LK", "bangladeshi": "BD", "singaporean": "SG",
    "fijian": "FJ", "samoan": "WS", "tongan": "TO", "papua new guinean": "PG", "maltese": "MT", "swedish": "SE", "norwegian": "NO",
    "danish": "DK", "finnish": "FI", "belgian": "BE", "swiss": "CH", "austrian": "AT", "czech": "CZ", "slovak": "SK", "slovenian": "SI",
    "montenegrin": "ME", "kosovar": "XK", "moroccan": "MA", "algerian": "DZ", "tunisian": "TN", "libyan": "LY", "jordanian": "JO",
    "saudi, saudi arabian": "SA", "emirati": "AE", "israeli": "IL", "armenian": "AM", "georgian": "GE", "kazakh": "KZ", "uzbek": "UZ",
    "cameroonian": "CM", "ivorian": "CI", "senegalese": "SN", "malian": "ML", "sierra leonean": "SL", "togolese": "TG", "ugandan": "UG",
    "rwandan": "RW", "zambian": "ZM", "malawian": "MW", "mozambican": "MZ", "angolan": "AO", "namibian": "NA", "botswanan": "BW",
    "jamaican": "JM", "trinidadian": "TT", "cuban": "CU", "dominican": "DO", "haitian": "HT", "salvadoran": "SV", "guatemalan": "GT",
    "honduran": "HN", "costa rican": "CR", "panamanian": "PA", "ecuadorian": "EC", "bolivian": "BO", "paraguayan": "PY",
    "taiwanese": "TW", "mongolian": "MN", "bhutanese": "BT", "maldivian": "MV", "laotian": "LA", "timorese": "TL", "kurdish": "",
}


def flag_of(nationality) -> str:
    if not nationality:
        return ""
    code = DEMONYM_ISO.get(str(nationality).strip().lower(), "")
    return "".join(chr(0x1F1E6 + ord(c) - 65) for c in code) if len(code) == 2 else ""


def slugify(name: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")


def load_profiles():
    if not PROFILES.exists():
        print(f"WARNING: {PROFILES} not found — ages, headshots, careers and cup matches will be empty")
        return {}, {}, {}
    d = json.load(open(PROFILES))
    return d.get("profiles", {}), d.get("careers", {}), d.get("member_matches", {})


def profile_frame(profiles: dict) -> pd.DataFrame:
    rows = []
    for pid, p in profiles.items():
        clubs = p.get("player_clubs") or []
        rows.append({"player_id": pid, "age": p.get("age"), "nationality": p.get("nationality"), "flag": flag_of(p.get("nationality")), "headshot": p.get("image"),
                     "dribl_url": DRIBL_PROFILE.format(id=pid),
                     "_club_colors": {c.get("name"): (c.get("color"), c.get("accent")) for c in clubs}})
    return pd.DataFrame(rows)


def career_frame(careers: dict) -> pd.DataFrame:
    rows = []
    for pid, seasons in careers.items():
        for c in seasons:
            rows.append({"player_id": pid, "season": c.get("season_name"), "clubs": "; ".join(c.get("club_names") or []),
                         "leagues": "; ".join(dict.fromkeys(str(l.get("league_name")) for l in (c.get("leagues") or []))),
                         "played": c.get("played"), "started": c.get("started"), "minutes": c.get("minutes"), "goals": c.get("goals"),
                         "yellow_cards": c.get("yellow_cards"), "red_cards": c.get("red_cards"), "votes": c.get("votes"),
                         "clean_sheets": c.get("clean_sheets"), "was_goalkeeper": bool(c.get("was_goalkeeper"))})
    return pd.DataFrame(rows).sort_values(["player_id", "season"])


def member_match_frame(member_matches: dict, known_matches: set, player_teams: dict, player_clubs: dict) -> pd.DataFrame:
    """player_teams/player_clubs: player_id -> set of team ids / club names from the SL dataset. DRIBL sets side='borrowed'
    for borrowed players, so the side is resolved from the player's known teams, then clubs."""
    rows = []
    strip = lambda t: str(t or "").replace(" Male", "").replace(" Female", "")
    for pid, ms in member_matches.items():
        teams, clubs = player_teams.get(pid, set()), player_clubs.get(pid, set())
        for m in ms:
            hs, as_ = m.get("home_score"), m.get("away_score")
            side = m.get("side")
            borrowed_side = side == "borrowed"
            if side not in ("home", "away"):
                h_t, a_t = m.get("home_team_hash_id"), m.get("away_team_hash_id")
                h_c, a_c = m.get("home_club_name"), m.get("away_club_name")
                if h_t in teams and a_t not in teams:
                    side = "home"
                elif a_t in teams and h_t not in teams:
                    side = "away"
                elif h_c in clubs and a_c not in clubs:
                    side = "home"
                elif a_c in clubs and h_c not in clubs:
                    side = "away"
                else:
                    side = None
            if hs is None or as_ is None or side not in ("home", "away"):
                result = ""
            else:
                own, opp = (hs, as_) if side == "home" else (as_, hs)
                result = "W" if own > opp else "D" if own == opp else "L"
            date = pd.to_datetime(m.get("date"), utc=True, errors="coerce")
            rows.append({"player_id": pid, "date": date.tz_convert("Australia/Adelaide").strftime("%Y-%m-%d %H:%M") if pd.notna(date) else "",
                         "comp": m.get("comp_name"), "league": m.get("league_name"), "full_round": m.get("full_round") or m.get("round"),
                         "home_team": strip(m.get("home_team_name")), "away_team": strip(m.get("away_team_name")),
                         "home_club": m.get("home_club_name"), "away_club": m.get("away_club_name"),
                         "home_score": hs, "away_score": as_, "score": f"{hs}–{as_}" if hs is not None and as_ is not None else "",
                         "side": side, "result": result, "borrowed_side": borrowed_side, "did_play": bool(m.get("played")), "starting": bool(m.get("started")),
                         "minutes": m.get("minutes"), "goals": m.get("goals"), "yellow_cards": m.get("yellow_card_count"),
                         "red_cards": m.get("red_card_count"), "votes": m.get("votes"), "is_captain": bool(m.get("is_captain")),
                         "is_goalkeeper": bool(m.get("is_goalkeeper")), "clean_sheet": bool(m.get("clean_sheet")),
                         "match_hash_id": m.get("match_hash_id"), "in_dataset": m.get("match_hash_id") in known_matches})
    return pd.DataFrame(rows).sort_values(["player_id", "date"])


def main():
    tables = build_scouting.compute()
    profiles, careers, member_matches = load_profiles()
    season, shortlist, app = tables["Player Season"], tables["Shortlist"], tables["Appearances"]
    matches, ctx, ladders = tables["Matches"], tables["Team Context"], tables["Ladders"]

    season = season.copy()
    season["hidden_gem"] = (season.grade != "SEN") & (season.sen_minutes == 0)
    season["role"] = season.role.fillna("Outfield")
    app_play = app[app.playing]

    # profile fields: age, nationality, headshot, DRIBL link, club colours; crest key from clubs.csv
    for c in ("age", "nationality", "flag", "headshot", "dribl_url", "club_color", "club_accent"):
        season[c] = None
    if profiles:
        pf = profile_frame(profiles).set_index("player_id")
        season = season.join(pf.drop(columns=["_club_colors"]), on="player_id", rsuffix="_p")
        for c in ("age", "nationality", "flag", "headshot", "dribl_url"):
            season[c] = season.pop(f"{c}_p")
        colors = season.apply(lambda r: (pf.loc[r.player_id, "_club_colors"].get(r.club) if r.player_id in pf.index else None) or (None, None), axis=1)
        season["club_color"] = [c[0] for c in colors]
        season["club_accent"] = [c[1] for c in colors]
    season["club_slug"] = season.club.map(slugify)
    shortlist = shortlist.merge(season[["player_id", "team_id", "age"]], on=["player_id", "team_id"], how="left")

    SITE_DATA.mkdir(parents=True, exist_ok=True)
    exports = {
        "players.csv": tidy(season, PLAYER_COLS),
        "shortlist.csv": tidy(shortlist, SHORTLIST_COLS),
        "appearances.parquet": tidy(app_play, APPEARANCE_COLS, bool_as_text=False),
        "matches.csv": tidy(matches, MATCH_COLS),
        "teams.csv": tidy(ctx, TEAM_COLS),
        "ladders.csv": tidy(ladders, LADDER_COLS),
    }
    if careers:
        exports["careers.csv"] = tidy(career_frame(careers), CAREER_COLS)
    if member_matches:
        player_teams = app_play.groupby("player_id").team_id.agg(set).to_dict()
        player_clubs = app_play.groupby("player_id").club.agg(set).to_dict()
        exports["member_matches.parquet"] = tidy(member_match_frame(member_matches, set(matches.match_hash_id), player_teams, player_clubs), MEMBER_MATCH_COLS, bool_as_text=False)
    for name, df in exports.items():
        missing = [c for c in df.columns if c not in LABELS]
        assert not missing, f"{name}: no LABELS entry for {missing}"
        if name.endswith(".parquet"):
            df.to_parquet(SITE_DATA / name, index=False)
        else:
            df.to_csv(SITE_DATA / name, index=False)
        print(f"{name}: {len(df)} rows x {len(df.columns)} cols, {(SITE_DATA / name).stat().st_size / 1e6:.2f} MB")

    labels = {c: {"label": v[0], "short": v[1], "desc": v[2], "fmt": v[3], "higher_is_better": v[4], "metric": v[5]}
              for c, v in LABELS.items()}
    (SITE_DATA / "labels.json").write_text(json.dumps(labels, indent=1))

    leagues = matches[["league", "division", "grade"]].drop_duplicates("league")
    leagues["is_finals"] = leagues.league.str.contains("Final")
    (SITE_DATA / "leagues.json").write_text(json.dumps(league_order(leagues), indent=1))
    (SITE_DATA / "notes.json").write_text(json.dumps([{"topic": t, "note": n} for t, n in build_scouting.NOTES], indent=1))
    meta = {"extracted_at": tables["raw"].get("extracted_at"), "season": "2026", "matches": len(matches),
            "profiles": len(profiles), "with_age": int(season.age.notna().sum()) if "age" in season else 0,
            "players": int(season.player_id.nunique()), "player_seasons": len(season), "teams": len(ctx),
            "appearances": len(app_play), "leagues": len(leagues)}
    (SITE_DATA / "meta.json").write_text(json.dumps(meta, indent=1))
    print("labels.json, leagues.json, notes.json, meta.json written;", meta)


if __name__ == "__main__":
    main()

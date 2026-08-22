# utils/situational.py
import requests
import numpy as np
import pandas as pd
import streamlit as st
from concurrent.futures import ThreadPoolExecutor

LEONES_TEAM_ID = 695

def parse_game_plate_appearances(game_pk: int) -> list[dict]:
    """Extrae todas las apariciones al plato con contexto situacional."""
    url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
    try:
        res = requests.get(url, timeout=20)
        if res.status_code != 200:
            return []
        data = res.json()
        
        plays = data.get("liveData", {}).get("plays", {}).get("allPlays", [])
        game_date = data.get("gameData", {}).get("datetime", {}).get("originalDate", "")
        home_team = data.get("gameData", {}).get("teams", {}).get("home", {}).get("name", "Home")
        away_team = data.get("gameData", {}).get("teams", {}).get("away", {}).get("name", "Away")
        home_id = data.get("gameData", {}).get("teams", {}).get("home", {}).get("id")
        away_id = data.get("gameData", {}).get("teams", {}).get("away", {}).get("id")
        
        records = []
        for play in plays:
            matchup = play.get("matchup", {})
            batter = matchup.get("batter", {})
            pitcher = matchup.get("pitcher", {})
            bat_side = matchup.get("batSide", {}).get("code", "R")
            pitch_hand = matchup.get("pitchHand", {}).get("code", "R")
            
            about = play.get("about", {})
            inning = about.get("inning", 1)
            half = about.get("halfInning", "top")
            
            batter_team_id = away_id if half == "top" else home_id
            pitcher_team_id = home_id if half == "top" else away_id
            batter_team_name = away_team if half == "top" else home_team
            opposing_team_name = home_team if half == "top" else away_team
            
            result = play.get("result", {})
            event = result.get("event", "Out")
            rbi = result.get("rbi", 0)
            desc = result.get("description", "")
            
            # Situación de corredores antes de la jugada
            # runners list
            runners = play.get("runners", [])
            origin_bases = [r.get("movement", {}).get("originBase") for r in runners if r.get("movement", {}).get("originBase")]
            
            runner_1b = "1B" in origin_bases
            runner_2b = "2B" in origin_bases
            runner_3b = "3B" in origin_bases
            
            is_bases_empty = (not runner_1b and not runner_2b and not runner_3b)
            is_risp = (runner_2b or runner_3b)
            is_bases_loaded = (runner_1b and runner_2b and runner_3b)
            
            # Outs antes de la jugada
            count = play.get("count", {})
            outs = count.get("outs", 0)
            is_2_outs = (outs == 2)
            is_2_outs_risp = (is_2_outs and is_risp)
            
            # Inning bucket
            if inning <= 3:
                inning_bucket = "Inicios (1-3)"
            elif inning <= 6:
                inning_bucket = "Medio (4-6)"
            else:
                inning_bucket = "Finales/Clutch (7-9+)"
                
            # Identificar hit, turno oficial, boleto, etc.
            is_hit = event in ["Single", "Double", "Triple", "Home Run"]
            is_single = (event == "Single")
            is_double = (event == "Double")
            is_triple = (event == "Triple")
            is_hr = (event == "Home Run")
            is_walk = event in ["Walk", "Intent Walk"]
            is_strikeout = event in ["Strikeout", "Strikeout Looking"]
            is_sac = event in ["Sac Fly", "Sac Bunt", "Sac Fly Double Play"]
            is_hbp = (event == "Hit By Pitch")
            
            # Turno Oficial al Bate (AB) excluye BB, HBP, SAC, interferencias
            is_ab = not (is_walk or is_hbp or is_sac or "Interference" in event)
            is_pa = True
            
            records.append({
                "game_pk": game_pk,
                "game_date": game_date,
                "home_team": home_team,
                "away_team": away_team,
                "inning": inning,
                "half": half,
                "inning_bucket": inning_bucket,
                "batter_id": batter.get("id"),
                "batter_name": batter.get("fullName", "Desconocido"),
                "batter_team_id": batter_team_id,
                "is_batter_leones": (batter_team_id == LEONES_TEAM_ID),
                "bat_side": bat_side,
                "pitcher_id": pitcher.get("id"),
                "pitcher_name": pitcher.get("fullName", "Desconocido"),
                "pitcher_team_id": pitcher_team_id,
                "is_pitcher_leones": (pitcher_team_id == LEONES_TEAM_ID),
                "opposing_team": opposing_team_name,
                "pitch_hand": pitch_hand,
                "event": event,
                "rbi": rbi,
                "description": desc,
                "outs": outs,
                "is_2_outs": is_2_outs,
                "runner_1b": runner_1b,
                "runner_2b": runner_2b,
                "runner_3b": runner_3b,
                "is_bases_empty": is_bases_empty,
                "is_risp": is_risp,
                "is_bases_loaded": is_bases_loaded,
                "is_2_outs_risp": is_2_outs_risp,
                "is_pa": is_pa,
                "is_ab": is_ab,
                "is_hit": is_hit,
                "is_single": is_single,
                "is_double": is_double,
                "is_triple": is_triple,
                "is_hr": is_hr,
                "is_walk": is_walk,
                "is_strikeout": is_strikeout,
                "is_sac": is_sac,
                "is_hbp": is_hbp
            })
        return records
    except Exception:
        return []


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_season_situational_data(season: int, team_id: int = LEONES_TEAM_ID) -> pd.DataFrame:
    """Descarga todas las apariciones al plato de la temporada para análisis situacional."""
    sched_url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=17&leagueId=135&season={season}&teamId={team_id}"
    try:
        res = requests.get(sched_url, timeout=30)
        if res.status_code != 200:
            return pd.DataFrame()
        sched_data = res.json()
    except Exception:
        return pd.DataFrame()
        
    game_pks = []
    for d in sched_data.get("dates", []):
        for g in d.get("games", []):
            if g.get("status", {}).get("detailedState") in ["Final", "Completed Early", "Game Over"]:
                game_pks.append(g["gamePk"])
                
    if not game_pks:
        return pd.DataFrame()
        
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(parse_game_plate_appearances, game_pks))
        
    all_records = [item for sublist in results for item in sublist]
    if not all_records:
        return pd.DataFrame()
        
    return pd.DataFrame(all_records)


def summarize_slash_line(df: pd.DataFrame) -> dict:
    """Calcula la línea estadística clásica (PA, AB, H, 2B, 3B, HR, BB, SO, RBI, AVG, OBP, SLG, OPS)."""
    if df.empty:
        return {
            "PA": 0, "AB": 0, "H": 0, "2B": 0, "3B": 0, "HR": 0,
            "BB": 0, "SO": 0, "RBI": 0, "AVG": ".000", "OBP": ".000", "SLG": ".000", "OPS": ".000"
        }
        
    pa = int(df["is_pa"].sum())
    ab = int(df["is_ab"].sum())
    h = int(df["is_hit"].sum())
    h2b = int(df["is_double"].sum())
    h3b = int(df["is_triple"].sum())
    hr = int(df["is_hr"].sum())
    h1b = h - (h2b + h3b + hr)
    bb = int(df["is_walk"].sum())
    so = int(df["is_strikeout"].sum())
    rbi = int(df["rbi"].sum())
    hbp = int(df["is_hbp"].sum())
    sac = int(df["is_sac"].sum())
    
    avg_num = (h / ab) if ab > 0 else 0.0
    obp_num = ((h + bb + hbp) / (ab + bb + hbp + sac)) if (ab + bb + hbp + sac) > 0 else 0.0
    tb = (h1b + 2 * h2b + 3 * h3b + 4 * hr)
    slg_num = (tb / ab) if ab > 0 else 0.0
    ops_num = obp_num + slg_num
    
    return {
        "PA": pa, "AB": ab, "H": h, "2B": h2b, "3B": h3b, "HR": hr,
        "BB": bb, "SO": so, "RBI": rbi,
        "AVG_num": avg_num, "OBP_num": obp_num, "SLG_num": slg_num, "OPS_num": ops_num,
        "AVG": f"{avg_num:.3f}".replace("0.", "."),
        "OBP": f"{obp_num:.3f}".replace("0.", "."),
        "SLG": f"{slg_num:.3f}".replace("0.", "."),
        "OPS": f"{ops_num:.3f}".replace("0.", ".")
    }


def compute_all_situational_splits(df_subject: pd.DataFrame) -> pd.DataFrame:
    """Calcula y compara los splits situacionales clave."""
    splits = [
        ("Total Acumulado", df_subject),
        ("Bases Limpias", df_subject[df_subject["is_bases_empty"] == True]),
        ("Hombres en Posición Anotadora (RISP)", df_subject[df_subject["is_risp"] == True]),
        ("RISP con 2 Outs (Clutch)", df_subject[df_subject["is_2_outs_risp"] == True]),
        ("Bases Llenas", df_subject[df_subject["is_bases_loaded"] == True]),
        ("vs Lanzadores Derechos (RHP)", df_subject[df_subject["pitch_hand"] == "R"]),
        ("vs Lanzadores Zurdos (LHP)", df_subject[df_subject["pitch_hand"] == "L"]),
        ("Entradas Tempranas (1-3)", df_subject[df_subject["inning_bucket"] == "Inicios (1-3)"]),
        ("Entradas Medias (4-6)", df_subject[df_subject["inning_bucket"] == "Medio (4-6)"]),
        ("Entradas Tardías / Clutch (7-9+)", df_subject[df_subject["inning_bucket"] == "Finales/Clutch (7-9+)"])
    ]
    
    rows = []
    for name, sub in splits:
        if not sub.empty:
            st_dict = summarize_slash_line(sub)
            st_dict["Situación"] = name
            rows.append(st_dict)
            
    if not rows:
        return pd.DataFrame()
        
    res_df = pd.DataFrame(rows)
    cols = ["Situación", "PA", "AB", "H", "2B", "3B", "HR", "BB", "SO", "RBI", "AVG", "OBP", "SLG", "OPS"]
    return res_df[cols]


def compute_bvp_summary(df_pas: pd.DataFrame, batter_id: int = None, pitcher_id: int = None) -> pd.DataFrame:
    """Calcula la tabla de enfrentamientos cara a cara BvP."""
    if batter_id:
        sub = df_pas[df_pas["batter_id"] == batter_id]
        group_col = "pitcher_name"
        label_col = "Lanzador Rival"
    elif pitcher_id:
        sub = df_pas[df_pas["pitcher_id"] == pitcher_id]
        group_col = "batter_name"
        label_col = "Bateador Rival"
    else:
        return pd.DataFrame()
        
    rows = []
    for rival, group in sub.groupby(group_col):
        st_dict = summarize_slash_line(group)
        st_dict[label_col] = rival
        st_dict["Equipo Rival"] = group["opposing_team"].iloc[0] if "opposing_team" in group else ""
        rows.append(st_dict)
        
    if not rows:
        return pd.DataFrame()
        
    res_df = pd.DataFrame(rows).sort_values("PA", ascending=False)
    cols = [label_col, "Equipo Rival", "PA", "AB", "H", "2B", "3B", "HR", "BB", "SO", "RBI", "AVG", "OBP", "SLG", "OPS"]
    return res_df[cols]

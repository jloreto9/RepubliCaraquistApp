"""
Backfill ELO por temporada y fase usando juegos ya guardados en Supabase.

Uso:
  python scripts/backfill_elo.py --season 2025 --reset
  python scripts/backfill_elo.py --season 2025 --phases regular,round_robin
"""

import argparse
import os
import sys
from datetime import datetime

from supabase import create_client

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.elo import BASE_ELO, HOME_ADVANTAGE, K_BY_PHASE, update_elo

VALID_PHASES = ["regular", "wildcard_playin", "round_robin", "final"]


def parse_args():
    parser = argparse.ArgumentParser(description="Backfill ELO por temporada/fase")
    parser.add_argument("--season", type=int, required=True, help="Temporada (ej: 2025)")
    parser.add_argument(
        "--phases",
        type=str,
        default=",".join(VALID_PHASES),
        help="Lista de fases separadas por coma",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Borrar ELO previo de la temporada/fases antes de reconstruir",
    )
    return parser.parse_args()


def get_supabase_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("Faltan SUPABASE_URL o SUPABASE_KEY en variables de entorno")
    return create_client(url, key)


def parse_phases(phases_raw):
    phases = [p.strip() for p in phases_raw.split(",") if p.strip()]
    invalid = [p for p in phases if p not in VALID_PHASES]
    if invalid:
        raise ValueError(f"Fases inválidas: {invalid}. Válidas: {VALID_PHASES}")
    return phases


def fetch_final_games(supabase, season, phase):
    base = (
        supabase.table("games")
        .select("id, game_datetime, game_date, home_team_id, away_team_id, home_score, away_score")
        .eq("season", season)
        .eq("status", "Final")
    )
    try:
        response = base.eq("phase", phase).execute()
        games = response.data or []
    except Exception:
        # Fallback para esquemas que no tengan columna phase.
        response = base.eq("game_type", phase).execute()
        games = response.data or []

    # Orden determinístico por game_datetime asc con fallback a game_date.
    games.sort(key=lambda g: (g.get("game_datetime") or g.get("game_date") or "", g.get("id") or 0))
    return games


def reset_phase_data(supabase, season, phase):
    supabase.table("elo_game_log").delete().eq("season", season).eq("phase", phase).execute()
    supabase.table("elo_ratings").delete().eq("season", season).eq("phase", phase).execute()


def load_processed_ids(supabase, season, phase):
    response = (
        supabase.table("elo_game_log")
        .select("game_id")
        .eq("season", season)
        .eq("phase", phase)
        .execute()
    )
    return {row["game_id"] for row in (response.data or [])}


def load_ratings_map(supabase, season, phase):
    response = (
        supabase.table("elo_ratings")
        .select("*")
        .eq("season", season)
        .eq("phase", phase)
        .execute()
    )
    return {row["team_id"]: row for row in (response.data or [])}


def process_phase(supabase, season, phase, reset=False):
    if reset:
        reset_phase_data(supabase, season, phase)

    games = fetch_final_games(supabase, season, phase)
    total_final_games = len(games)
    processed = 0
    skipped = 0

    processed_ids = load_processed_ids(supabase, season, phase)
    ratings_map = load_ratings_map(supabase, season, phase)

    for game in games:
        game_id = game.get("id")
        if game_id in processed_ids:
            skipped += 1
            continue

        home_team_id = game.get("home_team_id")
        away_team_id = game.get("away_team_id")
        home_score = game.get("home_score")
        away_score = game.get("away_score")
        game_datetime = game.get("game_datetime") or game.get("game_date")

        if None in [home_team_id, away_team_id, home_score, away_score]:
            skipped += 1
            continue

        home_row = ratings_map.get(home_team_id, {})
        away_row = ratings_map.get(away_team_id, {})

        home_elo = float(home_row.get("elo", BASE_ELO))
        away_elo = float(away_row.get("elo", BASE_ELO))
        home_games_played = int(home_row.get("games_played", 0))
        away_games_played = int(away_row.get("games_played", 0))

        home_win = home_score > away_score
        k_value = K_BY_PHASE.get(phase, K_BY_PHASE["unknown"])
        new_home_elo, new_away_elo = update_elo(
            r_home=home_elo,
            r_away=away_elo,
            home_win=home_win,
            k=k_value,
            home_advantage=HOME_ADVANTAGE,
        )

        now_iso = datetime.now().isoformat()
        home_payload = {
            "season": season,
            "phase": phase,
            "team_id": home_team_id,
            "elo": round(new_home_elo, 2),
            "games_played": home_games_played + 1,
            "last_game_id": game_id,
            "game_datetime": game_datetime,
            "updated_at": now_iso,
        }
        away_payload = {
            "season": season,
            "phase": phase,
            "team_id": away_team_id,
            "elo": round(new_away_elo, 2),
            "games_played": away_games_played + 1,
            "last_game_id": game_id,
            "game_datetime": game_datetime,
            "updated_at": now_iso,
        }

        supabase.table("elo_ratings").upsert(home_payload).execute()
        supabase.table("elo_ratings").upsert(away_payload).execute()
        supabase.table("elo_game_log").insert(
            {
                "season": season,
                "phase": phase,
                "game_id": game_id,
                "game_datetime": game_datetime,
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "home_score": home_score,
                "away_score": away_score,
                "home_elo_before": round(home_elo, 2),
                "away_elo_before": round(away_elo, 2),
                "home_elo_after": round(new_home_elo, 2),
                "away_elo_after": round(new_away_elo, 2),
                "k_value": k_value,
                "home_advantage": HOME_ADVANTAGE,
                "updated_at": now_iso,
            }
        ).execute()

        ratings_map[home_team_id] = home_payload
        ratings_map[away_team_id] = away_payload
        processed_ids.add(game_id)
        processed += 1

    print(
        f"[{phase}] total_final_games={total_final_games} processed={processed} skipped={skipped}"
    )


def main():
    args = parse_args()
    phases = parse_phases(args.phases)
    supabase = get_supabase_client()

    print(f"Iniciando backfill ELO para temporada {args.season}")
    print(f"Fases: {', '.join(phases)}")
    print(f"Reset: {args.reset}")

    for phase in phases:
        process_phase(supabase, args.season, phase, reset=args.reset)

    print("Backfill ELO finalizado")


if __name__ == "__main__":
    main()

# scripts/update_daily.py
import os
import sys
from datetime import datetime, timedelta
from supabase import create_client
import statsapi
from utils.elo import BASE_ELO, HOME_ADVANTAGE, K_BY_PHASE, update_elo

# Configuración
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
LEAGUE_ID = 135  # LVBP

# Inicializar Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

PHASE_BY_GAME_TYPE = {
    "R": "regular",
    "D": "wildcard_playin",
    "L": "round_robin",
    "W": "final"
}

ELO_PHASES = ["regular", "wildcard_playin", "round_robin", "final"]


def map_phase(game_type_code):
    """Mapea gameType de MLB a fase interna."""
    if not game_type_code:
        return "unknown"
    return PHASE_BY_GAME_TYPE.get(str(game_type_code).upper(), "unknown")


def build_game_record(game, game_date, season):
    """Construye el payload de juego con campos de fase y compatibilidad retro."""
    game_type_code = game.get("gameType")
    phase = map_phase(game_type_code)
    return {
        "id": game.get("gamePk"),
        "game_date": game_date,
        "game_datetime": game.get("gameDate"),
        "home_team_id": game.get("teams", {}).get("home", {}).get("team", {}).get("id"),
        "away_team_id": game.get("teams", {}).get("away", {}).get("team", {}).get("id"),
        "home_score": game.get("teams", {}).get("home", {}).get("score"),
        "away_score": game.get("teams", {}).get("away", {}).get("score"),
        "status": game.get("status", {}).get("detailedState"),
        "venue": game.get("venue", {}).get("name"),
        "season": season,
        # Compatibilidad con la columna existente
        "game_type": phase,
        # Nuevos campos auditable por fase
        "game_type_code": game_type_code,
        "phase": phase,
        "series_description": game.get("seriesDescription")
    }


def upsert_game_record(supabase_client, game_record):
    """Upsert de games con fallback seguro cuando faltan columnas nuevas."""
    try:
        supabase_client.table("games").upsert(game_record).execute()
        return
    except Exception as e:
        message = str(e).lower()

    has_missing_column_hint = any(
        hint in message for hint in ["does not exist", "could not find the", "schema cache"]
    )
    touches_new_columns = any(
        col in message for col in ["game_type_code", "phase", "series_description"]
    )
    if not (has_missing_column_hint and touches_new_columns):
        raise

    fallback_record = dict(game_record)
    fallback_record.pop("game_type_code", None)
    fallback_record.pop("phase", None)
    fallback_record.pop("series_description", None)
    supabase_client.table("games").upsert(fallback_record).execute()

def get_current_season():
    """Determina la temporada actual"""
    now = datetime.now()
    month = now.month
    year = now.year

    # La temporada 2025-2026 se guarda como 2025 (año de inicio)
    if month >= 10:  # Oct-Dic: temporada en curso
        return year
    elif month <= 2:  # Ene-Feb: continuación de temporada anterior
        return year - 1
    else:
        # Fuera de temporada (Mar-Sep)
        return year

def update_yesterdays_games():
    """Actualiza los juegos de ayer"""
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    season = get_current_season()
    
    print(f"📅 Actualizando juegos del {yesterday}")
    print(f"🏆 Temporada: {season}")
    
    try:
        # Obtener juegos de ayer
        schedule = statsapi.get("schedule", {
            "sportId": 17,
            "startDate": yesterday,
            "endDate": yesterday,
            "leagueId": LEAGUE_ID
        })
        
        games_updated = 0
        stats_updated = 0
        
        for date in schedule.get("dates", []):
            for game in date.get("games", []):
                game_id = game.get("gamePk")
                
                # Preparar registro del juego
                game_record = build_game_record(game, date.get("date"), season)
                
                # Upsert juego (actualizar si existe, insertar si no)
                try:
                    upsert_game_record(supabase, game_record)
                    games_updated += 1
                    
                    # Si el juego está finalizado, obtener estadísticas
                    if game.get("status",{}).get("detailedState") == "Final":
                        stats_count = update_game_stats(game_id)
                        stats_updated += stats_count
                        
                except Exception as e:
                    print(f"⚠️ Error actualizando juego {game_id}: {str(e)[:100]}")
        
        print(f"✅ {games_updated} juegos actualizados")
        print(f"📊 {stats_updated} registros de estadísticas actualizados")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

def update_game_stats(game_id):
    """Actualiza estadísticas de un juego específico"""
    stats_count = 0
    
    try:
        boxscore = statsapi.get("game_boxscore", {"gamePk": game_id})
        
        # Procesar estadísticas de bateo y pitcheo
        for side in ["home", "away"]:
            team_data = boxscore.get("teams", {}).get(side, {})
            team_id = team_data.get("team", {}).get("id")
            
            for player_id_str, player_data in team_data.get("players", {}).items():
                player_id = player_data.get("person", {}).get("id")
                
                # Verificar/insertar jugador
                player_record = {
                    'id': player_id,
                    'full_name': player_data.get("person", {}).get("fullName"),
                    'team_id': team_id,
                    'jersey_number': player_data.get("jerseyNumber"),
                    'position': player_data.get("position", {}).get("abbreviation")
                }
                
                try:
                    supabase.table('players').upsert(player_record).execute()
                except:
                    pass  # El jugador ya existe
                
                # Estadísticas de bateo
                if "batting" in player_data.get("stats", {}):
                    bat = player_data["stats"]["batting"]
                    batting_record = {
                        "game_id": game_id,
                        "player_id": player_id,
                        "team_id": team_id,
                        "ab": bat.get("atBats", 0),
                        "r": bat.get("runs", 0),
                        "h": bat.get("hits", 0),
                        "doubles": bat.get("doubles", 0),
                        "triples": bat.get("triples", 0),
                        "hr": bat.get("homeRuns", 0),
                        "rbi": bat.get("rbi", 0),
                        "bb": bat.get("baseOnBalls", 0),
                        "so": bat.get("strikeOuts", 0),
                        "sb": bat.get("stolenBases", 0),
                        "cs": bat.get("caughtStealing", 0),
                        "hbp": bat.get("hitByPitch", 0),
                        "sf": bat.get("sacFlies", 0),
                        "sh": bat.get("sacBunts", 0)
                    }
                    
                    try:
                        supabase.table('batting_stats').upsert(batting_record).execute()
                        stats_count += 1
                    except:
                        pass
                
                # Estadísticas de pitcheo
                if "pitching" in player_data.get("stats", {}):
                    pit = player_data["stats"]["pitching"]
                    ip_string = pit.get("inningsPitched", "0.0")
                    
                    # Convertir innings a decimal
                    ip_parts = ip_string.split('.')
                    ip_decimal = float(ip_parts[0]) + (float(ip_parts[1])/3 if len(ip_parts) > 1 else 0)
                    
                    pitching_record = {
                        "game_id": game_id,
                        "player_id": player_id,
                        "team_id": team_id,
                        "ip_string": ip_string,
                        "ip_decimal": round(ip_decimal, 2),
                        "h": pit.get("hits", 0),
                        "r": pit.get("runs", 0),
                        "er": pit.get("earnedRuns", 0),
                        "bb": pit.get("baseOnBalls", 0),
                        "so": pit.get("strikeOuts", 0),
                        "hr": pit.get("homeRuns", 0),
                        "hbp": pit.get("hitBatsmen", 0),
                        "wp": pit.get("wildPitches", 0),
                        "bk": pit.get("balks", 0)
                    }
                    
                    try:
                        supabase.table('pitching_stats').upsert(pitching_record).execute()
                        stats_count += 1
                    except:
                        pass
                    
    except Exception as e:
        print(f"⚠️ Error actualizando stats del juego {game_id}: {str(e)[:100]}")
    
    return stats_count

def update_todays_games():
    """Actualiza los juegos de hoy (para el schedule)"""
    today = datetime.now().strftime('%Y-%m-%d')
    season = get_current_season()
    
    print(f"📅 Actualizando schedule del {today}")
    
    try:
        # Obtener juegos de hoy
        schedule = statsapi.get("schedule", {
            "sportId": 17,
            "startDate": today,
            "endDate": today,
            "leagueId": LEAGUE_ID
        })
        
        games_scheduled = 0
        
        for date in schedule.get("dates", []):
            for game in date.get("games", []):
                game_id = game.get("gamePk")
                
                # Preparar registro del juego (aunque no haya terminado)
                game_record = build_game_record(game, date.get("date"), season)
                
                try:
                    upsert_game_record(supabase, game_record)
                    games_scheduled += 1
                except Exception as e:
                    print(f"⚠️ Error con juego {game_id}: {str(e)[:50]}")
        
        print(f"📋 {games_scheduled} juegos en el schedule de hoy")
        
    except Exception as e:
        print(f"⚠️ Error actualizando schedule: {str(e)[:100]}")

def update_standings():
    """Calcula y actualiza standings"""
    season = get_current_season()
    print(f"📊 Actualizando standings de temporada {season}")
    
    try:
        # Obtener todos los juegos finalizados de la temporada
        games = supabase.table('games') \
            .select('*') \
            .eq('season', season) \
            .eq('status', 'Final') \
            .execute()
        
        if not games.data:
            print("⚠️ No hay juegos finalizados para calcular standings")
            return
        
        # Obtener equipos de LVBP
        teams = supabase.table('teams') \
            .select('*') \
            .eq('league_id', LEAGUE_ID) \
            .execute()
        
        standings_data = []
        
        for team in teams.data:
            team_id = team['id']
            wins = 0
            losses = 0
            runs_for = 0
            runs_against = 0
            
            for game in games.data:
                if game['home_team_id'] == team_id:
                    runs_for += game['home_score'] or 0
                    runs_against += game['away_score'] or 0
                    if game['home_score'] > game['away_score']:
                        wins += 1
                    else:
                        losses += 1
                elif game['away_team_id'] == team_id:
                    runs_for += game['away_score'] or 0
                    runs_against += game['home_score'] or 0
                    if game['away_score'] > game['home_score']:
                        wins += 1
                    else:
                        losses += 1
            
            if wins + losses > 0:
                pct = wins / (wins + losses)
                
                standings_data.append({
                    'team_id': team_id,
                    'season': season,
                    'wins': wins,
                    'losses': losses,
                    'pct': round(pct, 3),
                    'runs_for': runs_for,
                    'runs_against': runs_against,
                    'run_diff': runs_for - runs_against,
                    'updated_at': datetime.now().isoformat()
                })
        
        # Calcular games back
        if standings_data:
            standings_data.sort(key=lambda x: x['pct'], reverse=True)
            leader_wins = standings_data[0]['wins']
            leader_losses = standings_data[0]['losses']
            
            for team in standings_data:
                gb = ((leader_wins - team['wins']) + (team['losses'] - leader_losses)) / 2
                team['games_back'] = round(gb, 1)
            
            # Upsert standings
            for team_standing in standings_data:
                supabase.table('standings').upsert(team_standing).execute()
            
            print(f"✅ Standings actualizados para {len(standings_data)} equipos")
        
    except Exception as e:
        print(f"❌ Error actualizando standings: {str(e)}")

def get_phase_games_for_elo(season, phase):
    """Obtiene juegos finalizados por fase para procesar ELO."""
    base_query = supabase.table('games') \
        .select('id, game_datetime, game_date, home_team_id, away_team_id, home_score, away_score') \
        .eq('season', season) \
        .eq('status', 'Final')

    try:
        response = base_query.eq('phase', phase).order('game_datetime', desc=False).execute()
        return response.data or []
    except Exception:
        # Compatibilidad retro cuando la columna phase aún no existe.
        response = base_query.eq('game_type', phase).order('game_datetime', desc=False).execute()
        return response.data or []


def update_elo_ratings(season):
    """Actualiza ELO por fase de forma idempotente."""
    print(f"📈 Actualizando ELO por fase para temporada {season}")

    for phase in ELO_PHASES:
        processed_count = 0
        skipped_count = 0

        try:
            games = get_phase_games_for_elo(season, phase)
            if not games:
                print(f"📌 {phase}: processed_count=0 skipped_count=0")
                continue

            log_response = supabase.table('elo_game_log') \
                .select('game_id') \
                .eq('season', season) \
                .eq('phase', phase) \
                .execute()
            processed_ids = {row['game_id'] for row in (log_response.data or [])}

            ratings_response = supabase.table('elo_ratings') \
                .select('*') \
                .eq('season', season) \
                .eq('phase', phase) \
                .execute()
            ratings_map = {row['team_id']: row for row in (ratings_response.data or [])}

            for game in games:
                game_id = game.get('id')
                if game_id in processed_ids:
                    skipped_count += 1
                    continue

                home_team_id = game.get('home_team_id')
                away_team_id = game.get('away_team_id')
                home_score = game.get('home_score')
                away_score = game.get('away_score')
                game_datetime = game.get('game_datetime') or game.get('game_date')

                if None in [home_team_id, away_team_id, home_score, away_score]:
                    skipped_count += 1
                    continue

                home_row = ratings_map.get(home_team_id, {})
                away_row = ratings_map.get(away_team_id, {})
                home_elo = float(home_row.get('elo', BASE_ELO))
                away_elo = float(away_row.get('elo', BASE_ELO))
                home_games_played = int(home_row.get('games_played', 0))
                away_games_played = int(away_row.get('games_played', 0))

                home_win = home_score > away_score
                k_value = K_BY_PHASE.get(phase, K_BY_PHASE['unknown'])
                new_home_elo, new_away_elo = update_elo(
                    r_home=home_elo,
                    r_away=away_elo,
                    home_win=home_win,
                    k=k_value,
                    home_advantage=HOME_ADVANTAGE
                )

                now_iso = datetime.now().isoformat()
                home_payload = {
                    'season': season,
                    'phase': phase,
                    'team_id': home_team_id,
                    'elo': round(new_home_elo, 2),
                    'games_played': home_games_played + 1,
                    'last_game_id': game_id,
                    'game_datetime': game_datetime,
                    'updated_at': now_iso
                }
                away_payload = {
                    'season': season,
                    'phase': phase,
                    'team_id': away_team_id,
                    'elo': round(new_away_elo, 2),
                    'games_played': away_games_played + 1,
                    'last_game_id': game_id,
                    'game_datetime': game_datetime,
                    'updated_at': now_iso
                }

                supabase.table('elo_ratings').upsert(home_payload).execute()
                supabase.table('elo_ratings').upsert(away_payload).execute()
                supabase.table('elo_game_log').insert({
                    'season': season,
                    'phase': phase,
                    'game_id': game_id,
                    'game_datetime': game_datetime,
                    'home_team_id': home_team_id,
                    'away_team_id': away_team_id,
                    'home_score': home_score,
                    'away_score': away_score,
                    'home_elo_before': round(home_elo, 2),
                    'away_elo_before': round(away_elo, 2),
                    'home_elo_after': round(new_home_elo, 2),
                    'away_elo_after': round(new_away_elo, 2),
                    'k_value': k_value,
                    'home_advantage': HOME_ADVANTAGE,
                    'updated_at': now_iso
                }).execute()

                ratings_map[home_team_id] = home_payload
                ratings_map[away_team_id] = away_payload
                processed_ids.add(game_id)
                processed_count += 1

            print(f"📌 {phase}: processed_count={processed_count} skipped_count={skipped_count}")
        except Exception as e:
            print(f"⚠️ Error actualizando ELO en fase {phase}: {str(e)}")


def main():
    print("🚀 Iniciando actualización diaria LVBP")
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"🏆 Temporada: {get_current_season()}")
    print("="*50)
    
    # 1. Actualizar juegos de ayer
    update_yesterdays_games()
    
    # 2. Actualizar schedule de hoy
    update_todays_games()
    
    # 3. Actualizar standings
    update_standings()

    # 4. Actualizar ELO por fase
    update_elo_ratings(get_current_season())
    
    print("="*50)
    print("✅ Actualización completada exitosamente")

if __name__ == "__main__":
    main()

# scripts/update_daily.py
import os
import sys
from datetime import datetime, timedelta
from supabase import create_client
import statsapi

# Configuración
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
LEAGUE_ID = 135  # LVBP

# Inicializar Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_current_season():
    """Determina la temporada actual"""
    now = datetime.now()
    month = now.month
    year = now.year
    
    # La temporada 2025-2026 se guarda como 2026
    if month >= 10:  # Oct-Dic
        return year + 1
    elif month <= 2:  # Ene-Feb
        return year
    else:
        # Fuera de temporada (Mar-Sep)
        return year

def update_yesterdays_games():
    """Actualiza los juegos de ayer"""
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    today = datetime.now().strftime('%Y-%m-%d')
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
                game_record = {
                    "id": game_id,
                    "game_date": date.get("date"),
                    "game_datetime": game.get("gameDate"),
                    "home_team_id": game.get("teams",{}).get("home",{}).get("team",{}).get("id"),
                    "away_team_id": game.get("teams",{}).get("away",{}).get("team",{}).get("id"),
                    "home_score": game.get("teams",{}).get("home",{}).get("score"),
                    "away_score": game.get("teams",{}).get("away",{}).get("score"),
                    "status": game.get("status",{}).get("detailedState"),
                    "venue": game.get("venue",{}).get("name"),
                    "season": season,
                    "game_type": "regular"
                }
                
                # Upsert juego (actualizar si existe, insertar si no)
                try:
                    supabase.table('games').upsert(game_record).execute()
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
                game_record = {
                    "id": game_id,
                    "game_date": date.get("date"),
                    "game_datetime": game.get("gameDate"),
                    "home_team_id": game.get("teams",{}).get("home",{}).get("team",{}).get("id"),
                    "away_team_id": game.get("teams",{}).get("away",{}).get("team",{}).get("id"),
                    "home_score": game.get("teams",{}).get("home",{}).get("score"),
                    "away_score": game.get("teams",{}).get("away",{}).get("score"),
                    "status": game.get("status",{}).get("detailedState"),
                    "venue": game.get("venue",{}).get("name"),
                    "season": season,
                    "game_type": "regular"
                }
                
                try:
                    supabase.table('games').upsert(game_record).execute()
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
    
    print("="*50)
    print("✅ Actualización completada exitosamente")

if __name__ == "__main__":
    main()

# streamlit_app/utils/supabase_client.py
import os
from supabase import create_client, Client
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Inicializar cliente de Supabase
@st.cache_resource
def init_supabase() -> Client:
    """Inicializa y retorna el cliente de Supabase"""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
    
    return create_client(url, key)

def get_current_season():
    """
    Determina la temporada actual de LVBP
    La temporada va de octubre a enero/febrero
    """
    now = datetime.now()
    month = now.month
    year = now.year
    
    # Si estamos entre octubre y diciembre, la temporada es año actual - año siguiente
    if month >= 10:  # Octubre, Noviembre, Diciembre
        return year + 1  # Ej: Oct 2024 = Temporada 2025
    # Si estamos en enero o febrero, seguimos en la temporada del año actual
    elif month <= 2:  # Enero, Febrero
        return year  # Ej: Enero 2025 = Temporada 2025
    else:
        # Fuera de temporada (marzo-septiembre)
        # Mostrar la última temporada completada
        return year  # Ej: Julio 2025 = Temporada 2025 (última completada)

# Funciones de consulta actualizadas
@st.cache_data(ttl=3600)  # Cache por 1 hora
def get_standings(season=None):
    """Obtiene los standings actuales"""
    if season is None:
        season = get_current_season()
    
    supabase = init_supabase()
    
    # Primero intentar obtener de la tabla standings si existe
    response = supabase.table('standings') \
        .select('*') \
        .eq('season', season) \
        .order('pct', desc=True) \
        .execute()
    
    if response.data:
        return pd.DataFrame(response.data)
    
    # Si no hay datos en standings, calcular desde games
    return calculate_standings_from_games(season)

def calculate_standings_from_games(season=None):
    """Calcula standings desde la tabla games"""
    if season is None:
        season = get_current_season()
    
    supabase = init_supabase()
    
    # Obtener todos los juegos de la temporada
    games = supabase.table('games') \
        .select('*') \
        .eq('season', season) \
        .eq('status', 'Final') \
        .execute()
    
    if not games.data:
        return pd.DataFrame()
    
    games_df = pd.DataFrame(games.data)
    
    # Obtener equipos
    teams = supabase.table('teams') \
        .select('*') \
        .eq('league_id', 135) \
        .execute()
    
    if not teams.data:
        return pd.DataFrame()
    
    teams_df = pd.DataFrame(teams.data)
    
    # Calcular standings
    standings_data = []
    
    for team in teams_df.itertuples():
        # Filtrar juegos del equipo
        team_games = games_df[
            (games_df['home_team_id'] == team.id) | 
            (games_df['away_team_id'] == team.id)
        ]
        
        wins = 0
        losses = 0
        runs_for = 0
        runs_against = 0
        home_wins = 0
        home_losses = 0
        away_wins = 0
        away_losses = 0
        last_10 = []
        
        for _, game in team_games.iterrows():
            if game['home_team_id'] == team.id:
                # Juego de local
                runs_for += game['home_score'] or 0
                runs_against += game['away_score'] or 0
                
                if game['home_score'] > game['away_score']:
                    wins += 1
                    home_wins += 1
                    last_10.append('W')
                else:
                    losses += 1
                    home_losses += 1
                    last_10.append('L')
            else:
                # Juego de visitante
                runs_for += game['away_score'] or 0
                runs_against += game['home_score'] or 0
                
                if game['away_score'] > game['home_score']:
                    wins += 1
                    away_wins += 1
                    last_10.append('W')
                else:
                    losses += 1
                    away_losses += 1
                    last_10.append('L')
        
        # Calcular estadísticas
        games_played = wins + losses
        pct = wins / games_played if games_played > 0 else 0
        
        # Últimos 10 juegos
        last_10 = last_10[-10:] if len(last_10) >= 10 else last_10
        last_10_record = f"{last_10.count('W')}-{last_10.count('L')}"
        
        # Racha actual
        if last_10:
            current_streak = 1
            streak_type = last_10[-1]
            for i in range(len(last_10)-2, -1, -1):
                if last_10[i] == streak_type:
                    current_streak += 1
                else:
                    break
            streak = f"{streak_type}{current_streak}"
        else:
            streak = "-"
        
        standings_data.append({
            'team_id': team.id,
            'team_name': team.name,
            'team_abbreviation': team.abbreviation,
            'season': season,
            'games_played': games_played,
            'wins': wins,
            'losses': losses,
            'pct': pct,
            'games_back': 0,  # Se calculará después
            'runs_for': runs_for,
            'runs_against': runs_against,
            'run_diff': runs_for - runs_against,
            'home_record': f"{home_wins}-{home_losses}",
            'away_record': f"{away_wins}-{away_losses}",
            'last_10': last_10_record,
            'streak': streak
        })
    
    # Crear DataFrame y ordenar por PCT
    standings_df = pd.DataFrame(standings_data).sort_values('pct', ascending=False)
    
    # Calcular games back
    if not standings_df.empty:
        leader_wins = standings_df.iloc[0]['wins']
        leader_losses = standings_df.iloc[0]['losses']
        
        standings_df['games_back'] = standings_df.apply(
            lambda x: ((leader_wins - x['wins']) + (x['losses'] - leader_losses)) / 2,
            axis=1
        )
    
    return standings_df

@st.cache_data(ttl=3600)
def get_team_stats(team_id=695, season=None):
    """Obtiene estadísticas del equipo"""
    if season is None:
        season = get_current_season()
    
    supabase = init_supabase()
    
    # Juegos del equipo
    games = supabase.table('games') \
        .select('*') \
        .eq('season', season) \
        .or_(f'home_team_id.eq.{team_id},away_team_id.eq.{team_id}') \
        .order('game_date', desc=True) \
        .execute()
    
    return pd.DataFrame(games.data) if games.data else pd.DataFrame()

@st.cache_data(ttl=1800)  # Cache por 30 minutos
def get_recent_games(team_id=695, limit=10):
    """Obtiene los últimos juegos del equipo"""
    supabase = init_supabase()
    
    response = supabase.table('games') \
        .select('*, home_team:teams!games_home_team_id_fkey(name, abbreviation), away_team:teams!games_away_team_id_fkey(name, abbreviation)') \
        .or_(f'home_team_id.eq.{team_id},away_team_id.eq.{team_id}') \
        .eq('status', 'Final') \
        .order('game_date', desc=True) \
        .limit(limit) \
        .execute()
    
    return pd.DataFrame(response.data) if response.data else pd.DataFrame()

@st.cache_data(ttl=3600)
def get_available_seasons():
    """Obtiene todas las temporadas disponibles en la base de datos"""
    supabase = init_supabase()
    
    response = supabase.table('games') \
        .select('season') \
        .execute()
    
    if response.data:
        seasons = list(set([g['season'] for g in response.data if g['season']]))
        return sorted(seasons, reverse=True)
    
    return [get_current_season()]

# Función para obtener estadísticas de bateo
@st.cache_data(ttl=3600)
def get_batting_stats(team_id=None, season=None, limit=50):
    """Obtiene estadísticas de bateo"""
    if season is None:
        season = get_current_season()
    
    supabase = init_supabase()
    
    # Construir query base
    query = supabase.table('batting_stats') \
        .select('*, players!inner(full_name, jersey_number), teams!inner(name)')
    
    # Filtrar por equipo si se especifica
    if team_id:
        query = query.eq('team_id', team_id)
    
    # Ejecutar query
    response = query.limit(limit * 10).execute()  # Traer más para agrupar
    
    if response.data:
        df = pd.DataFrame(response.data)
        # Aquí procesarías los datos según necesites
        return df
    
    return pd.DataFrame()

# Función para obtener estadísticas de pitcheo
@st.cache_data(ttl=3600)
def get_pitching_stats(team_id=None, season=None, limit=50):
    """Obtiene estadísticas de pitcheo"""
    if season is None:
        season = get_current_season()
    
    supabase = init_supabase()
    
    query = supabase.table('pitching_stats') \
        .select('*, players!inner(full_name, jersey_number), teams!inner(name)')
    
    if team_id:
        query = query.eq('team_id', team_id)
    
    response = query.limit(limit * 10).execute()
    
    if response.data:
        return pd.DataFrame(response.data)
    
    return pd.DataFrame()

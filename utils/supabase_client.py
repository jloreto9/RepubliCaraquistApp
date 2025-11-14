# utils/supabase_client.py
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
    """Retorna la temporada actual"""
    return 2026  # Temporada 2025-2026

@st.cache_data(ttl=3600)
def get_available_seasons():
    """Obtiene todas las temporadas disponibles en la base de datos"""
    supabase = init_supabase()
    
    try:
        response = supabase.table('games') \
            .select('season') \
            .execute()
        
        if response.data:
            seasons = list(set([g['season'] for g in response.data if g['season']]))
            # Ordenar de más reciente a más antigua
            return sorted(seasons, reverse=True)
    except:
        pass
    
    # Retornar temporadas por defecto si no hay datos
    # 2015 = temporada 2014-2015, 2016 = temporada 2015-2016, etc.
    return [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015]

# UNA SOLA función get_standings - COMPLETA
@st.cache_data(ttl=600)  # Cache por 10 minutos
def get_standings(season=None):
    """Calcula standings desde la tabla games"""
    if season is None:
        season = get_current_season()
    
    supabase = init_supabase()
    
    # Primero intentar tabla standings
    try:
        response = supabase.table('standings') \
            .select('*') \
            .eq('season', season) \
            .order('pct', desc=True) \
            .execute()
        
        if response.data:
            return pd.DataFrame(response.data)
    except:
        pass
    
    # Si no hay standings, calcular desde games
    try:
        # Obtener juegos
        games_response = supabase.table('games') \
            .select('*') \
            .eq('season', season) \
            .eq('status', 'Final') \
            .execute()
        
        if not games_response.data:
            return pd.DataFrame()
        
        games_df = pd.DataFrame(games_response.data)
        
        # Obtener equipos
        teams_response = supabase.table('teams') \
            .select('*') \
            .eq('league_id', 135) \
            .execute()
        
        if not teams_response.data:
            return pd.DataFrame()
        
        teams_df = pd.DataFrame(teams_response.data)
        
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
                'team_abbreviation': team.abbreviation if hasattr(team, 'abbreviation') else '',
                'wins': wins,
                'losses': losses,
                'pct': pct,
                'games_back': 0,
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
        
    except Exception as e:
        st.error(f"Error calculando standings: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_team_stats(team_id=695, season=None):
    """Obtiene estadísticas del equipo"""
    if season is None:
        season = get_current_season()
    
    supabase = init_supabase()
    
    try:
        games = supabase.table('games') \
            .select('*') \
            .eq('season', season) \
            .or_(f'home_team_id.eq.{team_id},away_team_id.eq.{team_id}') \
            .order('game_date', desc=True) \
            .execute()
        
        return pd.DataFrame(games.data) if games.data else pd.DataFrame()
    except:
        return pd.DataFrame()

@st.cache_data(ttl=1800)
def get_recent_games(team_id=695, limit=10):
    """Obtiene los últimos juegos del equipo"""
    supabase = init_supabase()
    
    try:
        response = supabase.table('games') \
            .select('*, home_team:teams!games_home_team_id_fkey(name, abbreviation), away_team:teams!games_away_team_id_fkey(name, abbreviation)') \
            .or_(f'home_team_id.eq.{team_id},away_team_id.eq.{team_id}') \
            .eq('status', 'Final') \
            .order('game_date', desc=True) \
            .limit(limit) \
            .execute()
        
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_batting_stats(team_id=695, limit=50):
    """Obtiene estadísticas de bateo"""
    supabase = init_supabase()
    
    try:
        response = supabase.table('batting_stats') \
            .select('*, players!inner(full_name)') \
            .eq('team_id', team_id) \
            .limit(limit) \
            .execute()
        
        if response.data:
            return pd.DataFrame(response.data)
    except:
        pass
    
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_pitching_stats(team_id=695, limit=50):
    """Obtiene estadísticas de pitcheo"""
    supabase = init_supabase()
    
    try:
        response = supabase.table('pitching_stats') \
            .select('*, players!inner(full_name)') \
            .eq('team_id', team_id) \
            .limit(limit) \
            .execute()
        
        if response.data:
            return pd.DataFrame(response.data)
    except:
        pass
    
    return pd.DataFrame()

def calculate_batting_stats(df):
    """Calcula estadísticas de bateo agregadas"""
    if df.empty:
        return df
    
    grouped = df.groupby('player_id').agg({
        'ab': 'sum',
        'r': 'sum',
        'h': 'sum',
        'doubles': 'sum',
        'triples': 'sum',
        'hr': 'sum',
        'rbi': 'sum',
        'bb': 'sum',
        'so': 'sum',
        'sb': 'sum'
    }).reset_index()
    
    # Calcular promedios
    grouped['avg'] = (grouped['h'] / grouped['ab']).round(3).fillna(0)
    grouped['obp'] = ((grouped['h'] + grouped['bb']) / (grouped['ab'] + grouped['bb'])).round(3).fillna(0)
    grouped['slg'] = ((grouped['h'] + grouped['doubles'] + 2*grouped['triples'] + 3*grouped['hr']) / grouped['ab']).round(3).fillna(0)
    grouped['ops'] = (grouped['obp'] + grouped['slg']).round(3)
    
    return grouped.sort_values('avg', ascending=False)


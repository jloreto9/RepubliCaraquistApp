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
    url = os.environ.get("SUPABASE_URL") or st.secrets["SUPABASE_URL"]
    key = os.environ.get("SUPABASE_KEY") or st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# Funciones de consulta
@st.cache_data(ttl=3600)  # Cache por 1 hora
def get_standings(season=2025):
    """Obtiene los standings actuales"""
    supabase = init_supabase()
    
    response = supabase.table('standings') \
        .select('*') \
        .eq('season', season) \
        .order('pct', desc=True) \
        .execute()
    
    return pd.DataFrame(response.data)

@st.cache_data(ttl=3600)
def get_team_stats(team_id=695, season=2025):
    """Obtiene estadísticas del equipo"""
    supabase = init_supabase()
    
    # Juegos del equipo
    games = supabase.table('games') \
        .select('*') \
        .eq('season', season) \
        .or_(f'home_team_id.eq.{team_id},away_team_id.eq.{team_id}') \
        .order('game_date', desc=True) \
        .execute()
    
    return pd.DataFrame(games.data)

@st.cache_data(ttl=3600)
def get_batting_stats(team_id=695, limit=50):
    """Obtiene estadísticas de bateo"""
    supabase = init_supabase()
    
    # Query para estadísticas acumuladas
    response = supabase.table('batting_season_stats') \
        .select('*') \
        .eq('team_id', team_id) \
        .order('avg', desc=True) \
        .limit(limit) \
        .execute()
    
    if response.data:
        return pd.DataFrame(response.data)
    
    # Si no hay vista materializada, calcular desde batting_stats
    response = supabase.table('batting_stats') \
        .select('*, players!inner(full_name)') \
        .eq('team_id', team_id) \
        .execute()
    
    if response.data:
        df = pd.DataFrame(response.data)
        # Agrupar y calcular estadísticas
        return calculate_batting_stats(df)
    
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_pitching_stats(team_id=695, limit=50):
    """Obtiene estadísticas de pitcheo"""
    supabase = init_supabase()
    
    response = supabase.table('pitching_season_stats') \
        .select('*') \
        .eq('team_id', team_id) \
        .order('era', asc=True) \
        .limit(limit) \
        .execute()
    
    if response.data:
        return pd.DataFrame(response.data)
    
    return pd.DataFrame()

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
    
    return pd.DataFrame(response.data)

def calculate_batting_stats(df):
    """Calcula estadísticas de bateo agregadas"""
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
    grouped['avg'] = (grouped['h'] / grouped['ab']).round(3)
    grouped['obp'] = ((grouped['h'] + grouped['bb']) / (grouped['ab'] + grouped['bb'])).round(3)
    grouped['slg'] = ((grouped['h'] + grouped['doubles'] + 2*grouped['triples'] + 3*grouped['hr']) / grouped['ab']).round(3)
    grouped['ops'] = (grouped['obp'] + grouped['slg']).round(3)
    
    return grouped.sort_values('avg', ascending=False)

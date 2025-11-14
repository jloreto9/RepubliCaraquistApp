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
            return sorted(seasons, reverse=True)
    except:
        pass
    
    return [get_current_season()]

# Funciones de consulta
@st.cache_data(ttl=3600)  # Cache por 1 hora
def get_standings(season=None):
    """Obtiene los standings actuales"""
    if season is None:
        season = get_current_season()
    
    supabase = init_supabase()
    
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
    
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_team_stats(team_id=695, season=None):
    """Obtiene estadísticas del equipo"""
    if season is None:
        season = get_current_season()
    
    supabase = init_supabase()
    
    try:
        # Juegos del equipo
        games = supabase.table('games') \
            .select('*') \
            .eq('season', season) \
            .or_(f'home_team_id.eq.{team_id},away_team_id.eq.{team_id}') \
            .order('game_date', desc=True) \
            .execute()
        
        return pd.DataFrame(games.data) if games.data else pd.DataFrame()
    except:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_batting_stats(team_id=695, limit=50):
    """Obtiene estadísticas de bateo"""
    supabase = init_supabase()
    
    try:
        # Query para estadísticas de bateo
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

@st.cache_data(ttl=1800)  # Cache por 30 minutos
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

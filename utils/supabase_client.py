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

@st.cache_data(ttl=600)  # Cache por 10 minutos
def get_standings(season=None):
    """Calcula standings desde la tabla games - Solo equipos LVBP"""
    if season is None:
        season = get_current_season()
    
    supabase = init_supabase()
    
    # IDs de los equipos LVBP
    LVBP_TEAM_IDS = [692, 693, 694, 695, 696, 697, 698, 699]
    
    # Primero intentar tabla standings si existe
    try:
        response = supabase.table('standings') \
            .select('*') \
            .eq('season', season) \
            .in_('team_id', LVBP_TEAM_IDS) \
            .order('pct', desc=True) \
            .execute()
        
        if response.data:
            return pd.DataFrame(response.data)
    except:
        pass
    
    # Si no hay standings, calcular desde games
    try:
        # Obtener juegos de la temporada - CORRECCIÓN: Incluir 'Final', 'Completed' y 'Completed Early'
        games_response = supabase.table('games') \
            .select('*') \
            .eq('season', season) \
            .in_('status', ['Final', 'Completed', 'Completed Early']) \
            .execute()
        
        if not games_response.data:
            return pd.DataFrame()
        
        games_df = pd.DataFrame(games_response.data)
        games_df = games_df.sort_values('game_date')
        
        # Filtrar solo juegos de equipos LVBP
        games_df = games_df[
            (games_df['home_team_id'].isin(LVBP_TEAM_IDS)) | 
            (games_df['away_team_id'].isin(LVBP_TEAM_IDS))
        ]
        
        # Obtener información de equipos
        teams_response = supabase.table('teams') \
            .select('*') \
            .in_('id', LVBP_TEAM_IDS) \
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
            
            if len(team_games) == 0:
                continue
            
            wins = 0
            losses = 0
            runs_for = 0
            runs_against = 0
            home_wins = 0
            home_losses = 0
            away_wins = 0
            away_losses = 0
            last_10 = []
            
            # Ordenar juegos por fecha para calcular rachas
            team_games_sorted = team_games.sort_values('game_date')
            
            for _, game in team_games_sorted.iterrows():
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
            last_10_wins = last_10.count('W')
            last_10_losses = last_10.count('L')
            last_10_record = f"{last_10_wins}-{last_10_losses}"
            
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
                'games_back': 0,  # Se calculará después
                'runs_for': runs_for,
                'runs_against': runs_against,
                'run_diff': runs_for - runs_against,
                'home_record': f"{home_wins}-{home_losses}",
                'away_record': f"{away_wins}-{away_losses}",
                'last_10': last_10_record,
                'streak': streak
            })
        
        if not standings_data:
            return pd.DataFrame()
        
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

@st.cache_data(ttl=600)
def get_leones_advanced_stats(season=None):
    """Calcula estadísticas avanzadas de los Leones del Caracas"""
    if season is None:
        season = get_current_season()
    
    supabase = init_supabase()
    
    try:
        # Obtener juegos de los Leones en la temporada
        games_response = supabase.table('games') \
            .select('*') \
            .eq('season', season) \
            .in_('status', ['Final', 'Completed', 'Completed Early']) \
            .or_('home_team_id.eq.695,away_team_id.eq.695') \
            .execute()
        
        if not games_response.data:
            return {}
        
        games_df = pd.DataFrame(games_response.data)
        game_ids = games_df['id'].tolist()
        
        # Inicializar contadores
        total_games = len(games_df)
        wins = 0
        losses = 0
        home_wins = 0
        home_losses = 0
        away_wins = 0
        away_losses = 0
        night_wins = 0
        night_losses = 0
        shutouts = 0
        extra_inning_wins = 0
        extra_inning_losses = 0
        one_run_wins = 0
        one_run_losses = 0
        comeback_wins = 0
        comeback_losses = 0
        up_wins = 0
        up_losses = 0
        blown_leads = 0
        remontados = 0
        arriba_wins = 0
        arriba_losses = 0
        oct_wins = 0
        oct_losses = 0
        nov_wins = 0
        nov_losses = 0
        dec_wins = 0
        dec_losses = 0
        starter_wins = 0
        starter_losses = 0
        reliever_wins = 0
        reliever_losses = 0
        saves = 0
        
        # Intentar consultar innings (si la tabla existe)
        innings_df = pd.DataFrame()
        try:
            innings_response = supabase.table('game_innings') \
                .select('*') \
                .in_('game_id', game_ids) \
                .execute()
            if innings_response.data:
                innings_df = pd.DataFrame(innings_response.data)
        except Exception as e:
            # Si la tabla no existe, continuar sin innings
            pass
        
        # Últimos 10 juegos
        last_10_games = games_df.sort_values('game_date', ascending=False).head(10)
        last_10_wins = 0
        last_10_losses = 0
        
        # Racha actual
        streak_games = []
        
        for _, game in games_df.iterrows():
            game_id = game['id']
            is_home = game['home_team_id'] == 695
            leones_score = game['home_score'] if is_home else game['away_score']
            opponent_score = game['away_score'] if is_home else game['home_score']
            won = leones_score > opponent_score
            
            # Récord general
            if won:
                wins += 1
                streak_games.append('W')
            else:
                losses += 1
                streak_games.append('L')
            
            # Home/Away
            if is_home:
                if won:
                    home_wins += 1
                else:
                    home_losses += 1
            else:
                if won:
                    away_wins += 1
                else:
                    away_losses += 1
            
            # Blanqueo
            if opponent_score == 0:
                shutouts += 1
            
            # Extra innings
            if game.get('inning', 9) > 9:
                if won:
                    extra_inning_wins += 1
                else:
                    extra_inning_losses += 1
            
            # Por 1 carrera
            if abs(leones_score - opponent_score) == 1:
                if won:
                    one_run_wins += 1
                else:
                    one_run_losses += 1
            
            # Remontadas, arriba, terreneadas y decisiones de pitcheo (solo si innings_df tiene datos)
            if not innings_df.empty:
                game_innings = innings_df[innings_df['game_id'] == game_id].sort_values('inning')
                if not game_innings.empty:
                    inning_runs_leones = game_innings.apply(
                        lambda row: row['home_score'] if is_home else row['away_score'], axis=1
                    )
                    inning_runs_opp = game_innings.apply(
                        lambda row: row['away_score'] if is_home else row['home_score'], axis=1
                    )

                    cumulative_leones = inning_runs_leones.cumsum()
                    cumulative_opp = inning_runs_opp.cumsum()

                    score_by_inning = pd.DataFrame({
                        'inning': game_innings['inning'],
                        'leones': cumulative_leones,
                        'opp': cumulative_opp
                    })

                    # Estado al 5to y 7mo inning
                    through_five = score_by_inning[score_by_inning['inning'] == 5]
                    through_seven = score_by_inning[score_by_inning['inning'] == 7]

                    if not through_five.empty:
                        five_leones = through_five.iloc[0]['leones']
                        five_opp = through_five.iloc[0]['opp']

                        # Remontados: ganaban al 5to y terminaron perdiendo
                        if five_leones > five_opp and not won:
                            remontados += 1

                        # Decisiones de abridores / relevistas (aproximación)
                        if five_leones > five_opp and won:
                            starter_wins += 1
                        elif five_leones < five_opp and not won:
                            starter_losses += 1
                        elif five_leones < five_opp and won:
                            reliever_wins += 1
                        elif five_leones > five_opp and not won:
                            reliever_losses += 1
                        else:
                            # Empatados al 5to, decisión recae en el bullpen
                            if won:
                                reliever_wins += 1
                            else:
                                reliever_losses += 1

                    if not through_seven.empty:
                        seven_leones = through_seven.iloc[0]['leones']
                        seven_opp = through_seven.iloc[0]['opp']
                        if seven_leones > seven_opp:
                            if won:
                                arriba_wins += 1
                            else:
                                arriba_losses += 1

                    # Arriba / Remontadas generales
                    leones_was_behind = (score_by_inning['leones'] < score_by_inning['opp']).any()
                    leones_was_ahead = (score_by_inning['leones'] > score_by_inning['opp']).any()

                    if won and leones_was_behind:
                        comeback_wins += 1
                    elif not won and leones_was_behind:
                        comeback_losses += 1

                    if won and leones_was_ahead:
                        up_wins += 1
                    elif not won and leones_was_ahead:
                        up_losses += 1

                    # Terreneadas (walk-offs)
                    final_inning = score_by_inning['inning'].max()
                    last_frame = score_by_inning[score_by_inning['inning'] == final_inning]
                    prev_frame = score_by_inning[score_by_inning['inning'] == final_inning - 1]

                    if not last_frame.empty and not prev_frame.empty:
                        prev_leones = prev_frame.iloc[0]['leones']
                        prev_opp = prev_frame.iloc[0]['opp']
                        final_leones = last_frame.iloc[0]['leones']
                        final_opp = last_frame.iloc[0]['opp']

                        # Si el local deja en el terreno al final
                        walkoff_for = is_home and won and prev_leones <= prev_opp and final_leones > final_opp
                        walkoff_against = (not is_home) and (not won) and prev_opp <= prev_leones and final_opp > final_leones

                        if walkoff_for or walkoff_against:
                            blown_leads += 1
            
            # Por mes
            try:
                month = pd.to_datetime(game['game_date']).month
                if month == 10:
                    if won:
                        oct_wins += 1
                    else:
                        oct_losses += 1
                elif month == 11:
                    if won:
                        nov_wins += 1
                    else:
                        nov_losses += 1
                elif month == 12:
                    if won:
                        dec_wins += 1
                    else:
                        dec_losses += 1
            except:
                pass

            # Salvados: aproximar con margen de 3 carreras o menos
            if won and abs(leones_score - opponent_score) <= 3:
                saves += 1
        
        # Últimos 10
        for _, g in last_10_games.iterrows():
            is_home = g['home_team_id'] == 695
            leones_score = g['home_score'] if is_home else g['away_score']
            opponent_score = g['away_score'] if is_home else g['home_score']
            if leones_score > opponent_score:
                last_10_wins += 1
            else:
                last_10_losses += 1
        
        # Racha
        if streak_games:
            current_streak = 1
            streak_type = streak_games[-1]
            for i in range(len(streak_games)-2, -1, -1):
                if streak_games[i] == streak_type:
                    current_streak += 1
                else:
                    break
            streak = f"{current_streak} {streak_type}"
        else:
            streak = "N/A"
        
        return {
            'total_games': total_games,
            'record': f"{wins}-{losses}",
            'home_record': f"{home_wins}-{home_losses}",
            'away_record': f"{away_wins}-{away_losses}",
            'night_record': f"{night_wins}-{night_losses}",
            'shutouts': f"{shutouts}",
            'streak': streak,
            'extra_inning': f"{extra_inning_wins}-{extra_inning_losses}",
            'last_10': f"{last_10_wins}-{last_10_losses}",
            'one_run': f"{one_run_wins}-{one_run_losses}",
            'comebacks': f"{comeback_wins}-{comeback_losses}",
            'up': f"{arriba_wins}-{arriba_losses}",
            'blown_leads': f"{blown_leads}",
            'starters': f"{starter_wins}-{starter_losses}",
            'relievers': f"{reliever_wins}-{reliever_losses}",
            'saves': f"{saves}",
            'remontados': f"{remontados}",
            'oct': f"{oct_wins}G-{oct_losses}P",
            'nov': f"{nov_wins}G-{nov_losses}P",
            'dec': f"{dec_wins}G-{dec_losses}P"
        }
        
    except Exception as e:
        st.error(f"Error calculando estadísticas avanzadas: {str(e)}")
        return {}
   
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
def get_batting_stats(team_id=695, limit=50, season=None):
    """Obtiene estadísticas de bateo agregadas por jugador"""
    supabase = init_supabase()

    if season is None:
        season = get_current_season()

    try:
        # Obtener todos los registros de bateo del equipo para la temporada
        response = supabase.table('batting_stats') \
            .select('*, players!inner(full_name), games!inner(season)') \
            .eq('team_id', team_id) \
            .eq('games.season', season) \
            .execute()

        if not response.data:
            return pd.DataFrame()

        df = pd.DataFrame(response.data)

        # Extraer nombre del jugador
        df['player_name'] = df['players'].apply(
            lambda x: x.get('full_name', 'N/A') if isinstance(x, dict) else 'N/A'
        )

        # Agrupar por jugador y sumar estadísticas
        grouped = df.groupby(['player_id', 'player_name']).agg({
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

        # Calcular estadísticas derivadas
        grouped['avg'] = (grouped['h'] / grouped['ab']).fillna(0).round(3)
        grouped['obp'] = ((grouped['h'] + grouped['bb']) / (grouped['ab'] + grouped['bb'])).fillna(0).round(3)
        grouped['slg'] = ((grouped['h'] + grouped['doubles'] + 2*grouped['triples'] + 3*grouped['hr']) / grouped['ab']).fillna(0).round(3)
        grouped['ops'] = (grouped['obp'] + grouped['slg']).round(3)

        # Crear columna 'players' con el formato esperado
        grouped['players'] = grouped.apply(
            lambda row: {'full_name': row['player_name']}, axis=1
        )

        return grouped.sort_values('ops', ascending=False).head(limit)

    except Exception as e:
        print(f"Error obteniendo estadísticas de bateo: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_pitching_stats(team_id=695, limit=50, season=None):
    """Obtiene estadísticas de pitcheo agregadas por jugador"""
    supabase = init_supabase()

    if season is None:
        season = get_current_season()

    try:
        # Obtener todos los registros de pitcheo del equipo para la temporada
        response = supabase.table('pitching_stats') \
            .select('*, players!inner(full_name), games!inner(season)') \
            .eq('team_id', team_id) \
            .eq('games.season', season) \
            .execute()

        if not response.data:
            return pd.DataFrame()

        df = pd.DataFrame(response.data)

        # Extraer nombre del jugador
        df['player_name'] = df['players'].apply(
            lambda x: x.get('full_name', 'N/A') if isinstance(x, dict) else 'N/A'
        )

        # Contar juegos (apariciones)
        df['g_count'] = 1

        # Agrupar por jugador y sumar estadísticas
        grouped = df.groupby(['player_id', 'player_name']).agg({
            'ip_decimal': 'sum',
            'h': 'sum',
            'r': 'sum',
            'er': 'sum',
            'bb': 'sum',
            'so': 'sum',
            'hr': 'sum',
            'g_count': 'sum'
        }).reset_index()

        # Renombrar columnas
        grouped = grouped.rename(columns={
            'ip_decimal': 'ip',
            'g_count': 'g'
        })

        # Calcular estadísticas derivadas
        grouped['era'] = ((grouped['er'] * 9) / grouped['ip']).fillna(0).round(2)
        grouped['whip'] = ((grouped['h'] + grouped['bb']) / grouped['ip']).fillna(0).round(2)

        # Estas estadísticas no están disponibles en el boxscore individual
        # Las inicializamos en 0 por ahora
        grouped['w'] = 0
        grouped['l'] = 0
        grouped['sv'] = 0
        grouped['gs'] = 0

        # Crear columna 'players' con el formato esperado
        grouped['players'] = grouped.apply(
            lambda row: {'full_name': row['player_name']}, axis=1
        )

        return grouped.sort_values('ip', ascending=False).head(limit)

    except Exception as e:
        print(f"Error obteniendo estadísticas de pitcheo: {str(e)}")
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















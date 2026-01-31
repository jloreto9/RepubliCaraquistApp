# Rama de pruebas

import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import os
from dotenv import load_dotenv
from utils.supabase_client import get_standings, get_recent_games, get_current_season, get_available_seasons, get_leones_advanced_stats, get_batting_stats, get_pitching_stats

# Constantes para WPA
TEAM_ID = 695  # Leones del Caracas

# ========================================
# FUNCIONES WPA PARA MVP DEL ÚLTIMO JUEGO
# ========================================

def calculate_wp(inning: int, diff: int) -> float:
    """Calcula Win Probability simple basado en inning y diferencial"""
    leverage = min(inning / 9.0, 1.0)
    wp = 1.0 / (1.0 + np.exp(-0.75 * diff))
    return max(0.0, min(1.0, wp + 0.25 * leverage * (wp - 0.5)))


@st.cache_data(ttl=600)
def get_game_wpa_mvp(game_pk: int) -> dict:
    """Obtiene el MVP del juego basado en WPA"""
    try:
        # Obtener feed del juego
        url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
        response = requests.get(url, timeout=30)
        feed = response.json()

        # Identificar si Leones es local
        home_id = feed["gameData"]["teams"]["home"]["id"]
        leones_is_home = (home_id == TEAM_ID)

        # Procesar jugadas
        all_plays = feed.get("liveData", {}).get("plays", {}).get("allPlays", [])

        if not all_plays:
            return None

        wpa_data = {}
        prev_wp = 0.5
        home_score = away_score = 0

        for play in all_plays:
            about = play.get("about", {})
            matchup = play.get("matchup", {})

            inning = about.get("inning", 1)
            half = about.get("halfInning", "top")

            # Calcular carreras
            runs = sum(1 for runner in play.get("runners", [])
                       if runner.get("movement", {}).get("end") == "score")

            if half == "bottom":
                home_score += runs
            else:
                away_score += runs

            # Perspectiva Leones
            leones_score = home_score if leones_is_home else away_score
            opp_score = away_score if leones_is_home else home_score

            # Calcular WPA
            diff = leones_score - opp_score
            wp_after = calculate_wp(inning, diff)
            wpa = wp_after - prev_wp

            # Acumular WPA por jugador
            batter_id = matchup.get("batter", {}).get("id")
            batter_name = matchup.get("batter", {}).get("fullName", "Desconocido")
            pitcher_id = matchup.get("pitcher", {}).get("id")
            pitcher_name = matchup.get("pitcher", {}).get("fullName", "Desconocido")

            if batter_id:
                if batter_id not in wpa_data:
                    wpa_data[batter_id] = {"name": batter_name, "wpa_bat": 0, "wpa_pit": 0}
                wpa_data[batter_id]["wpa_bat"] += wpa

            if pitcher_id:
                if pitcher_id not in wpa_data:
                    wpa_data[pitcher_id] = {"name": pitcher_name, "wpa_bat": 0, "wpa_pit": 0}
                wpa_data[pitcher_id]["wpa_pit"] += wpa

            prev_wp = wp_after

        # Obtener roster de Leones
        try:
            box_url = f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore"
            box_response = requests.get(box_url, timeout=30)
            box = box_response.json()

            roster_ids = set()
            for side in ["home", "away"]:
                team_data = box.get("teams", {}).get(side, {})
                if team_data.get("team", {}).get("id") == TEAM_ID:
                    for player_id, _ in team_data.get("players", {}).items():
                        try:
                            roster_ids.add(int(player_id.replace("ID", "")))
                        except:
                            pass
        except:
            roster_ids = set()

        # Calcular WPA total y filtrar solo Leones
        mvp = None
        max_wpa = -999

        for player_id, data in wpa_data.items():
            if roster_ids and player_id not in roster_ids:
                continue

            total_wpa = data["wpa_bat"] + data["wpa_pit"]
            if total_wpa > max_wpa:
                max_wpa = total_wpa
                mvp = {
                    "name": data["name"],
                    "wpa_total": total_wpa,
                    "wpa_bat": data["wpa_bat"],
                    "wpa_pit": data["wpa_pit"]
                }

        return mvp

    except Exception as e:
        return None

# Cargar variables de entorno
load_dotenv()

# Configuración de la página
st.set_page_config(
    page_title="RepubliCaraquistApp",
    page_icon="logo.png",  # ← Tu logo como favicon
    layout="wide",
    initial_sidebar_state="expanded",
)
# app.py - Después de st.set_page_config()

# CSS para cambiar "app" por "Home" y alinearlo correctamente
st.markdown("""
    <style>
    /* Ocultar el texto "app" original */
    [data-testid="stSidebarNav"] a[href="/"] {
        position: relative;
    }
    
    [data-testid="stSidebarNav"] a[href="/"] span {
        visibility: hidden;
    }
    
    /* Agregar "Home" con la misma alineación */
    [data-testid="stSidebarNav"] a[href="/"]:after {
        content: "🏠 Home";
        visibility: visible;
        position: absolute;
        left: 0;
        top: 0;
        padding: 0.25rem 0.75rem;
        display: flex;
        align-items: center;
        width: 100%;
        height: 100%;
    }
    
    /* Mantener el hover effect */
    [data-testid="stSidebarNav"] a[href="/"]:hover:after {
        background-color: rgba(151, 166, 195, 0.15);
    }
    
    /* Cuando Home está seleccionado */
    [data-testid="stSidebarNav"] a[href="/"][aria-selected="true"]:after {
        font-weight: 600;
        background-color: rgba(151, 166, 195, 0.25);
    }
    
    /* Tu CSS existente */
    .main-header {
        font-size: 3rem;
        color: #FDB827;
        text-align: center;
        font-weight: bold;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .leones-gold {
        color: #FDB827;
    }
    .leones-red {
        color: #CE1141;
    }
    </style>
""", unsafe_allow_html=True)


# CSS personalizado
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        color: #FDB827;
        text-align: center;
        font-weight: bold;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        margin-top: -10px;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .leones-gold {
        color: #FDB827;
    }
    .leones-red {
        color: #010E50;
    }
    </style>
    """, unsafe_allow_html=True)

# Header principal - versión horizontal
col1, col2, col3 = st.columns([1, 3, 1])

with col1:
    st.write("")

with col2:
    col_logo, col_text = st.columns([1, 3])
    
    with col_logo:
        st.image("logo.png", width=120)
    
    with col_text:
        st.markdown("""
            <div style='padding-top: 20px;'>
                <h1 style='font-size: 2.5rem; color: #FDB827; font-weight: bold; 
                           text-shadow: 2px 2px 4px rgba(0,0,0,0.3); margin: 0;'>
                    RepubliCaraquistApp
                </h1>
                <p style='font-size: 1rem; color: #666; margin: 5px 0;'>
                    Análisis Avanzado de los Leones del Caracas - LVBP
                </p>
            </div>
        """, unsafe_allow_html=True)

with col3:
    st.write("")

# Importar funciones DESPUÉS del header
from utils.supabase_client import get_standings, get_recent_games, get_current_season, get_available_seasons

# Sidebar COMPLETO
with st.sidebar:
    st.image("logo.png", width=200)  # ← Usando tu logo.png local
    st.markdown("---")
    
    # Selector de temporada con formato correcto
    current_season = get_current_season()
    available_seasons = get_available_seasons()

    # Si no hay temporadas disponibles, usar la actual
    if not available_seasons:
        available_seasons = [current_season]

    # Crear diccionario para el selector con formato legible
    season_options = {}
    for season in available_seasons:
        # Formato: "2025-2026" para mostrar, 2025 como valor (año de inicio)
        display_text = f"{season}-{season+1}"
        season_options[display_text] = season

    # Determinar el índice de la temporada actual para seleccionarla por defecto
    current_season_display = f"{current_season}-{current_season+1}"
    season_list = list(season_options.keys())
    default_index = season_list.index(current_season_display) if current_season_display in season_list else 0

    # Selector con formato de temporada
    selected_season_display = st.selectbox(
        "⚾ Temporada",
        options=season_list,
        index=default_index
    )
    
    # Obtener el valor real de la temporada seleccionada
    selected_season = season_options[selected_season_display]
    
    # Mostrar temporada formateada
    st.markdown(f"### Temporada {selected_season_display}")
    
    st.markdown("**Liga Venezolana de Béisbol Profesional**")
    
    # Info de última actualización
    st.markdown("---")
    st.info(f"🔄 Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    # Links útiles
    st.markdown("---")
    st.markdown("### 🔗 Enlaces")
    st.markdown("[🌐 LVBP Oficial](https://www.lvbp.com)")
    st.markdown("[🦁 Leones del Caracas](https://www.leones.com)")
    st.markdown("[📊 MLB Stats API](https://statsapi.mlb.com)")

# CONTENIDO PRINCIPAL - Dashboard con datos reales
# Obtener datos reales
standings_df = get_standings(selected_season)  # Usar selected_season

# Datos de los Leones
if not standings_df.empty:
    # Asegurarse de que el DataFrame esté ordenado por PCT
    standings_df = standings_df.sort_values('pct', ascending=False).reset_index(drop=True)
    
    # Buscar datos de los Leones
    leones_data = standings_df[standings_df['team_name'].str.contains('Leones', case=False, na=False)]
    
    if not leones_data.empty:
        leones = leones_data.iloc[0]
        
        # Calcular posición correctamente después del reset_index
        # Buscar el índice donde están los Leones
        for idx, row in standings_df.iterrows():
            if 'Leones' in str(row['team_name']):
                position = idx + 1  # +1 porque el índice empieza en 0
                break
        else:
            position = 0  # Si no se encuentra
        
        position_text = f"{position}°"
        
        # Récord
        wins = int(leones.get('wins', 0))
        losses = int(leones.get('losses', 0))
        record_text = f"{wins}-{losses}"
        pct = leones.get('pct', 0)
        
        # Racha
        streak = leones.get('streak', 'N/A')
        
        # Diferencial
        run_diff = int(leones.get('run_diff', 0))
        runs_for = int(leones.get('runs_for', 0))
        runs_against = int(leones.get('runs_against', 0))
        
        # Récord
        wins = int(leones.get('wins', 0))
        losses = int(leones.get('losses', 0))
        record_text = f"{wins}-{losses}"
        pct = leones.get('pct', 0)
        
        # Racha
        streak = leones.get('streak', 'N/A')
        
        # Diferencial
        run_diff = int(leones.get('run_diff', 0))
        runs_for = int(leones.get('runs_for', 0))
        runs_against = int(leones.get('runs_against', 0))
    else:
        # Valores por defecto si no hay datos
        position_text = "N/A"
        position = 0
        record_text = "0-0"
        pct = 0
        streak = "N/A"
        run_diff = 0
        runs_for = 0
        runs_against = 0
else:
    # Sin datos - valores por defecto
    position_text = "N/A"
    position = 0
    record_text = "0-0"
    pct = 0
    streak = "N/A"
    run_diff = 0
    runs_for = 0
    runs_against = 0

# Mostrar métricas
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric(
        label="🏆 Posición",
        value=position_text,
        delta="En la tabla" if position > 0 else "Sin datos"
    )
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric(
        label="📊 Récord",
        value=record_text,
        delta=f".{int(pct*1000):03d} PCT" if pct > 0 else ".000 PCT"
    )
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric(
        label="🔥 Racha",
        value=streak,
        delta="Racha actual"
    )
    st.markdown('</div>', unsafe_allow_html=True)

with col4:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric(
        label="🎯 Diferencial",
        value=f"{run_diff:+d}" if run_diff != 0 else "0",
        delta=f"RF: {runs_for} | RA: {runs_against}"
    )
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# Tabs principales
tab1, tab2, tab3, tab4 = st.tabs(["📅 Último Juego", "📈 Tendencias", "🌟 Líderes del Equipo", "🦁 Leones Stats"])

with tab1:
    # Obtener último juego real
    recent_games = get_recent_games(team_id=695, limit=1)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 🆚 Último Resultado")
        
        if not recent_games.empty:
            last_game = recent_games.iloc[0]
            
            # Determinar si Leones ganó
            is_home = last_game['home_team_id'] == 695
            
            # Manejar datos anidados de manera segura
            if isinstance(last_game.get('away_team'), dict):
                away_team_name = last_game['away_team'].get('name', 'Rival')
            else:
                away_team_name = 'Rival'
                
            if isinstance(last_game.get('home_team'), dict):
                home_team_name = last_game['home_team'].get('name', 'Local')
            else:
                home_team_name = 'Local'
            
            if is_home:
                score_text = f"Leones del Caracas {last_game['home_score']} - {last_game['away_score']} {away_team_name}"
                won = last_game['home_score'] > last_game['away_score']
            else:
                score_text = f"{home_team_name} {last_game['home_score']} - {last_game['away_score']} Leones del Caracas"
                won = last_game['away_score'] > last_game['home_score']
            
            # Color según resultado
            bg_color = 'linear-gradient(135deg, #0A2342 0%, #15457C 100%)' if won else 'linear-gradient(135deg, #440C0C 0%, #8E2020 100%)'
            
            # Formatear fecha
            try:
                game_date = pd.to_datetime(last_game['game_date']).strftime('%d de %B, %Y')
            except:
                game_date = last_game.get('game_date', 'Fecha no disponible')
            
            st.markdown(f"""
            <div style='background: {bg_color}; 
                        padding: 2rem; border-radius: 1rem; color: white;'>
                <h2 style='text-align: center; margin: 0;'>
                    {score_text}
                </h2>
                <p style='text-align: center; margin-top: 1rem;'>
                    📅 {game_date} | 📍 {last_game.get('venue', 'Estadio')}
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("No hay juegos recientes disponibles")
    
    with col2:
        st.markdown("### ⭐ MVP de Leones")

        if not recent_games.empty:
            last_game = recent_games.iloc[0]
            game_pk = last_game.get('id')

            if game_pk:
                mvp_data = get_game_wpa_mvp(game_pk)

                if mvp_data:
                    wpa_color = "#196F3D" if mvp_data['wpa_total'] > 0 else "#922B21"

                    st.markdown(f"""
                    <div style='background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                                padding: 1.5rem; border-radius: 1rem; text-align: center;
                                border: 2px solid #FDB827;'>
                        <h2 style='color: #FDB827; margin: 0 0 0.5rem 0;'>
                            {mvp_data['name']}
                        </h2>
                        <p style='font-size: 2rem; color: {wpa_color}; margin: 0.5rem 0; font-weight: bold;'>
                            WPA: {mvp_data['wpa_total']:+.3f}
                        </p>
                        <div style='display: flex; justify-content: space-around; margin-top: 1rem;'>
                            <div>
                                <span style='color: #888; font-size: 0.8rem;'>Bateo</span><br>
                                <span style='color: white; font-weight: bold;'>{mvp_data['wpa_bat']:+.3f}</span>
                            </div>
                            <div>
                                <span style='color: #888; font-size: 0.8rem;'>Pitcheo</span><br>
                                <span style='color: white; font-weight: bold;'>{mvp_data['wpa_pit']:+.3f}</span>
                            </div>
                        </div>
                        <p style='color: #888; font-size: 0.75rem; margin-top: 1rem;'>
                            Win Probability Added
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info("No hay datos de WPA disponibles para este juego")
            else:
                st.info("ID del juego no disponible")
        else:
            st.info("No hay juegos recientes")

with tab2:
    st.markdown("### 📊 Últimos 10 Juegos")
    
    recent_10 = get_recent_games(team_id=695, limit=10)
    
    if not recent_10.empty:
        games_display = []
        grouped_by_date = recent_10.groupby('game_date')
        
        for date, group in grouped_by_date:
            game_count = len(group)
            for idx, game in enumerate(group.iterrows(), start=1):
                game = game[1]
                is_home = game['home_team_id'] == 695
                
                try:
                    fecha = pd.to_datetime(date).strftime('%d/%m')
                except:
                    fecha = 'N/A'
                
                if is_home:
                    rival = game.get('away_team', {}).get('abbreviation', 'RIV') if isinstance(game.get('away_team'), dict) else 'RIV'
                    resultado = 'W' if game['home_score'] > game['away_score'] else 'L'
                    marcador = f"{game['home_score']}-{game['away_score']}"
                else:
                    rival = f"@{game.get('home_team', {}).get('abbreviation', 'RIV')}" if isinstance(game.get('home_team'), dict) else '@RIV'
                    resultado = 'W' if game['away_score'] > game['home_score'] else 'L'
                    marcador = f"{game['away_score']}-{game['home_score']}"
                
                if game_count > 1:
                    rival = f"{rival} (Juego {idx})"
                
                games_display.append({
                    'Fecha': fecha,
                    'Rival': rival,
                    'Resultado': resultado,
                    'Marcador': marcador
                })
        
        df_games = pd.DataFrame(games_display)
        
        def color_result(val):
            if val == 'W':
                color = '#196F3D'
            else:
                color = '#922B21'
            return f'background-color: {color}'
        
        st.dataframe(
            df_games.style.applymap(color_result, subset=['Resultado']),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No hay datos de juegos recientes disponibles.")

with tab3:
    # Obtener estadísticas de bateo y pitcheo
    batting_df = get_batting_stats(team_id=695, limit=10, season=selected_season)
    pitching_df = get_pitching_stats(team_id=695, limit=10, season=selected_season)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🏏 Líderes de Bateo")
        st.caption("Ordenados por OPS (mín. 10 AB)")

        if not batting_df.empty:
            # Filtrar jugadores con mínimo de AB
            batting_filtered = batting_df[batting_df['ab'] >= 10].copy()

            if not batting_filtered.empty:
                # Preparar tabla de display
                display_batting = batting_filtered.head(5)[['player_name', 'avg', 'hr', 'rbi', 'ops', 'ab', 'h']].copy()
                display_batting.columns = ['Jugador', 'AVG', 'HR', 'RBI', 'OPS', 'AB', 'H']

                # Formatear AVG y OPS
                display_batting['AVG'] = display_batting['AVG'].apply(lambda x: f".{int(x*1000):03d}" if x < 1 else "1.000")
                display_batting['OPS'] = display_batting['OPS'].apply(lambda x: f"{x:.3f}")

                # Estilo para resaltar el líder
                def highlight_leader(row):
                    if row.name == display_batting.index[0]:
                        return ['background-color: rgba(253, 184, 39, 0.3); font-weight: bold'] * len(row)
                    return [''] * len(row)

                st.dataframe(
                    display_batting.style.apply(highlight_leader, axis=1),
                    use_container_width=True,
                    hide_index=True
                )

                # Mostrar líder destacado
                leader = batting_filtered.iloc[0]
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                            padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #FDB827;'>
                    <span style='color: #FDB827; font-weight: bold;'>👑 Líder OPS:</span>
                    <span style='color: white;'>{leader['player_name']}</span>
                    <span style='color: #888;'>({leader['ops']:.3f})</span>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("No hay suficientes datos (mín. 10 AB)")
        else:
            st.info("No hay datos de bateo disponibles")

    with col2:
        st.markdown("### ⚾ Líderes de Pitcheo")
        st.caption("Ordenados por ERA (mín. 5 IP)")

        if not pitching_df.empty:
            # Filtrar pitchers con mínimo de IP
            pitching_filtered = pitching_df[pitching_df['ip'] >= 5].copy()

            if not pitching_filtered.empty:
                # Ordenar por ERA (menor es mejor)
                pitching_filtered = pitching_filtered.sort_values('era', ascending=True)

                # Preparar tabla de display
                display_pitching = pitching_filtered.head(5)[['player_name', 'era', 'so', 'whip', 'ip', 'bb']].copy()
                display_pitching.columns = ['Jugador', 'ERA', 'K', 'WHIP', 'IP', 'BB']

                # Formatear ERA y WHIP
                display_pitching['ERA'] = display_pitching['ERA'].apply(lambda x: f"{x:.2f}")
                display_pitching['WHIP'] = display_pitching['WHIP'].apply(lambda x: f"{x:.2f}")
                display_pitching['IP'] = display_pitching['IP'].apply(lambda x: f"{x:.1f}")

                # Estilo para resaltar el líder
                def highlight_pitcher_leader(row):
                    if row.name == display_pitching.index[0]:
                        return ['background-color: rgba(253, 184, 39, 0.3); font-weight: bold'] * len(row)
                    return [''] * len(row)

                st.dataframe(
                    display_pitching.style.apply(highlight_pitcher_leader, axis=1),
                    use_container_width=True,
                    hide_index=True
                )

                # Mostrar líder destacado
                leader_pit = pitching_filtered.iloc[0]
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                            padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #FDB827;'>
                    <span style='color: #FDB827; font-weight: bold;'>👑 Líder ERA:</span>
                    <span style='color: white;'>{leader_pit['player_name']}</span>
                    <span style='color: #888;'>({leader_pit['era']:.2f})</span>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("No hay suficientes datos (mín. 5 IP)")
        else:
            st.info("No hay datos de pitcheo disponibles")

st.markdown("---")

with tab4:
    st.markdown("### 🦁 Leones del Caracas 25-26")
    
    # Obtener estadísticas avanzadas
    advanced_stats = get_leones_advanced_stats(selected_season)
    
    if advanced_stats:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**Juego N°{advanced_stats['total_games']} ({advanced_stats['record']})**")
            st.markdown(f"**Home Club:** {advanced_stats['home_record']}")
            st.markdown(f"**Visitante:** {advanced_stats['away_record']}")
            st.markdown(f"**De noche:** {advanced_stats['night_record']}")
            st.markdown(f"**Blanqueo:** {advanced_stats['shutouts']}")
            st.markdown(f"**Racha:** {advanced_stats['streak']}")
            st.markdown(f"**En extrainning:** {advanced_stats['extra_inning']}")
            st.markdown(f"**Ult-10J:** {advanced_stats['last_10']}")
        
        with col2:
            st.markdown(f"**Por 1 Carrera:** {advanced_stats['one_run']}")
            st.markdown(f"**Remontados:** {advanced_stats['remontados']}")
            st.markdown(f"**Arriba:** {advanced_stats['up']}")
            st.markdown(f"**Terreneadas:** {advanced_stats['blown_leads']}")
            st.markdown(f"**Abridores:** {advanced_stats['starters']}")
            st.markdown(f"**Relevistas:** {advanced_stats['relievers']}")
            st.markdown(f"**Salvados:** {advanced_stats['saves']}")
            st.markdown(f"**OCT:** {advanced_stats['oct']}")
            st.markdown(f"**NOV:** {advanced_stats['nov']}")
            st.markdown(f"**DEC:** {advanced_stats['dec']}")
    else:
        st.info("No hay datos disponibles para estadísticas avanzadas.")

# Footer
st.markdown("""
<div style='text-align: center; color: #666; padding: 2rem;'>
    <p>Desarrollado por Jorge Leonardo Loreto</p>
    <p>📊 Científico de Datos | ⚾ Analista de Béisbol | 🦁 Fanático de los Leones del Caracas</p>
    <p>Twitter: @JorgeLoreto / @RepubCaraquista</p>
    <p>📊 Datos actualizados diariamente a las 2:00 AM VET</p>
    <p>Powered by MLB Stats API & Supabase</p>
</div>
""", unsafe_allow_html=True)

# Información de navegación
st.info("👈 **Navega por las diferentes secciones usando el menú lateral**")

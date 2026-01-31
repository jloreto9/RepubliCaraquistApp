# pages/3_📈_Análisis_WPA.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime
import sys
import os

# Agregar el directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar funciones de Supabase
try:
    from utils.supabase_client import init_supabase, get_available_seasons, get_current_season
except:
    from streamlit_app.utils.supabase_client import init_supabase, get_available_seasons, get_current_season

# Configuración de la página
st.set_page_config(
    page_title="Análisis WPA - RepubliCaraquistApp",
    page_icon="📈",
    layout="wide"
)

# Constantes
TEAM_ID = 695  # Leones del Caracas
LEONES_GOLD = "#FDB827"
LEONES_RED = "#CE1141"

# ========================================
# FUNCIONES DE CÁLCULO WPA
# ========================================

def calculate_wp(inning: int, diff: int) -> float:
    """Calcula Win Probability simple basado en inning y diferencial"""
    leverage = min(inning / 9.0, 1.0)
    wp = 1.0 / (1.0 + np.exp(-0.75 * diff))
    return max(0.0, min(1.0, wp + 0.25 * leverage * (wp - 0.5)))


@st.cache_data(ttl=300)
def get_leones_games_from_supabase(season: int) -> pd.DataFrame:
    """Obtiene todos los juegos de Leones desde Supabase"""
    supabase = init_supabase()

    try:
        response = supabase.table('games') \
            .select('*') \
            .eq('season', season) \
            .in_('status', ['Final', 'Completed', 'Completed Early']) \
            .or_(f'home_team_id.eq.{TEAM_ID},away_team_id.eq.{TEAM_ID}') \
            .order('game_date', desc=True) \
            .execute()

        if response.data:
            df = pd.DataFrame(response.data)
            return df
    except Exception as e:
        st.error(f"Error obteniendo juegos: {str(e)}")

    return pd.DataFrame()


@st.cache_data(ttl=600)
def process_game_feed(game_pk: int) -> tuple:
    """Procesa el feed del juego desde la API de MLB y calcula WPA"""
    try:
        url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
        response = requests.get(url, timeout=30)
        feed = response.json()
    except Exception as e:
        return pd.DataFrame(), False, str(e)

    # Identificar si Leones es local o visitante
    try:
        home_id = feed["gameData"]["teams"]["home"]["id"]
        leones_is_home = (home_id == TEAM_ID)

        home_name = feed["gameData"]["teams"]["home"]["name"]
        away_name = feed["gameData"]["teams"]["away"]["name"]
    except:
        return pd.DataFrame(), False, "Error en datos del juego"

    # Procesar jugadas
    all_plays = feed.get("liveData", {}).get("plays", {}).get("allPlays", [])

    if not all_plays:
        return pd.DataFrame(), leones_is_home, "No hay jugadas disponibles"

    wpa_rows = []
    prev_wp = 0.5
    home_score = away_score = 0

    for idx, play in enumerate(all_plays):
        about = play.get("about", {})
        result = play.get("result", {})
        matchup = play.get("matchup", {})

        inning = about.get("inning", 1)
        half = about.get("halfInning", "top")

        # Calcular carreras anotadas
        runs = sum(1 for runner in play.get("runners", [])
                   if runner.get("movement", {}).get("end") == "score")

        # Actualizar score
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

        # Determinar si el bateador/pitcher es de Leones
        batter_team = matchup.get("batter", {}).get("parentTeamId")
        pitcher_team = matchup.get("pitcher", {}).get("parentTeamId")

        wpa_rows.append({
            "atbat_index": idx,
            "inning": inning,
            "halfInning": half,
            "batter_id": matchup.get("batter", {}).get("id"),
            "batter": matchup.get("batter", {}).get("fullName", "Desconocido"),
            "pitcher_id": matchup.get("pitcher", {}).get("id"),
            "pitcher": matchup.get("pitcher", {}).get("fullName", "Desconocido"),
            "eventType": result.get("event", ""),
            "description": result.get("description", ""),
            "leones_before": leones_score - (runs if half == ("bottom" if leones_is_home else "top") else 0),
            "opp_before": opp_score - (runs if half != ("bottom" if leones_is_home else "top") else 0),
            "leones_after": leones_score,
            "opp_after": opp_score,
            "wp_before": prev_wp,
            "wp_after": wp_after,
            "wpa": wpa,
            "batter_is_leones": batter_team == TEAM_ID if batter_team else None,
            "pitcher_is_leones": pitcher_team == TEAM_ID if pitcher_team else None
        })

        prev_wp = wp_after

    # Ajustar WPA final
    if wpa_rows:
        final_diff = wpa_rows[-1]["leones_after"] - wpa_rows[-1]["opp_after"]
        final_wp = 1.0 if final_diff > 0 else 0.0
        wpa_rows[-1]["wp_after"] = final_wp
        wpa_rows[-1]["wpa"] = final_wp - wpa_rows[-1]["wp_before"]

    return pd.DataFrame(wpa_rows), leones_is_home, None


@st.cache_data(ttl=600)
def get_game_roster(game_pk: int) -> set:
    """Obtiene los IDs de jugadores de Leones que participaron en el juego"""
    try:
        url = f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore"
        response = requests.get(url, timeout=30)
        box = response.json()

        players = set()

        for side in ["home", "away"]:
            team_data = box.get("teams", {}).get(side, {})
            if team_data.get("team", {}).get("id") == TEAM_ID:
                for player_id, player_data in team_data.get("players", {}).items():
                    players.add(player_data.get("person", {}).get("id"))

        return players
    except:
        return set()


def calculate_player_wpa(df_wpa: pd.DataFrame, roster_ids: set) -> pd.DataFrame:
    """Calcula WPA total por jugador"""
    # WPA como bateador
    wpa_bat = df_wpa.groupby(["batter_id", "batter"])["wpa"].sum().reset_index()
    wpa_bat.columns = ["player_id", "player", "wpa_bat"]

    # WPA como pitcher (invertido - bueno para el pitcher si el bateador hace negativo)
    wpa_pit = df_wpa.groupby(["pitcher_id", "pitcher"])["wpa"].sum().reset_index()
    wpa_pit.columns = ["player_id", "player", "wpa_pit"]

    # Combinar
    wpa_total = pd.merge(wpa_bat, wpa_pit, on=["player_id", "player"], how="outer").fillna(0)

    # Filtrar solo jugadores de Leones si tenemos el roster
    if roster_ids:
        wpa_total = wpa_total[wpa_total["player_id"].isin(roster_ids)]

    wpa_total["WPA_total"] = wpa_total["wpa_bat"] + wpa_total["wpa_pit"]
    wpa_total = wpa_total.sort_values("WPA_total", ascending=False)

    return wpa_total


# ========================================
# FUNCIONES DE VISUALIZACIÓN
# ========================================

def create_wp_evolution_chart(df_wpa: pd.DataFrame, game_info: dict) -> go.Figure:
    """Crea gráfico de evolución de Win Probability"""
    # Preparar datos
    df_plot = df_wpa.copy()
    df_plot['play_number'] = range(len(df_plot))

    # Agregar punto inicial
    initial_row = pd.DataFrame({
        'play_number': [-1],
        'wp_after': [0.5],
        'inning': [1]
    })
    df_plot = pd.concat([initial_row, df_plot], ignore_index=True)
    df_plot = df_plot.sort_values('play_number').reset_index(drop=True)

    fig = go.Figure()

    # Línea principal de WP
    fig.add_trace(go.Scatter(
        x=df_plot['play_number'],
        y=df_plot['wp_after'],
        mode='lines',
        name='Win Probability',
        line=dict(color=LEONES_GOLD, width=3),
        hovertemplate='Jugada %{x}<br>WP: %{y:.1%}<extra></extra>'
    ))

    # Área de ventaja Leones
    fig.add_trace(go.Scatter(
        x=df_plot['play_number'],
        y=df_plot['wp_after'].where(df_plot['wp_after'] >= 0.5, 0.5),
        fill='tonexty',
        fillcolor='rgba(253, 184, 39, 0.3)',
        line=dict(width=0),
        name='Ventaja Leones',
        showlegend=True,
        hoverinfo='skip'
    ))

    # Línea base 50%
    fig.add_trace(go.Scatter(
        x=df_plot['play_number'],
        y=[0.5] * len(df_plot),
        mode='lines',
        line=dict(color='gray', width=1, dash='dash'),
        name='50%',
        showlegend=False,
        hoverinfo='skip'
    ))

    # Área de ventaja rival
    fig.add_trace(go.Scatter(
        x=df_plot['play_number'],
        y=df_plot['wp_after'].where(df_plot['wp_after'] < 0.5, 0.5),
        fill='tonexty',
        fillcolor='rgba(139, 0, 0, 0.3)',
        line=dict(width=0),
        name='Ventaja Rival',
        showlegend=True,
        hoverinfo='skip'
    ))

    # Marcar jugadas clave positivas
    top_positive = df_wpa.nlargest(3, 'wpa')
    for _, play in top_positive.iterrows():
        play_num = play['atbat_index'] + 1
        wp_val = play['wp_after']
        fig.add_trace(go.Scatter(
            x=[play_num],
            y=[wp_val],
            mode='markers+text',
            marker=dict(color='green', size=12, symbol='triangle-up'),
            text=[f"{play['batter'][:10]}<br>+{play['wpa']:.2f}"],
            textposition='top center',
            textfont=dict(size=9, color='darkgreen'),
            name=f"+ {play['batter'][:15]}",
            showlegend=False
        ))

    # Marcar jugadas clave negativas
    top_negative = df_wpa[df_wpa['wpa'] < -0.05].nsmallest(3, 'wpa')
    for _, play in top_negative.iterrows():
        play_num = play['atbat_index'] + 1
        wp_val = play['wp_after']
        fig.add_trace(go.Scatter(
            x=[play_num],
            y=[wp_val],
            mode='markers+text',
            marker=dict(color='red', size=12, symbol='triangle-down'),
            text=[f"{play['batter'][:10]}<br>{play['wpa']:.2f}"],
            textposition='bottom center',
            textfont=dict(size=9, color='darkred'),
            name=f"- {play['batter'][:15]}",
            showlegend=False
        ))

    # Configuración del layout
    final_wp = df_plot.iloc[-1]['wp_after']
    result_text = "GANARON" if final_wp == 1.0 else "PERDIERON"
    result_color = LEONES_GOLD if final_wp == 1.0 else LEONES_RED

    fig.update_layout(
        title=dict(
            text=f"Evolución Win Probability - Leones del Caracas<br><sub>{game_info.get('matchup', '')}</sub>",
            font=dict(size=16)
        ),
        xaxis_title="Progreso del Juego (Jugadas)",
        yaxis_title="Win Probability",
        yaxis=dict(
            tickformat='.0%',
            range=[-0.05, 1.05],
            tickvals=[0, 0.25, 0.5, 0.75, 1.0]
        ),
        height=500,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode='x unified',
        annotations=[
            dict(
                x=0.98, y=0.95,
                xref='paper', yref='paper',
                text=f"<b>Leones {result_text}</b>",
                showarrow=False,
                font=dict(size=14, color=result_color),
                bgcolor='rgba(255,255,255,0.8)',
                bordercolor=result_color,
                borderwidth=2,
                borderpad=4
            )
        ]
    )

    return fig


def create_wpa_by_inning_chart(df_wpa: pd.DataFrame) -> go.Figure:
    """Crea gráfico de WPA acumulado por inning"""
    wpa_by_inning = df_wpa.groupby('inning')['wpa'].sum().reset_index()

    colors = [LEONES_GOLD if x > 0 else LEONES_RED for x in wpa_by_inning['wpa']]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=wpa_by_inning['inning'],
        y=wpa_by_inning['wpa'],
        marker_color=colors,
        text=wpa_by_inning['wpa'].apply(lambda x: f'{x:+.2f}' if abs(x) > 0.01 else ''),
        textposition='outside',
        textfont=dict(size=10, color='white'),
        hovertemplate='Inning %{x}<br>WPA: %{y:+.3f}<extra></extra>'
    ))

    fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=1)

    fig.update_layout(
        title="WPA Acumulado por Inning",
        xaxis_title="Inning",
        yaxis_title="WPA",
        height=350,
        showlegend=False,
        xaxis=dict(tickmode='linear', tick0=1, dtick=1)
    )

    return fig


def create_score_evolution_chart(df_wpa: pd.DataFrame) -> go.Figure:
    """Crea gráfico de evolución del marcador"""
    score_by_inning = df_wpa.groupby('inning').agg({
        'leones_after': 'last',
        'opp_after': 'last'
    }).reset_index()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=score_by_inning['inning'],
        y=score_by_inning['leones_after'],
        mode='lines+markers+text',
        name='Leones',
        line=dict(color=LEONES_GOLD, width=3),
        marker=dict(size=10),
        text=score_by_inning['leones_after'].astype(int),
        textposition='top center',
        textfont=dict(color=LEONES_GOLD, size=10)
    ))

    fig.add_trace(go.Scatter(
        x=score_by_inning['inning'],
        y=score_by_inning['opp_after'],
        mode='lines+markers+text',
        name='Rival',
        line=dict(color=LEONES_RED, width=3),
        marker=dict(size=10, symbol='square'),
        text=score_by_inning['opp_after'].astype(int),
        textposition='bottom center',
        textfont=dict(color=LEONES_RED, size=10)
    ))

    fig.update_layout(
        title="Evolución del Marcador",
        xaxis_title="Inning",
        yaxis_title="Carreras",
        height=350,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        xaxis=dict(tickmode='linear', tick0=1, dtick=1),
        yaxis=dict(rangemode='tozero')
    )

    return fig


def create_heroes_villains_chart(wpa_total: pd.DataFrame) -> go.Figure:
    """Crea gráfico de héroes y villanos"""
    if wpa_total.empty:
        return go.Figure()

    # Top 5 mejores y peores
    top_5_best = wpa_total.nlargest(5, 'WPA_total')
    top_5_worst = wpa_total[wpa_total['WPA_total'] < -0.01].nsmallest(5, 'WPA_total')

    top_players = pd.concat([top_5_best, top_5_worst]).drop_duplicates().sort_values('WPA_total')

    if top_players.empty:
        return go.Figure()

    colors = [LEONES_GOLD if x > 0 else LEONES_RED for x in top_players['WPA_total']]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=top_players['player'],
        x=top_players['WPA_total'],
        orientation='h',
        marker_color=colors,
        text=top_players['WPA_total'].apply(lambda x: f'{x:+.3f}'),
        textposition='outside',
        textfont=dict(size=10),
        hovertemplate='%{y}<br>WPA Total: %{x:+.3f}<extra></extra>'
    ))

    fig.add_vline(x=0, line_dash="solid", line_color="black", line_width=1)

    # Calcular límites del eje X
    x_max = max(abs(top_players['WPA_total'].max()), abs(top_players['WPA_total'].min())) * 1.3

    fig.update_layout(
        title="Héroes y Villanos - Contribución WPA",
        xaxis_title="WPA Total",
        yaxis_title="",
        height=400,
        showlegend=False,
        xaxis=dict(range=[-x_max, x_max])
    )

    return fig


# ========================================
# INTERFAZ PRINCIPAL
# ========================================

st.title("📈 Análisis WPA (Win Probability Added)")
st.markdown("### Leones del Caracas")

# Sidebar - Selector de temporada y juego
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/8/89/Leones_del_Caracas_logo.svg/200px-Leones_del_Caracas_logo.svg.png", width=100)

    st.markdown("---")

    # Selector de temporada
    current_season = get_current_season()
    available_seasons = get_available_seasons()

    if not available_seasons:
        available_seasons = [current_season]

    season_options = {f"{s}-{s+1}": s for s in available_seasons}
    season_list = list(season_options.keys())
    current_display = f"{current_season}-{current_season+1}"
    default_idx = season_list.index(current_display) if current_display in season_list else 0

    selected_season_display = st.selectbox(
        "Temporada",
        options=season_list,
        index=default_idx
    )
    selected_season = season_options[selected_season_display]

    st.markdown("---")

    # Información
    with st.expander("ℹ️ ¿Qué es WPA?"):
        st.markdown("""
        **Win Probability Added (WPA)** mide cuánto contribuyó cada jugada al resultado final del juego.

        - **WPA positivo**: La jugada aumentó las probabilidades de ganar de Leones
        - **WPA negativo**: La jugada disminuyó las probabilidades

        Un jugador con alto WPA fue decisivo en la victoria, mientras que WPA negativo indica jugadas que costaron el juego.
        """)

# Obtener juegos de Supabase
df_games = get_leones_games_from_supabase(selected_season)

if df_games.empty:
    st.warning(f"No hay juegos finalizados para la temporada {selected_season_display}")
    st.stop()

# Diccionario de nombres de equipos
TEAM_NAMES = {
    695: "Leones",
    698: "Tiburones",
    696: "Magallanes",
    699: "Tigres",
    692: "Águilas",
    693: "Cardenales",
    694: "Caribes",
    697: "Margarita"
}

# Preparar opciones de juegos
game_options = []
for _, game in df_games.iterrows():
    try:
        fecha = pd.to_datetime(game['game_date']).strftime('%d/%m/%Y')
    except:
        fecha = str(game.get('game_date', 'N/A'))[:10]

    is_home = game['home_team_id'] == TEAM_ID

    if is_home:
        rival_id = game['away_team_id']
        rival_name = TEAM_NAMES.get(rival_id, f"Equipo {rival_id}")
        matchup = f"vs {rival_name}"
        score = f"{game.get('home_score', '?')}-{game.get('away_score', '?')}"
    else:
        rival_id = game['home_team_id']
        rival_name = TEAM_NAMES.get(rival_id, f"Equipo {rival_id}")
        matchup = f"@ {rival_name}"
        score = f"{game.get('away_score', '?')}-{game.get('home_score', '?')}"

    # Determinar resultado
    leones_score = game['home_score'] if is_home else game['away_score']
    opp_score = game['away_score'] if is_home else game['home_score']
    result = "V" if leones_score > opp_score else "D"
    result_emoji = "✅" if result == "V" else "❌"

    game_options.append({
        'id': game['id'],
        'display': f"{fecha} | {matchup} | {score} {result_emoji}",
        'matchup': f"{fecha} - Leones {matchup} ({score})",
        'is_home': is_home,
        'rival': rival_name
    })

# Selector de juego
st.markdown("### Seleccionar Juego")

col1, col2 = st.columns([3, 1])

with col1:
    selected_game_display = st.selectbox(
        "Juego a analizar",
        options=[g['display'] for g in game_options],
        index=0,
        label_visibility="collapsed"
    )

# Encontrar el juego seleccionado
selected_game = next((g for g in game_options if g['display'] == selected_game_display), None)

if selected_game is None:
    st.error("Error seleccionando juego")
    st.stop()

game_pk = selected_game['id']

with col2:
    analyze_btn = st.button("🔍 Analizar", type="primary", use_container_width=True)

# Procesar juego
if analyze_btn or 'last_game_pk' not in st.session_state or st.session_state.last_game_pk != game_pk:
    st.session_state.last_game_pk = game_pk

    with st.spinner("Procesando datos del juego..."):
        df_wpa, leones_is_home, error = process_game_feed(game_pk)

        if error:
            st.error(f"Error procesando juego: {error}")
            st.stop()

        if df_wpa.empty:
            st.warning("No hay datos de jugadas disponibles para este juego")
            st.stop()

        # Obtener roster
        roster_ids = get_game_roster(game_pk)

        # Calcular WPA por jugador
        wpa_total = calculate_player_wpa(df_wpa, roster_ids)

        # Guardar en session state
        st.session_state.df_wpa = df_wpa
        st.session_state.wpa_total = wpa_total
        st.session_state.leones_is_home = leones_is_home
        st.session_state.game_info = selected_game

# Mostrar resultados si hay datos
if 'df_wpa' in st.session_state and not st.session_state.df_wpa.empty:
    df_wpa = st.session_state.df_wpa
    wpa_total = st.session_state.wpa_total
    game_info = st.session_state.game_info

    # Resultado del juego
    final_leones = df_wpa.iloc[-1]['leones_after']
    final_opp = df_wpa.iloc[-1]['opp_after']
    won = final_leones > final_opp

    # Métricas principales
    st.markdown("---")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        result_text = "VICTORIA" if won else "DERROTA"
        result_color = "normal" if won else "inverse"
        st.metric("Resultado", result_text, f"{int(final_leones)}-{int(final_opp)}")

    with col2:
        wp_max = df_wpa['wp_after'].max()
        st.metric("WP Máximo", f"{wp_max:.1%}")

    with col3:
        wp_min = df_wpa['wp_after'].min()
        st.metric("WP Mínimo", f"{wp_min:.1%}")

    with col4:
        big_plays = (df_wpa['wpa'].abs() > 0.1).sum()
        st.metric("Jugadas Grandes", big_plays, "(|WPA| > 0.1)")

    with col5:
        if not wpa_total.empty:
            mvp = wpa_total.iloc[0]
            st.metric("MVP", mvp['player'][:15], f"WPA: {mvp['WPA_total']:+.3f}")

    st.markdown("---")

    # Tabs de visualización
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Evolución WP",
        "📊 Por Inning",
        "🦸 Héroes/Villanos",
        "📋 Detalle Jugadas"
    ])

    with tab1:
        # Gráfico principal de evolución
        fig_wp = create_wp_evolution_chart(df_wpa, game_info)
        st.plotly_chart(fig_wp, use_container_width=True)

        # Jugadas clave
        st.markdown("#### ⚡ Jugadas Clave")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**🔥 Mejores Jugadas**")
            top_plays = df_wpa.nlargest(5, 'wpa')[['inning', 'batter', 'eventType', 'wpa']].copy()
            top_plays['wpa'] = top_plays['wpa'].apply(lambda x: f"+{x:.3f}")
            top_plays.columns = ['Inning', 'Bateador', 'Resultado', 'WPA']
            st.dataframe(top_plays, use_container_width=True, hide_index=True)

        with col2:
            st.markdown("**💔 Peores Jugadas**")
            bottom_plays = df_wpa.nsmallest(5, 'wpa')[['inning', 'batter', 'eventType', 'wpa']].copy()
            bottom_plays['wpa'] = bottom_plays['wpa'].apply(lambda x: f"{x:.3f}")
            bottom_plays.columns = ['Inning', 'Bateador', 'Resultado', 'WPA']
            st.dataframe(bottom_plays, use_container_width=True, hide_index=True)

    with tab2:
        col1, col2 = st.columns(2)

        with col1:
            fig_inning = create_wpa_by_inning_chart(df_wpa)
            st.plotly_chart(fig_inning, use_container_width=True)

        with col2:
            fig_score = create_score_evolution_chart(df_wpa)
            st.plotly_chart(fig_score, use_container_width=True)

        # Innings críticos
        wpa_by_inning = df_wpa.groupby('inning')['wpa'].sum()
        critical_innings = wpa_by_inning[wpa_by_inning.abs() > 0.15]

        if not critical_innings.empty:
            st.markdown("#### ⚡ Innings Críticos (|WPA| > 0.15)")
            for inning, wpa in critical_innings.items():
                emoji = "🔥" if wpa > 0 else "💔"
                color = "green" if wpa > 0 else "red"
                st.markdown(f"{emoji} **{inning}° inning**: WPA <span style='color:{color}'>{wpa:+.3f}</span>", unsafe_allow_html=True)

    with tab3:
        if not wpa_total.empty:
            col1, col2 = st.columns([2, 1])

            with col1:
                fig_heroes = create_heroes_villains_chart(wpa_total)
                st.plotly_chart(fig_heroes, use_container_width=True)

            with col2:
                st.markdown("#### 🏆 Ranking WPA")

                # MVP
                mvp = wpa_total.iloc[0]
                st.success(f"**MVP**: {mvp['player']}\n\nWPA: {mvp['WPA_total']:+.3f}")

                # LVP
                if wpa_total['WPA_total'].min() < -0.05:
                    lvp = wpa_total.iloc[-1]
                    st.error(f"**LVP**: {lvp['player']}\n\nWPA: {lvp['WPA_total']:+.3f}")

            # Tabla completa
            st.markdown("#### 📋 WPA por Jugador (Leones)")

            display_wpa = wpa_total.head(15).copy()
            display_wpa['wpa_bat'] = display_wpa['wpa_bat'].apply(lambda x: f"{x:+.3f}" if x != 0 else "0.000")
            display_wpa['wpa_pit'] = display_wpa['wpa_pit'].apply(lambda x: f"{x:+.3f}" if x != 0 else "0.000")
            display_wpa['WPA_total'] = display_wpa['WPA_total'].apply(lambda x: f"{x:+.3f}" if x != 0 else "0.000")

            display_wpa = display_wpa[['player', 'wpa_bat', 'wpa_pit', 'WPA_total']]
            display_wpa.columns = ['Jugador', 'WPA Bateo', 'WPA Pitcheo', 'WPA Total']

            st.dataframe(display_wpa, use_container_width=True, hide_index=True)
        else:
            st.info("No hay datos de WPA por jugador disponibles")

    with tab4:
        st.markdown("#### 📋 Todas las Jugadas")

        # Filtros
        col1, col2, col3 = st.columns(3)

        with col1:
            inning_filter = st.multiselect(
                "Filtrar por Inning",
                options=sorted(df_wpa['inning'].unique()),
                default=[]
            )

        with col2:
            min_wpa = st.slider(
                "WPA mínimo (absoluto)",
                min_value=0.0,
                max_value=0.5,
                value=0.0,
                step=0.01
            )

        with col3:
            event_filter = st.multiselect(
                "Tipo de Evento",
                options=sorted(df_wpa['eventType'].unique()),
                default=[]
            )

        # Aplicar filtros
        df_filtered = df_wpa.copy()

        if inning_filter:
            df_filtered = df_filtered[df_filtered['inning'].isin(inning_filter)]

        if min_wpa > 0:
            df_filtered = df_filtered[df_filtered['wpa'].abs() >= min_wpa]

        if event_filter:
            df_filtered = df_filtered[df_filtered['eventType'].isin(event_filter)]

        # Mostrar tabla
        display_cols = ['inning', 'halfInning', 'batter', 'pitcher', 'eventType', 'wpa', 'wp_after']
        df_display = df_filtered[display_cols].copy()
        df_display['wpa'] = df_display['wpa'].apply(lambda x: f"{x:+.3f}")
        df_display['wp_after'] = df_display['wp_after'].apply(lambda x: f"{x:.1%}")
        df_display['halfInning'] = df_display['halfInning'].map({'top': '▲', 'bottom': '▼'})
        df_display.columns = ['Inn', '', 'Bateador', 'Pitcher', 'Evento', 'WPA', 'WP']

        st.dataframe(df_display, use_container_width=True, hide_index=True, height=400)

        st.caption(f"Mostrando {len(df_filtered)} de {len(df_wpa)} jugadas")

else:
    st.info("👆 Selecciona un juego y presiona **Analizar** para ver el análisis WPA")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>📈 Análisis WPA | Datos: MLB Stats API</p>
    <p>Win Probability calculado con modelo simplificado basado en inning y diferencial</p>
</div>
""", unsafe_allow_html=True)

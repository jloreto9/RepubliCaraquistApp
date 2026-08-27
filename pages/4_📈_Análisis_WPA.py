# pages/3_📈_Análisis_WPA.py
"""
Módulo de Análisis Avanzado de Win Probability Added (WPA), Leverage Index (LI)
y Modelado de Situaciones Críticas para los Leones del Caracas (LVBP).
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys
import os

# Path imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from utils.supabase_client import init_supabase, get_available_seasons, get_current_season
    from utils.teams import (
        LVBP_TEAMS,
        LVBP_ABBR,
        LVBP_COLORS,
        get_team_logo,
        get_team_name,
        get_team_abbr,
        get_team_color,
        resolve_team_id,
        get_brand_logo
    )
    from utils.wpa_engine import (
        process_game_wpa_advanced,
        calculate_player_game_wpa,
        get_season_wpa_leaderboard,
        format_base_state
    )
except Exception:
    from streamlit_app.utils.supabase_client import init_supabase, get_available_seasons, get_current_season
    from streamlit_app.utils.teams import (
        LVBP_TEAMS,
        LVBP_ABBR,
        LVBP_COLORS,
        get_team_logo,
        get_team_name,
        get_team_abbr,
        get_team_color,
        resolve_team_id,
        get_brand_logo
    )
    from streamlit_app.utils.wpa_engine import (
        process_game_wpa_advanced,
        calculate_player_game_wpa,
        get_season_wpa_leaderboard,
        format_base_state
    )

st.set_page_config(
    page_title="Análisis WPA & Apalancamiento - RepubliCaraquistApp",
    page_icon="📈",
    layout="wide"
)

try:
    from utils.styles import inject_custom_css
    inject_custom_css()
except:
    pass

TEAM_ID = 695  # Leones del Caracas
LEONES_GOLD = "#FDB827"
LEONES_RED = "#CE1141"
LEONES_NAVY = "#0C2340"

TEAM_NAMES = LVBP_TEAMS


@st.cache_data(ttl=300)
def get_leones_games_from_supabase(season: int) -> pd.DataFrame:
    """Obtiene todos los juegos finalizados de Leones desde Supabase"""
    supabase = init_supabase()
    try:
        response = supabase.table('games') \
            .select('*') \
            .eq('season', season) \
            .in_('status', ['Final', 'Completed', 'Completed Early', 'Game Over']) \
            .or_(f'home_team_id.eq.{TEAM_ID},away_team_id.eq.{TEAM_ID}') \
            .order('game_date', desc=True) \
            .execute()
        if response.data:
            return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error obteniendo juegos: {str(e)}")
    return pd.DataFrame()


# ========================================
# FUNCIONES DE VISUALIZACIÓN
# ========================================

def create_wp_evolution_chart(df_wpa: pd.DataFrame, game_info: dict) -> go.Figure:
    """Crea gráfico de evolución de Win Probability con datos de apalancamiento y bases"""
    df_plot = df_wpa.copy()
    df_plot['play_number'] = range(1, len(df_plot) + 1)

    # Punto inicial
    initial_row = pd.DataFrame([{
        'play_number': 0,
        'wp_after': 0.50,
        'inning': 1,
        'halfInning': 'top',
        'score_str': '0-0',
        'batter': 'Inicio del juego',
        'pitcher': 'Abridor',
        'eventType': 'Play Ball',
        'base_icons': '◇ ◇ ◇',
        'outs_before': 0,
        'li': 1.0,
        'wpa': 0.0
    }])
    df_plot = pd.concat([initial_row, df_plot], ignore_index=True)

    fig = go.Figure()

    # Área de ventaja Leones (> 50%)
    fig.add_trace(go.Scatter(
        x=df_plot['play_number'],
        y=df_plot['wp_after'].where(df_plot['wp_after'] >= 0.5, 0.5),
        fill='tonexty',
        fillcolor='rgba(253, 184, 39, 0.25)',
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
        line=dict(color='rgba(150, 150, 150, 0.6)', width=1.5, dash='dash'),
        name='Empate (50%)',
        showlegend=False,
        hoverinfo='skip'
    ))

    # Área de ventaja rival (< 50%)
    fig.add_trace(go.Scatter(
        x=df_plot['play_number'],
        y=df_plot['wp_after'].where(df_plot['wp_after'] < 0.5, 0.5),
        fill='tonexty',
        fillcolor='rgba(206, 17, 65, 0.20)',
        line=dict(width=0),
        name='Ventaja Rival',
        showlegend=True,
        hoverinfo='skip'
    ))

    # Línea principal de Win Probability
    custom_text = [
        f"<b>Jugada #{r['play_number']}</b> ({'▲' if r['halfInning']=='top' else '▼'}Inn {r['inning']})<br>"
        f"⚾ <b>{r['batter']}</b> vs {r['pitcher']}<br>"
        f"📌 Evento: <b>{r['eventType']}</b><br>"
        f"🏃 Bases: {r.get('base_icons', '◇ ◇ ◇')} | Outs: {r.get('outs_before', 0)}<br>"
        f"🔢 Marcador: <b>{r['score_str']}</b><br>"
        f"📈 WP: <b>{r['wp_after']:.1%}</b> (WPA: <b>{r['wpa']:+.3f}</b>)<br>"
        f"⚡ Apalancamiento (LI): <b>{r['li']:.2f}x</b>"
        for _, r in df_plot.iterrows()
    ]

    fig.add_trace(go.Scatter(
        x=df_plot['play_number'],
        y=df_plot['wp_after'],
        mode='lines',
        name='Win Probability (Leones)',
        line=dict(color=LEONES_GOLD, width=3.5),
        hovertext=custom_text,
        hoverinfo='text'
    ))

    # Jugadas de alto impacto positivo
    top_pos = df_wpa[df_wpa['wpa'] >= 0.08]
    if not top_pos.empty:
        fig.add_trace(go.Scatter(
            x=top_pos['atbat_index'] + 1,
            y=top_pos['wp_after'],
            mode='markers',
            marker=dict(color='#28a745', size=11, symbol='triangle-up', line=dict(color='white', width=1.5)),
            name='Impacto Positivo (+WPA)',
            hoverinfo='skip'
        ))

    # Jugadas de alto impacto negativo
    top_neg = df_wpa[df_wpa['wpa'] <= -0.08]
    if not top_neg.empty:
        fig.add_trace(go.Scatter(
            x=top_neg['atbat_index'] + 1,
            y=top_neg['wp_after'],
            mode='markers',
            marker=dict(color='#dc3545', size=11, symbol='triangle-down', line=dict(color='white', width=1.5)),
            name='Impacto Negativo (-WPA)',
            hoverinfo='skip'
        ))

    final_wp = df_plot.iloc[-1]['wp_after']
    res_str = "VICTORIA LEONES" if final_wp >= 0.5 else "DERROTA LEONES"
    res_color = "#28a745" if final_wp >= 0.5 else "#dc3545"

    fig.update_layout(
        title=dict(
            text=f"<b>Curva de Probabilidad de Victoria (Win Probability)</b><br><sub>{game_info.get('matchup', '')}</sub>",
            font=dict(size=16)
        ),
        xaxis_title="Secuencia de Jugadas (Play-by-Play)",
        yaxis_title="Probabilidad de Ganar (Leones)",
        yaxis=dict(
            tickformat='.0%',
            range=[-0.02, 1.02],
            tickvals=[0, 0.25, 0.5, 0.75, 1.0],
            gridcolor='rgba(200, 200, 200, 0.2)'
        ),
        xaxis=dict(gridcolor='rgba(200, 200, 200, 0.2)'),
        height=480,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode='closest',
        annotations=[
            dict(
                x=0.98, y=0.95,
                xref='paper', yref='paper',
                text=f"<b>{res_str}</b>",
                showarrow=False,
                font=dict(size=13, color=res_color),
                bgcolor='rgba(255, 255, 255, 0.9)',
                bordercolor=res_color,
                borderwidth=2,
                borderpad=4
            )
        ]
    )
    return fig


def create_wpa_by_inning_chart(df_wpa: pd.DataFrame) -> go.Figure:
    """Crea gráfico de WPA acumulado por inning"""
    wpa_by_inn = df_wpa.groupby('inning')['wpa'].sum().reset_index()
    colors = [LEONES_GOLD if x > 0 else LEONES_RED for x in wpa_by_inn['wpa']]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=wpa_by_inn['inning'],
        y=wpa_by_inn['wpa'],
        marker_color=colors,
        text=wpa_by_inn['wpa'].apply(lambda x: f"{x:+.3f}"),
        textposition='outside',
        textfont=dict(size=11),
        hovertemplate='Inning %{x}<br>WPA Neto: <b>%{y:+.3f}</b><extra></extra>'
    ))
    fig.add_hline(y=0, line_dash="solid", line_color="gray", line_width=1)
    fig.update_layout(
        title="<b>WPA Neto Acumulado por Inning</b>",
        xaxis_title="Inning",
        yaxis_title="WPA Neto",
        height=350,
        showlegend=False,
        xaxis=dict(tickmode='linear', tick0=1, dtick=1)
    )
    return fig


def create_leverage_by_inning_chart(df_wpa: pd.DataFrame) -> go.Figure:
    """Crea gráfico de Leverage Index promedio por Inning"""
    li_by_inn = df_wpa.groupby('inning')['li'].mean().reset_index()
    colors = ['#dc3545' if x >= 1.5 else ('#ffc107' if x >= 0.85 else '#17a2b8') for x in li_by_inn['li']]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=li_by_inn['inning'],
        y=li_by_inn['li'],
        marker_color=colors,
        text=li_by_inn['li'].apply(lambda x: f"{x:.2f}x"),
        textposition='outside',
        textfont=dict(size=11),
        hovertemplate='Inning %{x}<br>Apalancamiento Promedio: <b>%{y:.2f}x</b><extra></extra>'
    ))
    fig.add_hline(y=1.0, line_dash="dash", line_color="black", line_width=1.5, annotation_text="Promedio Liga (1.0x)")
    fig.update_layout(
        title="<b>Nivel de Tensión / Apalancamiento (LI) por Inning</b>",
        xaxis_title="Inning",
        yaxis_title="Leverage Index (LI)",
        height=350,
        showlegend=False,
        xaxis=dict(tickmode='linear', tick0=1, dtick=1)
    )
    return fig


def create_heroes_villains_chart(wpa_total: pd.DataFrame) -> go.Figure:
    """Crea gráfico de barras horizontal de Héroes y Villanos WPA"""
    if wpa_total.empty:
        return go.Figure()

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
        text=top_players['WPA_total'].apply(lambda x: f"{x:+.3f}"),
        textposition='outside',
        textfont=dict(size=11),
        hovertemplate='<b>%{y}</b><br>WPA Total: <b>%{x:+.3f}</b><extra></extra>'
    ))
    fig.add_vline(x=0, line_dash="solid", line_color="black", line_width=1)
    x_max = max(abs(top_players['WPA_total'].max()), abs(top_players['WPA_total'].min()), 0.1) * 1.35

    fig.update_layout(
        title="<b>Héroes y Villanos del Juego (WPA Total)</b>",
        xaxis_title="WPA Total Aportado",
        yaxis_title="",
        height=400,
        showlegend=False,
        xaxis=dict(range=[-x_max, x_max])
    )
    return fig


# ========================================
# PÁGINA PRINCIPAL
# ========================================

col_h_logo, col_h_txt = st.columns([1, 8])
with col_h_logo:
    st.image(get_brand_logo(), width=75)
with col_h_txt:
    st.title("📈 Análisis WPA & Sabermetría de Apalancamiento")
    st.markdown("### Leones del Caracas — Métricas de Probabilidad de Victoria (Win Expectancy)")

# Selector de modo principal
modo_vista = st.radio(
    "Selecciona la perspectiva de análisis:",
    ["🏟️ Análisis Juego a Juego", "🏆 Líderes de Temporada (Clutch & Impacto)"],
    horizontal=True
)

st.markdown("---")

current_season = get_current_season()
available_seasons = get_available_seasons() or [current_season]
season_options = {f"{s}-{s+1}": s for s in available_seasons}
current_display = f"{current_season}-{current_season+1}"

with st.sidebar:
    st.image(get_brand_logo(), width=200)
    st.markdown("---")
    
    selected_season_display = st.selectbox(
        "Temporada",
        options=list(season_options.keys()),
        index=list(season_options.keys()).index(current_display) if current_display in season_options else 0
    )
    selected_season = season_options[selected_season_display]
    
    st.markdown("---")
    with st.expander("ℹ️ Glosario Sabermétrico WPA & LI"):
        st.markdown("""
        * **Win Expectancy (WE):** Probabilidad instantánea de ganar según los 24 estados de base-out, marcador e inning.
        * **WPA (Win Probability Added):** Cuánto aumentó (+) o disminuyó (-) la probabilidad de ganar tras una jugada.
        * **LI (Leverage Index):** Nivel de tensión y dramatismo de la situación ($1.0 = \text{Promedio}$, $>1.5 = \text{Alta Presión}$).
        * **WPA/LI:** Contribución libre de contexto situacional.
        * **Clutch:** Medida de oportunismo ($WPA - WPA/LI$). Valores positivos indican rendimiento superior bajo máxima presión.
        """)

# ==============================================================================
# MODO 1: ANÁLISIS JUEGO A JUEGO
# ==============================================================================
if modo_vista == "🏟️ Análisis Juego a Juego":
    df_games = get_leones_games_from_supabase(selected_season)
    if df_games.empty:
        st.warning(f"No hay juegos finalizados registrados para la temporada {selected_season_display}")
        st.stop()

    game_options = []
    for _, game in df_games.iterrows():
        try:
            fecha = pd.to_datetime(game['game_date']).strftime('%d/%m/%Y')
        except:
            fecha = str(game.get('game_date', 'N/A'))[:10]

        is_home = (game['home_team_id'] == TEAM_ID)
        rival_id = game['away_team_id'] if is_home else game['home_team_id']
        rival_name = TEAM_NAMES.get(rival_id, f"Equipo {rival_id}")
        
        leo_score = game.get('home_score', 0) if is_home else game.get('away_score', 0)
        opp_score = game.get('away_score', 0) if is_home else game.get('home_score', 0)
        result = "V" if leo_score > opp_score else "D"
        result_emoji = "✅" if result == "V" else "❌"
        
        matchup_label = f"vs {rival_name}" if is_home else f"@ {rival_name}"
        score_str = f"{leo_score}-{opp_score}"

        game_options.append({
            'id': game['id'],
            'display': f"{fecha} | {matchup_label} | {score_str} {result_emoji}",
            'matchup': f"{fecha} — Leones {matchup_label} ({score_str})",
            'is_home': is_home,
            'rival_id': rival_id,
            'rival': rival_name
        })

    col1, col2 = st.columns([4, 1])
    with col1:
        selected_display = st.selectbox(
            "Seleccionar Partido:",
            options=[g['display'] for g in game_options],
            index=0
        )
    selected_game = next((g for g in game_options if g['display'] == selected_display), None)
    
    if selected_game:
        game_pk = selected_game['id']
        with st.spinner("Procesando matriz estocástica de Win Expectancy..."):
            df_wpa, is_home_leo, err = process_game_wpa_advanced(game_pk)
            
        if err or df_wpa.empty:
            st.error(f"Error cargando jugadas del partido: {err}")
            st.stop()
            
        wpa_players = calculate_player_game_wpa(df_wpa)
        
        # Tarjeta de Marcador y KPIs con Logos
        final_leones = df_wpa.iloc[-1]['leones_score_after']
        final_opp = df_wpa.iloc[-1]['opp_score_after']
        won = (final_leones > final_opp)
        
        home_tid = TEAM_ID if selected_game['is_home'] else selected_game['rival_id']
        away_tid = selected_game['rival_id'] if selected_game['is_home'] else TEAM_ID
        home_name = "Leones del Caracas" if selected_game['is_home'] else selected_game['rival']
        away_name = selected_game['rival'] if selected_game['is_home'] else "Leones del Caracas"
        home_score = final_leones if selected_game['is_home'] else final_opp
        away_score = final_opp if selected_game['is_home'] else final_leones
        
        bg_card = 'linear-gradient(135deg, #0A2342 0%, #15457C 100%)' if won else 'linear-gradient(135deg, #440C0C 0%, #8E2020 100%)'
        
        st.markdown(f"""
        <div style='background: {bg_card}; padding: 1.2rem; border-radius: 1rem; color: white; margin-top: 1rem; margin-bottom: 1rem;'>
            <div style='display: flex; align-items: center; justify-content: space-around;'>
                <div style='text-align: center; width: 35%;'>
                    <img src='{get_team_logo(home_tid, size=144)}' width='60' style='vertical-align: middle; margin-bottom: 4px;'><br>
                    <span style='font-weight: bold; font-size: 1.05rem;'>{home_name}</span>
                </div>
                <div style='text-align: center; width: 30%;'>
                    <span style='font-size: 2.2rem; font-weight: 800; letter-spacing: 2px;'>{home_score} - {away_score}</span><br>
                    <span style='background: {'#10b981' if won else '#ef4444'}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: bold;'>{'VICTORIA LEONES' if won else 'DERROTA LEONES'}</span>
                </div>
                <div style='text-align: center; width: 35%;'>
                    <img src='{get_team_logo(away_tid, size=144)}' width='60' style='vertical-align: middle; margin-bottom: 4px;'><br>
                    <span style='font-weight: bold; font-size: 1.05rem;'>{away_name}</span>
                </div>
            </div>
            <p style='text-align: center; margin-top: 0.8rem; margin-bottom: 0; font-size: 0.85rem; opacity: 0.85;'>
                📅 {selected_game['matchup']}
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
        with kpi1:
            st.metric("Resultado Final", "VICTORIA ✅" if won else "DERROTA ❌", f"{final_leones} - {final_opp}")
        with kpi2:
            st.metric("WP Máximo", f"{df_wpa['wp_after'].max():.1%}")
        with kpi3:
            st.metric("WP Mínimo", f"{df_wpa['wp_after'].min():.1%}")
        with kpi4:
            high_li_count = int((df_wpa['li'] >= 1.5).sum())
            st.metric("Jugadas High-LI (≥1.5x)", f"{high_li_count}", f"de {len(df_wpa)} jugadas")
        with kpi5:
            if not wpa_players.empty:
                mvp_p = wpa_players.iloc[0]
                st.metric("MVP del Juego", mvp_p['player'][:16], f"WPA: {mvp_p['WPA_total']:+.3f}")

        st.markdown("---")
        
        # Tabs de Juego
        t1, t2, t3, t4 = st.tabs([
            "📈 Evolución Win Probability",
            "📊 Por Inning & Apalancamiento",
            "🦸 Héroes & Villanos (WPA & Clutch)",
            "📋 Registro Completo de Jugadas"
        ])
        
        with t1:
            fig_wp = create_wp_evolution_chart(df_wpa, selected_game)
            st.plotly_chart(fig_wp, use_container_width=True)
            
            c_pos, c_neg = st.columns(2)
            with c_pos:
                st.markdown("#### 🔥 Momentos Más Valiosos (+WPA)")
                top_pos_plays = df_wpa.nlargest(5, 'wpa')[['inning', 'halfInning', 'outs_before', 'base_icons', 'batter', 'eventType', 'wpa', 'li']].copy()
                top_pos_plays['halfInning'] = top_pos_plays['halfInning'].map({'top': '▲', 'bottom': '▼'})
                top_pos_plays['wpa'] = top_pos_plays['wpa'].apply(lambda x: f"+{x:.3f}")
                top_pos_plays['li'] = top_pos_plays['li'].apply(lambda x: f"{x:.2f}x")
                top_pos_plays.columns = ['Inn', '', 'Outs', 'Bases', 'Bateador', 'Evento', 'WPA', 'LI']
                st.dataframe(top_pos_plays, use_container_width=True, hide_index=True)
                
            with c_neg:
                st.markdown("#### 💔 Momentos Más Costosos (-WPA)")
                top_neg_plays = df_wpa.nsmallest(5, 'wpa')[['inning', 'halfInning', 'outs_before', 'base_icons', 'batter', 'eventType', 'wpa', 'li']].copy()
                top_neg_plays['halfInning'] = top_neg_plays['halfInning'].map({'top': '▲', 'bottom': '▼'})
                top_neg_plays['wpa'] = top_neg_plays['wpa'].apply(lambda x: f"{x:.3f}")
                top_neg_plays['li'] = top_neg_plays['li'].apply(lambda x: f"{x:.2f}x")
                top_neg_plays.columns = ['Inn', '', 'Outs', 'Bases', 'Bateador', 'Evento', 'WPA', 'LI']
                st.dataframe(top_neg_plays, use_container_width=True, hide_index=True)

        with t2:
            ci1, ci2 = st.columns(2)
            with ci1:
                fig_inn_wpa = create_wpa_by_inning_chart(df_wpa)
                st.plotly_chart(fig_inn_wpa, use_container_width=True)
            with ci2:
                fig_inn_li = create_leverage_by_inning_chart(df_wpa)
                st.plotly_chart(fig_inn_li, use_container_width=True)

        with t3:
            if not wpa_players.empty:
                ch1, ch2 = st.columns([2, 1])
                with ch1:
                    fig_hv = create_heroes_villains_chart(wpa_players)
                    st.plotly_chart(fig_hv, use_container_width=True)
                with ch2:
                    st.markdown("#### 🌟 Desempeño Destacado")
                    mvp = wpa_players.iloc[0]
                    st.success(f"**MVP:** {mvp['player']}\n\n* **WPA Total:** `{mvp['WPA_total']:+.3f}`\n* **Clutch:** `{mvp['Clutch']:+.3f}`")
                    
                    if wpa_players['WPA_total'].min() < -0.05:
                        lvp = wpa_players.iloc[-1]
                        st.error(f"**LVP:** {lvp['player']}\n\n* **WPA Total:** `{lvp['WPA_total']:+.3f}`\n* **Clutch:** `{lvp['Clutch']:+.3f}`")
                
                st.markdown("#### 📋 Matriz de Impacto por Jugador (Leones)")
                tbl_disp = wpa_players[['player', 'wpa_bat', 'wpa_pit', 'WPA_total', 'WPA_LI_total', 'Clutch']].copy()
                tbl_disp['wpa_bat'] = tbl_disp['wpa_bat'].apply(lambda x: f"{x:+.3f}" if abs(x) > 0.0001 else "-")
                tbl_disp['wpa_pit'] = tbl_disp['wpa_pit'].apply(lambda x: f"{x:+.3f}" if abs(x) > 0.0001 else "-")
                tbl_disp['WPA_total'] = tbl_disp['WPA_total'].apply(lambda x: f"{x:+.3f}")
                tbl_disp['WPA_LI_total'] = tbl_disp['WPA_LI_total'].apply(lambda x: f"{x:+.3f}")
                tbl_disp['Clutch'] = tbl_disp['Clutch'].apply(lambda x: f"{x:+.3f}")
                tbl_disp.columns = ['Jugador', 'WPA Bateo', 'WPA Pitcheo', 'WPA Total', 'WPA/LI', 'Clutch']
                st.dataframe(tbl_disp, use_container_width=True, hide_index=True)

        with t4:
            st.markdown("#### 📋 Registro Detallado de Jugadas")
            f_col1, f_col2, f_col3 = st.columns(3)
            with f_col1:
                inn_filter = st.multiselect("Filtrar por Inning:", options=sorted(df_wpa['inning'].unique()), default=[])
            with f_col2:
                li_filter = st.selectbox("Nivel de Apalancamiento (LI):", ["Todos", "🔥 Alto (LI ≥ 1.5x)", "⚡ Medio (0.8x - 1.5x)", "❄️ Bajo (< 0.8x)"])
            with f_col3:
                evt_filter = st.multiselect("Tipo de Evento:", options=sorted(df_wpa['eventType'].unique()), default=[])
                
            df_filtered = df_wpa.copy()
            if inn_filter:
                df_filtered = df_filtered[df_filtered['inning'].isin(inn_filter)]
            if li_filter == "🔥 Alto (LI ≥ 1.5x)":
                df_filtered = df_filtered[df_filtered['li'] >= 1.5]
            elif li_filter == "⚡ Medio (0.8x - 1.5x)":
                df_filtered = df_filtered[(df_filtered['li'] >= 0.8) & (df_filtered['li'] < 1.5)]
            elif li_filter == "❄️ Bajo (< 0.8x)":
                df_filtered = df_filtered[df_filtered['li'] < 0.8]
            if evt_filter:
                df_filtered = df_filtered[df_filtered['eventType'].isin(evt_filter)]
                
            tbl_all = df_filtered[['inning', 'halfInning', 'outs_before', 'base_icons', 'score_str', 'batter', 'pitcher', 'eventType', 'wpa', 'li', 'wp_after']].copy()
            tbl_all['halfInning'] = tbl_all['halfInning'].map({'top': '▲', 'bottom': '▼'})
            tbl_all['wpa'] = tbl_all['wpa'].apply(lambda x: f"{x:+.3f}")
            tbl_all['li'] = tbl_all['li'].apply(lambda x: f"{x:.2f}x")
            tbl_all['wp_after'] = tbl_all['wp_after'].apply(lambda x: f"{x:.1%}")
            tbl_all.columns = ['Inn', '', 'Outs', 'Bases', 'Marcador', 'Bateador', 'Lanzador', 'Evento', 'WPA', 'LI', 'WP Leones']
            st.dataframe(tbl_all, use_container_width=True, hide_index=True, height=450)
            st.caption(f"Mostrando {len(tbl_all)} de {len(df_wpa)} jugadas.")

# ==============================================================================
# MODO 2: LÍDERES DE LA TEMPORADA
# ==============================================================================
else:
    st.markdown(f"### 🏆 Líderes de Temporada — Win Probability Added & Clutch ({selected_season_display})")
    
    with st.spinner("Compilando métricas acumuladas de la temporada..."):
        season_data = get_season_wpa_leaderboard(selected_season)
        
    if not season_data:
        st.warning(f"No se pudieron compilar datos acumulados para la temporada {selected_season_display}")
        st.stop()
        
    batters_df = season_data.get("batters", pd.DataFrame())
    pitchers_df = season_data.get("pitchers", pd.DataFrame())
    top_pos_plays = season_data.get("top_positive_plays", pd.DataFrame())
    top_neg_plays = season_data.get("top_negative_plays", pd.DataFrame())
    
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Juegos Analizados", f"{season_data.get('total_games', 0)} JJ")
    with k2:
        st.metric("Jugadas Procesadas", f"{season_data.get('total_plays', 0):,}")
    with k3:
        if not batters_df.empty:
            b_leader = batters_df.iloc[0]
            st.metric("Líder WPA Bateo", b_leader['batter'][:15], f"+{b_leader['WPA']:.2f} WPA")
    with k4:
        if not pitchers_df.empty:
            p_leader = pitchers_df.iloc[0]
            st.metric("Líder WPA Pitcheo", p_leader['pitcher'][:15], f"+{p_leader['WPA']:.2f} WPA")
            
    st.markdown("---")
    
    st_tab1, st_tab2, st_tab3 = st.tabs([
        "🏏 Bateadores (WPA & Clutch)",
        "🎯 Lanzadores (WPA & Apalancamiento)",
        "⚡ Top 10 Momentos Clave del Año"
    ])
    
    with st_tab1:
        st.markdown("#### 🏏 Ranking de Bateadores por Win Probability Added (WPA)")
        if not batters_df.empty:
            b_disp = batters_df.head(20).copy()
            b_disp['WPA'] = b_disp['WPA'].apply(lambda x: f"{x:+.3f}")
            b_disp['WPA_LI'] = b_disp['WPA_LI'].apply(lambda x: f"{x:+.3f}")
            b_disp['Clutch'] = b_disp['Clutch'].apply(lambda x: f"{x:+.3f}")
            b_disp['LI_avg'] = b_disp['LI_avg'].apply(lambda x: f"{x:.2f}x")
            b_disp.columns = ['ID', 'Bateador', 'JJ', 'Turnos (PA)', 'WPA Acumulado', 'WPA/LI', 'LI Promedio', 'Turnos High-LI (≥1.5x)', 'Clutch']
            st.dataframe(b_disp[['Bateador', 'JJ', 'Turnos (PA)', 'WPA Acumulado', 'WPA/LI', 'LI Promedio', 'Turnos High-LI (≥1.5x)', 'Clutch']], use_container_width=True, hide_index=True)
            
            # Gráfico de WPA de Bateo
            fig_bat = px.bar(
                batters_df.head(12),
                x='batter',
                y='WPA',
                title="<b>Top 12 Bateadores con Mayor WPA de la Temporada</b>",
                color='WPA',
                color_continuous_scale=[[0, LEONES_RED], [0.5, '#f5deb3'], [1, LEONES_GOLD]],
                labels={'batter': 'Bateador', 'WPA': 'WPA Total'}
            )
            fig_bat.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_bat, use_container_width=True)
        else:
            st.info("No hay datos de bateo disponibles.")
            
    with st_tab2:
        st.markdown("#### 🎯 Ranking de Lanzadores por Win Probability Added (WPA)")
        if not pitchers_df.empty:
            p_disp = pitchers_df.head(20).copy()
            p_disp['WPA'] = p_disp['WPA'].apply(lambda x: f"{x:+.3f}")
            p_disp['WPA_LI'] = p_disp['WPA_LI'].apply(lambda x: f"{x:+.3f}")
            p_disp['Clutch'] = p_disp['Clutch'].apply(lambda x: f"{x:+.3f}")
            p_disp['LI_avg'] = p_disp['LI_avg'].apply(lambda x: f"{x:.2f}x")
            p_disp.columns = ['ID', 'Lanzador', 'JJ', 'Bateadores Enfrentados (BF)', 'WPA Acumulado', 'WPA/LI', 'LI Promedio', 'Enfrentamientos High-LI', 'Clutch']
            st.dataframe(p_disp[['Lanzador', 'JJ', 'Bateadores Enfrentados (BF)', 'WPA Acumulado', 'WPA/LI', 'LI Promedio', 'Enfrentamientos High-LI', 'Clutch']], use_container_width=True, hide_index=True)
            
            # Gráfico de WPA de Pitcheo
            fig_pit = px.bar(
                pitchers_df.head(12),
                x='pitcher',
                y='WPA',
                title="<b>Top 12 Lanzadores con Mayor WPA de la Temporada</b>",
                color='WPA',
                color_continuous_scale=[[0, LEONES_RED], [0.5, '#f5deb3'], [1, '#28a745']],
                labels={'pitcher': 'Lanzador', 'WPA': 'WPA Total'}
            )
            fig_pit.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_pit, use_container_width=True)
        else:
            st.info("No hay datos de pitcheo disponibles.")

    with st_tab3:
        st.markdown("#### ⚡ Las 10 Jugadas Más Decisivas de Toda la Temporada")
        st.markdown("##### 🔥 Mayores Swings Positivos a Favor de Leones (+WPA)")
        if not top_pos_plays.empty:
            tp_disp = top_pos_plays[['game_date', 'inning', 'halfInning', 'score_str', 'batter', 'pitcher', 'eventType', 'description', 'wpa', 'li']].copy()
            tp_disp['game_date'] = pd.to_datetime(tp_disp['game_date']).dt.strftime('%d/%m/%Y')
            tp_disp['halfInning'] = tp_disp['halfInning'].map({'top': '▲', 'bottom': '▼'})
            tp_disp['wpa'] = tp_disp['wpa'].apply(lambda x: f"+{x:.3f}")
            tp_disp['li'] = tp_disp['li'].apply(lambda x: f"{x:.2f}x")
            tp_disp.columns = ['Fecha', 'Inn', '', 'Marcador', 'Bateador', 'Pitcher', 'Evento', 'Descripción', 'WPA', 'LI']
            st.dataframe(tp_disp, use_container_width=True, hide_index=True)
            
        st.markdown("##### 💔 Mayores Swings Negativos en Contra de Leones (-WPA)")
        if not top_neg_plays.empty:
            tn_disp = top_neg_plays[['game_date', 'inning', 'halfInning', 'score_str', 'batter', 'pitcher', 'eventType', 'description', 'wpa', 'li']].copy()
            tn_disp['game_date'] = pd.to_datetime(tn_disp['game_date']).dt.strftime('%d/%m/%Y')
            tn_disp['halfInning'] = tn_disp['halfInning'].map({'top': '▲', 'bottom': '▼'})
            tn_disp['wpa'] = tn_disp['wpa'].apply(lambda x: f"{x:.3f}")
            tn_disp['li'] = tn_disp['li'].apply(lambda x: f"{x:.2f}x")
            tn_disp.columns = ['Fecha', 'Inn', '', 'Marcador', 'Bateador', 'Pitcher', 'Evento', 'Descripción', 'WPA', 'LI']
            st.dataframe(tn_disp, use_container_width=True, hide_index=True)

# Glosario y Explicación Didáctica de WPA y Métricas Avanzadas
with st.expander("📖 Guía y Glosario: ¿Cómo entender WPA, Win Expectancy, Leverage Index y Clutch?", expanded=False):
    st.markdown(r"""
    ### 📈 La Revolución del WPA (Win Probability Added)
    A diferencia de las estadísticas tradicionales (que tratan un hit en el 1er inning perdiendo por 10 igual que un jonrón en el 9no para dejar en el terreno), **el WPA mide el impacto real de cada jugada en el destino final del partido**.

    | Métrica Sabermétrica | Nombre Completo | ¿Qué mide en lenguaje sencillo? | ¿Cómo interpretarla? |
    |---|---|---|---|
    | **WP (Win Probability)** | Probabilidad de Victoria | La probabilidad matemática (de 0% a 100%) de ganar el partido en este instante exacto, calculada según el inning, marcador, corredores en base y número de outs. | 50% = Juego empatado y equilibrado.<br>99% = Victoria casi sellada.<br>1% = Al borde de la derrota. |
    | **WPA** | Probabilidad de Victoria Añadida | La diferencia directa de probabilidad antes y después de una jugada: $\text{WPA} = WP_{\text{después}} - WP_{\text{antes}}$. | **Positivo (+):** Ayudó al equipo a ganar (ej. hit remolcador $= +0.25$ o $+25\%$ de chance de ganar).<br>**Negativo (-):** Perjudicó al equipo (ej. error o ponche con bases llenas $= -0.18$). |
    | **LI (Leverage Index)** | Índice de Apalancamiento / Presión | Cuánta tensión o dramatismo tiene el momento en comparación con un turno promedio. | **1.0x:** Tensión promedio estándar.<br>**> 1.5x:** Situación de alta presión (High Leverage).<br>**> 3.0x:** Momento crítico máximo (ej. bases llenas en la 9na con 2 outs y juego por 1 carrera).<br>**< 0.5x:** Juego decidido (baja presión). |
    | **WPA/LI** | WPA Ajustado por Contexto | El rendimiento puro del pelotero eliminando la suerte de haber jugado en situaciones de mucha o poca presión. | Mide la calidad intrínseca del jugador sin sesgo del momento en que el mánager lo usó. |
    | **Clutch Score** | Puntaje de Oportunismo / Frialdad | $WPA - (WPA / LI)$. Evalúa si el jugador rinde más cuando la presión es máxima. | **Positivo (+):** *Sangre fría.* Se crece bajo máxima presión.<br>**Negativo (-):** Rinde bien en juegos holgados, pero decae en momentos apretados. |
    | **RE24** | Matriz de Expectativa de Carreras | Modelo sabermétrico que calcula cuántas carreras anota en promedio un equipo según los 24 estados posibles (8 combinaciones de bases $\times$ 3 estados de outs). | Base matemática estocástica del motor de probabilidades. |
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #888; font-size: 0.85rem;'>
    <p>📈 <b>RepubliCaraquistApp — Suite Sabermétrica de Win Expectancy & WPA</b></p>
    <p>Modelo estocástico de 24 estados Base-Out (RE24) y Apalancamiento (Leverage Index) | Fuente: MLB Stats API</p>
</div>
""", unsafe_allow_html=True)

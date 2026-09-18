# pages/9_🔥_Pitching_Summary.py
"""
Pitching Summary & Telemetría Sabermétrica - RepubliCaraquistApp
---------------------------------------------------------------
Módulo avanzado de telemetría de lanzadores inspirado en Thomas Nestico (@TJStats).
Soporta:
1. Búsqueda universal (MLB/MiLB y todas las franquicias de la LVBP).
2. Arquitectura de doble rama:
   - MLB/MiLB: Telemetría Statcast completa (Velo, Spin, IVB, HB, Whiff%, CSW%, Zone%, xwOBA).
   - LVBP: Telemetría adaptada a Play-by-Play (Carga por entrada, Leverage Index Tango RE24, Platoon splits).
3. Tres modos temporales: Salida Individual, Temporada Completa y Rango de Fechas.
4. Generación y descarga de tarjetas panorámicas HD (2400x1350 px a 300 DPI) en Matplotlib.
"""

import os
import sys
import io
import datetime

# Asegurar path raíz en sys.path para compatibilidad absoluta en Streamlit Cloud
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from utils.pitching_engine import (
    search_pitchers,
    get_pitcher_by_id,
    get_pitcher_game_logs,
    get_game_pitch_data,
    get_pitcher_season_statcast_df,
    get_pitch_analysis_for_df,
    get_available_seasons as get_engine_seasons,
)
from utils.pitching_card import (
    build_pitching_summary_card,
    _get_pitch_color,
)
from utils.teams import get_brand_logo, LVBP_TEAMS, LVBP_ABBR, get_team_abbr

# Configuración de página
st.set_page_config(
    page_title="Pitching Summary & Telemetría - RepubliCaraquistApp",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inyectar estilos personalizados si están disponibles
try:
    from utils.styles import inject_custom_css
    inject_custom_css()
except Exception:
    pass

# Estilos CSS específicos para la vista de pitcheo
st.markdown("""
<style>
div[data-testid="stMetricValue"] {
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    color: #FDB827 !important;
}
div[data-testid="stMetricLabel"] {
    font-size: 0.8rem !important;
    color: #94A3B8 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}
.pitcher-badge {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 700;
    margin-right: 0.5rem;
}
.badge-caracas {
    background: rgba(253, 184, 39, 0.2);
    border: 1px solid #FDB827;
    color: #FDB827;
}
.badge-lvbp {
    background: rgba(59, 130, 246, 0.2);
    border: 1px solid #3B82F6;
    color: #93C5FD;
}
.badge-mlb {
    background: rgba(239, 68, 68, 0.2);
    border: 1px solid #EF4444;
    color: #FCA5A5;
}
</style>
""", unsafe_allow_html=True)


# ── 1. Inicialización de Estado Reactivo ────────────────────────────────────────

if "selected_pitcher" not in st.session_state:
    st.session_state["selected_pitcher"] = None
if "active_branch" not in st.session_state:
    st.session_state["active_branch"] = "lvbp"
if "pitcher_season" not in st.session_state:
    st.session_state["pitcher_season"] = 2025
if "time_mode" not in st.session_state:
    st.session_state["time_mode"] = "game"
if "selected_game_pk" not in st.session_state:
    st.session_state["selected_game_pk"] = None
if "range_dates" not in st.session_state:
    st.session_state["range_dates"] = (
        datetime.date(2024, 10, 1),
        datetime.date(2025, 1, 31)
    )

# Comprobar si viene un parámetro por URL (?pitcher_id=...) o session_state
query_pitcher_id = st.query_params.get("pitcher_id") or st.session_state.get("selected_pitcher_id")
if query_pitcher_id:
    try:
        pid_int = int(query_pitcher_id)
        curr = st.session_state.get("selected_pitcher")
        if not curr or curr.get("id") != pid_int:
            p_obj = get_pitcher_by_id(pid_int)
            if p_obj:
                st.session_state["selected_pitcher"] = p_obj
                st.session_state["active_branch"] = "lvbp" if p_obj.get("has_lvbp_history") else "mlb"
                if "selected_pitcher_id" in st.session_state:
                    del st.session_state["selected_pitcher_id"]
    except Exception:
        pass


# ── 2. Sidebar con Controles y Branding ────────────────────────────────────────

with st.sidebar:
    st.image(get_brand_logo(), width=180)
    st.markdown("---")
    st.subheader("⚙️ Control de Pitcheo")

    # Selector de Temporada
    available_seasons = [2025, 2024, 2023, 2022]
    sel_season = st.selectbox(
        "Temporada",
        available_seasons,
        index=available_seasons.index(st.session_state["pitcher_season"]) if st.session_state["pitcher_season"] in available_seasons else 0,
        key="sb_pitcher_season"
    )
    if sel_season != st.session_state["pitcher_season"]:
        st.session_state["pitcher_season"] = sel_season
        st.session_state["selected_game_pk"] = None
        st.rerun()

    # Botón para cambiar de lanzador
    if st.session_state["selected_pitcher"]:
        st.markdown("---")
        if st.button("🔍 Buscar Otro Lanzador", use_container_width=True):
            st.session_state["selected_pitcher"] = None
            st.session_state["selected_game_pk"] = None
            if "pitcher_id" in st.query_params:
                del st.query_params["pitcher_id"]
            st.rerun()

    st.markdown("---")
    st.markdown(
        """
        <div style='font-size:0.75rem; color:#64748B;'>
        <b>Metodología:</b><br>
        • Tarjetas HD inspiradas en Thomas Nestico (@TJStats).<br>
        • Telemetría MLB vía Statcast / Baseball Savant.<br>
        • Telemetría LVBP vía PBP, Tango RE24 & MLB Stats API.<br>
        • Autor: Jorge Leonardo Loreto • @republicaraquistapp
        </div>
        """,
        unsafe_allow_html=True
    )


# ── 3. Vista de Aterrizaje / Buscador (Si no hay lanzador activo) ───────────────

pitcher = st.session_state.get("selected_pitcher")

if not pitcher:
    col_t1, col_t2 = st.columns([1, 8])
    with col_t1:
        st.image(get_brand_logo(), width=75)
    with col_t2:
        st.title("🔥 Pitching Summary & Telemetría")
        st.markdown("**Centro de Analítica de Lanzadores — República Caraquista**")

    st.markdown("""
    Busca cualquier lanzador de la **LVBP (los 8 equipos)** o de **Grandes Ligas / Ligas Menores (MLB/MiLB)**
    para generar su desglose de pitcheo y su tarjeta gráfica oficial en alta resolución (300 DPI).
    """)

    # Barra de búsqueda
    search_q = st.text_input(
        "Buscar por nombre o ID numérico (MLB ID)",
        placeholder="Ej: Erick Leal, Ricardo Sánchez, Albert Suárez, 645307...",
        key="main_pitcher_search"
    )

    # Sugerencias rápidas de lanzadores populares
    st.markdown("##### ⚡ Accesos Rápidos Sugeridos:")
    chip_cols = st.columns(6)
    suggested = [
        ("🦁 Erick Leal", 612797),
        ("⚓ Ricardo Sánchez", 645307),
        ("🐦 Max Castillo", 666721),
        ("🦅 Albert Suárez", 544150),
        ("🦈 Junior Guerra", 448855),
        ("🦁 Jhoulys Chacín", 468504),
    ]
    for i, (label, p_id) in enumerate(suggested):
        with chip_cols[i]:
            if st.button(label, key=f"chip_{p_id}", use_container_width=True):
                found = get_pitcher_by_id(p_id)
                if found:
                    st.session_state["selected_pitcher"] = found
                    st.session_state["active_branch"] = "lvbp" if found.get("has_lvbp_history") else "mlb"
                    st.session_state["selected_game_pk"] = None
                    st.rerun()

    # Si el usuario escribió una búsqueda
    if search_q and len(search_q.strip()) >= 2:
        with st.spinner("Buscando lanzadores..."):
            results = search_pitchers(search_q.strip())

        if results:
            st.markdown(f"**Resultados encontrados ({len(results)}):**")
            for res_p in results:
                card_col1, card_col2, card_col3 = st.columns([1, 6, 2])
                with card_col1:
                    photo = res_p.get("photo_url") or "https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current/w_213,q_auto:best/v1/people/0/headshot/67/current"
                    st.image(photo, width=60)
                with card_col2:
                    p_name = res_p.get("name", "Lanzador")
                    t_name = res_p.get("team", "Equipo")
                    thr = res_p.get("throws", "R")
                    badges_html = ""
                    if res_p.get("has_caracas_history"):
                        badges_html += '<span class="pitcher-badge badge-caracas">🦁 Leones del Caracas</span>'
                    elif res_p.get("has_lvbp_history"):
                        abbr = res_p.get("lvbp_team_abbr") or "LVBP"
                        badges_html += f'<span class="pitcher-badge badge-lvbp">🇻🇪 {abbr}</span>'
                    if res_p.get("has_mlb_history"):
                        badges_html += '<span class="pitcher-badge badge-mlb">⚾ MLB</span>'

                    st.markdown(f"**{p_name}** {badges_html}", unsafe_allow_html=True)
                    st.caption(f"{t_name} • Lanza: {thr}HP • ID: {res_p.get('id')}")
                with card_col3:
                    if st.button("Ver Resumen", key=f"sel_{res_p.get('id')}", use_container_width=True):
                        st.session_state["selected_pitcher"] = res_p
                        st.session_state["active_branch"] = "lvbp" if res_p.get("has_lvbp_history") else "mlb"
                        st.session_state["selected_game_pk"] = None
                        st.rerun()
                st.markdown("---")
        else:
            st.warning("No se encontraron lanzadores con ese criterio.")

    st.stop()


# ── 4. Vista Activa: Lanzador Seleccionado ─────────────────────────────────────

p_id = pitcher.get("id")
p_name = pitcher.get("name", "Lanzador")
p_throws = pitcher.get("throws", "R")
has_lvbp = bool(pitcher.get("has_lvbp_history"))
has_caracas = bool(pitcher.get("has_caracas_history"))
lvbp_team_name = pitcher.get("lvbp_team_name") or ("Leones del Caracas" if has_caracas else "LVBP")
lvbp_team_abbr = pitcher.get("lvbp_team_abbr") or ("CAR" if has_caracas else "LVBP")

# Cabecera del perfil
col_head1, col_head2, col_head3 = st.columns([1, 6, 2])
with col_head1:
    photo = pitcher.get("photo_url") or "https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current/w_213,q_auto:best/v1/people/0/headshot/67/current"
    st.image(photo, width=95)

with col_head2:
    badge_tag = ""
    if has_caracas:
        badge_tag = '<span class="pitcher-badge badge-caracas">🦁 Leones del Caracas</span>'
    elif has_lvbp:
        badge_tag = f'<span class="pitcher-badge badge-lvbp">🇻🇪 LVBP • {lvbp_team_abbr}</span>'
    st.markdown(f"<h2 style='margin-bottom:0;'>{p_name} {badge_tag}</h2>", unsafe_allow_html=True)
    curr_team = pitcher.get("team") or lvbp_team_name
    st.markdown(f"<p style='color:#94A3B8; margin-top:0;'>{curr_team} • Lanza: <b>{p_throws}HP</b> • ID MLB: <b>{p_id}</b></p>", unsafe_allow_html=True)

with col_head3:
    if st.button("🔄 Cambiar Lanzador", use_container_width=True):
        st.session_state["selected_pitcher"] = None
        st.session_state["selected_game_pk"] = None
        if "pitcher_id" in st.query_params:
            del st.query_params["pitcher_id"]
        st.rerun()

st.markdown("---")

# ── 5. Selectores de Rama y Modo Temporal ─────────────────────────────────────

col_ctrl1, col_ctrl2 = st.columns([1, 1])

with col_ctrl1:
    branch_opts = []
    if has_lvbp:
        lvbp_lbl = "🦁 Leones del Caracas (LVBP)" if has_caracas else f"🇻🇪 {lvbp_team_name} (LVBP)"
        branch_opts.append(lvbp_lbl)
    branch_opts.append("⚾ MLB / MiLB (Statcast)")

    curr_b_idx = 0 if st.session_state["active_branch"] == "lvbp" and has_lvbp else (len(branch_opts) - 1)
    sel_branch_str = st.radio(
        "Rama Analítica",
        branch_opts,
        index=curr_b_idx,
        horizontal=True,
        key="rb_branch"
    )
    new_b = "lvbp" if "LVBP" in sel_branch_str else "mlb"
    if new_b != st.session_state["active_branch"]:
        st.session_state["active_branch"] = new_b
        st.session_state["selected_game_pk"] = None
        st.rerun()

with col_ctrl2:
    time_modes = [
        ("🎯 Salida Individual", "game"),
        ("📅 Temporada Completa", "season"),
        ("📆 Rango de Fechas", "range"),
    ]
    curr_m_idx = [m[1] for m in time_modes].index(st.session_state["time_mode"])
    sel_mode_tuple = st.radio(
        "Modo Temporal",
        time_modes,
        index=curr_m_idx,
        format_func=lambda x: x[0],
        horizontal=True,
        key="rb_time_mode"
    )
    if sel_mode_tuple[1] != st.session_state["time_mode"]:
        st.session_state["time_mode"] = sel_mode_tuple[1]
        st.rerun()

active_branch = st.session_state["active_branch"]
time_mode = st.session_state["time_mode"]
season_int = st.session_state["pitcher_season"]


# ── 6. Carga de Salidas e Historial ───────────────────────────────────────────

with st.spinner("Cargando historial de salidas..."):
    game_logs = get_pitcher_game_logs(
        p_id,
        season=season_int,
        is_lvbp=(active_branch == "lvbp")
    )

    # Fallback automático de temporada si la actual no tiene salidas
    if not game_logs:
        for fallback_s in [2025, 2024, 2023, 2022]:
            if fallback_s != season_int:
                test_logs = get_pitcher_game_logs(p_id, season=fallback_s, is_lvbp=(active_branch == "lvbp"))
                if test_logs:
                    season_int = fallback_s
                    st.session_state["pitcher_season"] = fallback_s
                    game_logs = test_logs
                    break

# Selector de juego o rango según el modo
selected_game_summary = {}
if time_mode == "game":
    if game_logs:
        opts_dict = {
            f"{g.get('date', '')} vs {g.get('opponent', '')} ({g.get('ip', 0)} IP, {g.get('so', 0)} K)": g
            for g in game_logs
        }
        labels = list(opts_dict.keys())
        selected_label = st.selectbox("Seleccionar Salida", labels, key="sb_game_select")
        selected_game_summary = opts_dict[selected_label]
        st.session_state["selected_game_pk"] = selected_game_summary.get("game_pk")
    else:
        st.warning(f"No se encontraron salidas registradas en la temporada {season_int} para este lanzador.")
elif time_mode == "range":
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        start_d = st.date_input("Fecha Inicial", value=st.session_state["range_dates"][0])
    with col_d2:
        end_d = st.date_input("Fecha Final", value=st.session_state["range_dates"][1])
    st.session_state["range_dates"] = (start_d, end_d)


# ── 7. Computación de Datos Analíticos ─────────────────────────────────────────

pitch_analysis = {}
df_statcast_season = pd.DataFrame()
current_game_pk = st.session_state.get("selected_game_pk")

if time_mode == "game" and current_game_pk:
    with st.spinner("Procesando datos del juego..."):
        pitch_analysis = get_game_pitch_data(
            current_game_pk,
            p_id,
            is_lvbp=(active_branch == "lvbp")
        )
elif time_mode in ("season", "range"):
    with st.spinner("Agregando métricas del período..."):
        if active_branch == "mlb":
            df_statcast_season = get_pitcher_season_statcast_df(p_id, season=season_int)
            if time_mode == "range" and not df_statcast_season.empty and "game_date" in df_statcast_season.columns:
                s_str = str(st.session_state["range_dates"][0])
                e_str = str(st.session_state["range_dates"][1])
                df_statcast_season = df_statcast_season[
                    (df_statcast_season["game_date"] >= s_str) & (df_statcast_season["game_date"] <= e_str)
                ]
            pitch_analysis = get_pitch_analysis_for_df(df_statcast_season)


# ── 8. Barra de KPIs Superiores ───────────────────────────────────────────────

def _outs_from_ip(ip_val) -> int:
    try:
        s = str(ip_val).strip()
        if '.' in s:
            p = s.split('.')
            return int(p[0]) * 3 + int(p[1])
        return int(float(s)) * 3
    except Exception:
        return 0

kpi_cols = st.columns(9)

if time_mode == "game":
    g = selected_game_summary
    k = pitch_analysis.get("pbp_kpis", {})
    tot_p = g.get("pitches") or pitch_analysis.get("total_pitches") or 0
    with kpi_cols[0]: st.metric("IP", str(g.get("ip", "0.0")))
    with kpi_cols[1]: st.metric("H", str(g.get("h", 0)))
    with kpi_cols[2]: st.metric("R", str(g.get("r", 0)))
    with kpi_cols[3]: st.metric("ER", str(g.get("er", 0)))
    with kpi_cols[4]: st.metric("BB", str(g.get("bb", 0)))
    with kpi_cols[5]: st.metric("K", str(g.get("so", 0)))
    with kpi_cols[6]: st.metric("Pitcheos", str(tot_p))
    with kpi_cols[7]: st.metric("CSW %", str(k.get("csw_pct", "—")))
    with kpi_cols[8]: st.metric("Whiff %", str(k.get("whiff_pct", "—")))
else:
    # Modo season o range
    logs = list(game_logs or [])
    if time_mode == "range":
        s_str = str(st.session_state["range_dates"][0])
        e_str = str(st.session_state["range_dates"][1])
        logs = [g for g in logs if s_str <= str(g.get("date", "")) <= e_str]

    if logs:
        tot_outs = sum(_outs_from_ip(g.get("ip", "0.0")) for g in logs)
        tot_ip_str = f"{tot_outs // 3}.{tot_outs % 3}"
        float_ip = tot_outs / 3.0
        tot_h = sum(int(g.get("h") or 0) for g in logs)
        tot_r = sum(int(g.get("r") or 0) for g in logs)
        tot_er = sum(int(g.get("er") or 0) for g in logs)
        tot_bb = sum(int(g.get("bb") or 0) for g in logs)
        tot_so = sum(int(g.get("so") or 0) for g in logs)
        tot_pitches = sum(int(g.get("pitches") or 0) for g in logs)
        calc_era = (tot_er * 9.0 / float_ip) if float_ip > 0 else 0.0
        calc_whip = ((tot_bb + tot_h) / float_ip) if float_ip > 0 else 0.0

        with kpi_cols[0]: st.metric("IP Total", tot_ip_str)
        with kpi_cols[1]: st.metric("H Total", str(tot_h))
        with kpi_cols[2]: st.metric("R Total", str(tot_r))
        with kpi_cols[3]: st.metric("ER Total", str(tot_er))
        with kpi_cols[4]: st.metric("BB Total", str(tot_bb))
        with kpi_cols[5]: st.metric("K Total", str(tot_so))
        with kpi_cols[6]: st.metric("Pitcheos", str(tot_pitches))
        with kpi_cols[7]: st.metric("ERA Período", f"{calc_era:.2f}")
        with kpi_cols[8]: st.metric("WHIP Período", f"{calc_whip:.2f}")
    else:
        for c in kpi_cols:
            with c: st.metric("—", "0")

st.markdown("---")


# ── 9. Gráficos y Telemetría Interactiva en Plotly ────────────────────────────

def _plotly_dark_layout(title: str) -> dict:
    return dict(
        title=dict(text=title, font=dict(color="#F8FAFC", size=14, family="Inter, sans-serif")),
        paper_bgcolor="#070B19",
        plot_bgcolor="#0D152B",
        font=dict(color="#94A3B8", family="Inter, sans-serif"),
        margin=dict(l=40, r=20, t=45, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

tab_graphs, tab_card = st.tabs(["📊 Telemetría & Gráficos Interactivos", "🖼️ Tarjeta HD Oficial (Thomas Nestico)"])

with tab_graphs:
    has_statcast = pitch_analysis.get("has_statcast", False) and active_branch == "mlb"

    if has_statcast:
        # Rama MLB con Statcast
        st.markdown("#### 🎯 Repertorio y Perfil de Lanzamientos (Statcast)")
        sc_table = pitch_analysis.get("statcast_table", [])
        if sc_table:
            df_sc_display = pd.DataFrame(sc_table)
            st.dataframe(df_sc_display, use_container_width=True, hide_index=True)

        col_g1, col_g2 = st.columns(2)
        pitches = pitch_analysis.get("pitches", [])

        with col_g1:
            # Gráfico cartesiano de quiebre (IVB vs HB)
            fig_mov = go.Figure()
            by_type = {}
            for p in pitches:
                if p.get("hb") is not None and p.get("ivb") is not None:
                    by_type.setdefault(p.get("pitch_name", "Desconocido"), []).append(p)

            for pt, plist in by_type.items():
                rgb = _get_pitch_color(pt)
                fig_mov.add_trace(go.Scatter(
                    x=[p["hb"] for p in plist],
                    y=[p["ivb"] for p in plist],
                    mode="markers",
                    name=pt,
                    marker=dict(size=8, color=f"rgb({rgb[0]},{rgb[1]},{rgb[2]})", opacity=0.85),
                    text=[f"{pt}<br>Velo: {p.get('speed')} mph<br>IVB: {p.get('ivb')}\"<br>HB: {p.get('hb')}\"" for p in plist],
                    hoverinfo="text",
                ))

            layout_mov = _plotly_dark_layout("Movimiento de Pitcheos (IVB vs HB en pulgadas)")
            layout_mov["xaxis"] = dict(title="Quiebre Horizontal (HB) [in]", range=[-25, 25], zeroline=True, zerolinecolor="rgba(253,184,39,0.3)")
            layout_mov["yaxis"] = dict(title="Quiebre Vertical Inducido (IVB) [in]", range=[-25, 25], zeroline=True, zerolinecolor="rgba(253,184,39,0.3)")
            fig_mov.update_layout(layout_mov)
            st.plotly_chart(fig_mov, use_container_width=True)

        with col_g2:
            # Gráfico de zona de strike
            fig_sz = go.Figure()
            for pt, plist in by_type.items():
                rgb = _get_pitch_color(pt)
                fig_sz.add_trace(go.Scatter(
                    x=[p.get("plate_x") for p in plist if p.get("plate_x") is not None],
                    y=[p.get("plate_z") for p in plist if p.get("plate_z") is not None],
                    mode="markers",
                    name=pt,
                    marker=dict(size=8, color=f"rgb({rgb[0]},{rgb[1]},{rgb[2]})", opacity=0.85),
                    text=[f"{pt}<br>Velo: {p.get('speed')} mph" for p in plist],
                    hoverinfo="text",
                ))
            layout_sz = _plotly_dark_layout("Localización en Zona de Strike")
            layout_sz["xaxis"] = dict(title="Coordenada X (ft) [Centro=0.0]", range=[-2.0, 2.0])
            layout_sz["yaxis"] = dict(title="Altura Z (ft)", range=[0.5, 4.5])
            layout_sz["shapes"] = [
                dict(type="rect", x0=-0.85, x1=0.85, y0=1.5, y1=3.5, line=dict(color="#3B82F6", width=2), fillcolor="rgba(59, 130, 246, 0.08)")
            ]
            fig_sz.update_layout(layout_sz)
            st.plotly_chart(fig_sz, use_container_width=True)

    else:
        # Rama LVBP (o modo sin Statcast)
        st.markdown("#### 🇻🇪 Desglose de Pitcheo y Carga de Trabajo (Play-by-Play)")
        workload = pitch_analysis.get("innings_workload", [])

        col_lv1, col_lv2 = st.columns(2)

        with col_lv1:
            # Gráfico de lanzamientos por entrada
            fig_work = go.Figure()
            if workload:
                inns = [f"Inn {w['inning']}" for w in workload]
                fig_work.add_trace(go.Bar(name="Strikes", x=inns, y=[w["strikes"] for w in workload], marker_color="#FDB827"))
                fig_work.add_trace(go.Bar(name="Bolas", x=inns, y=[w["pitches"] - w["strikes"] for w in workload], marker_color="rgba(80, 100, 140, 0.8)"))
                layout_work = _plotly_dark_layout("Lanzamientos por Entrada (Strikes vs Bolas)")
                layout_work["barmode"] = "stack"
                layout_work["yaxis"] = dict(title="Pitcheos")
                fig_work.update_layout(layout_work)
                st.plotly_chart(fig_work, use_container_width=True)
            else:
                st.info("No hay datos de lanzamientos por entrada disponibles.")

        with col_lv2:
            # Gráfico de Leverage Index (curva de apalancamiento)
            fig_li = go.Figure()
            if workload:
                inns = [f"Inn {w['inning']}" for w in workload]
                lis = [w.get("avg_li", 1.0) for w in workload]
                colors = ["#EF4444" if li >= 1.5 else ("#FDB827" if li >= 0.9 else "#3B82F6") for li in lis]
                fig_li.add_trace(go.Bar(name="Leverage Index", x=inns, y=lis, marker_color=colors, text=[f"{li:.2f}" for li in lis], textposition="auto"))
                layout_li = _plotly_dark_layout("Apalancamiento de Entrada (Leverage Index RE24)")
                layout_li["yaxis"] = dict(title="LI (1.0 = Promedio Liga)")
                layout_li["shapes"] = [
                    dict(type="line", x0=-0.5, x1=len(inns)-0.5, y0=1.0, y1=1.0, line=dict(color="rgba(255,255,255,0.4)", width=1, dash="dash")),
                    dict(type="line", x0=-0.5, x1=len(inns)-0.5, y0=1.5, y1=1.5, line=dict(color="rgba(239,68,68,0.6)", width=1.5, dash="dot")),
                ]
                fig_li.update_layout(layout_li)
                st.plotly_chart(fig_li, use_container_width=True)
            else:
                st.info("No hay datos de apalancamiento disponibles.")

    # Tabla de salidas registradas
    st.markdown("##### 📋 Historial de Salidas del Período:")
    if game_logs:
        df_logs_table = pd.DataFrame(game_logs)[["date", "opponent", "role", "decision", "ip", "h", "r", "er", "bb", "so", "pitches"]].copy()
        df_logs_table.columns = ["Fecha", "Rival", "Rol", "Decisión", "IP", "H", "C", "CL", "BB", "K", "Pitcheos"]
        st.dataframe(df_logs_table, use_container_width=True, hide_index=True)


# ── 10. Generación y Descarga de la Tarjeta Gráfica Oficial ────────────────────

with tab_card:
    st.markdown("### 🖼️ Tarjeta Panorámica Oficial de Pitcheo")
    st.caption("Resolución de exportación: 2400 x 1350 px a 300 DPI • Diseño inspirado en Thomas Nestico (@TJStats)")

    # Botón para forzar generación o regeneración
    with st.spinner("Renderizando tarjeta oficial en alta resolución..."):
        try:
            card_bytes = build_pitching_summary_card(
                pitcher_info=pitcher,
                game_summary=selected_game_summary,
                analysis=pitch_analysis,
                is_lvbp=(active_branch == "lvbp"),
                mode=time_mode,
                game_logs=game_logs,
                start_date=str(st.session_state["range_dates"][0]) if time_mode == "range" else None,
                end_date=str(st.session_state["range_dates"][1]) if time_mode == "range" else None,
                season=season_int,
                df_statcast=df_statcast_season,
            )
        except Exception as e:
            st.error(f"Error generando la tarjeta gráfica: {e}")
            card_bytes = None

    if card_bytes:
        st.image(card_bytes, use_container_width=True)

        safe_name = "".join(c for c in p_name if c.isalnum() or c == "_")
        league_tag = "LVBP" if active_branch == "lvbp" else "MLB"
        file_label = f"PitchingSummary_{safe_name}_{league_tag}_{season_int}_{time_mode}.png"

        st.download_button(
            label=f"📥 Descargar Tarjeta HD (PNG 300 DPI)",
            data=card_bytes,
            file_name=file_label,
            mime="image/png",
            use_container_width=True,
        )

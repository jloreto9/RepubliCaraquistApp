# pages/5_🎯_Disciplina_y_Zonas.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from utils.supabase_client import get_available_seasons
from utils.strike_zone import (
    fetch_season_pitches,
    create_strike_zone_figure,
    calculate_discipline_metrics,
    LEONES_TEAM_ID
)

st.set_page_config(
    page_title="Disciplina en el Plato y Zonas de Strike - Leones del Caracas",
    page_icon="🎯",
    layout="wide"
)

# Estilos CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #1e293b;
        border-radius: 10px;
        padding: 15px;
        border-left: 4px solid #3b82f6;
        margin-bottom: 10px;
    }
    .atbat-banner {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-left: 5px solid #FDB827;
        border-radius: 8px;
        padding: 12px 18px;
        margin-bottom: 15px;
        color: #f8fafc;
    }
</style>
""", unsafe_allow_html=True)

st.title("🎯 Disciplina en el Plato y Localización de Pitcheos")
st.markdown("Análisis avanzado de toma de decisiones en el plato (O-Swing%, Z-Swing%, Whiff Rate, CSW%), visualización de Zona de Strike y desglose turno a turno.")

# Sidebar
st.sidebar.header("⚙️ Configuración")

available_seasons = get_available_seasons()
season_options = [f"{s}-{s+1}" for s in available_seasons]
default_idx = 0
for idx, s in enumerate(available_seasons):
    if s == 2025:
        default_idx = idx
        break

selected_season_str = st.sidebar.selectbox("⚾ Temporada", season_options, index=default_idx)
selected_season = int(selected_season_str.split("-")[0])

if st.sidebar.button("🔄 Recargar Datos / Limpiar Caché"):
    st.cache_data.clear()
    st.rerun()

with st.spinner("Cargando lanzamientos de la temporada desde MLB Stats API..."):
    df_pitches = fetch_season_pitches(selected_season, team_id=LEONES_TEAM_ID, cache_version="v3_at_bats_opponents")

if df_pitches.empty:
    st.warning(f"⚠️ No se encontraron datos de lanzamientos para la temporada {selected_season_str}.")
    st.info("Prueba seleccionando la temporada **2025-2026**.")
    st.stop()

# Rol: Analizar Bateadores o Lanzadores
rol_view = st.sidebar.radio("👥 Perspectiva de Análisis", ["Bateadores de Leones", "Lanzadores de Leones"], index=0)

if rol_view == "Bateadores de Leones":
    df_pool = df_pitches[df_pitches["is_batter_leones"] == True].copy()
    player_col = "batter_name"
    opp_col = "pitcher_name"
    opp_label = "⚾ Lanzador que lanzaba"
    all_opp_label = "🌟 Todos los lanzadores rivales"
    team_title = "Leones del Caracas (Ofensiva)"
else:
    df_pool = df_pitches[df_pitches["is_pitcher_leones"] == True].copy()
    player_col = "pitcher_name"
    opp_col = "batter_name"
    opp_label = "🏏 Bateador contrario"
    all_opp_label = "🌟 Todos los bateadores contrarios"
    team_title = "Leones del Caracas (Pitcheo)"

# Filtro Temporal
df_pool["game_date_dt"] = pd.to_datetime(df_pool["game_date"])
tipo_temporal = st.sidebar.radio("📅 Alcance Temporal", ["Toda la Temporada", "Por Rango de Fechas", "Por Juego Específico"], index=0)

df_time = df_pool.copy()
suffix = ""

if tipo_temporal == "Por Rango de Fechas":
    min_d = df_pool["game_date_dt"].min().date()
    max_d = df_pool["game_date_dt"].max().date()
    d_range = st.sidebar.date_input("Rango de Fechas", value=(min_d, max_d), min_value=min_d, max_value=max_d)
    if isinstance(d_range, (list, tuple)) and len(d_range) == 2:
        df_time = df_pool[(df_pool["game_date_dt"].dt.date >= d_range[0]) & (df_pool["game_date_dt"].dt.date <= d_range[1])]
        suffix = f" ({d_range[0].strftime('%d/%m')} al {d_range[1].strftime('%d/%m')})"
elif tipo_temporal == "Por Juego Específico":
    games_u = df_pool.drop_duplicates(subset=["game_pk"]).sort_values("game_date", ascending=False)
    g_map = {f"📅 {g.get('game_date')} | {g.get('away_team')} @ {g.get('home_team')}": g["game_pk"] for _, g in games_u.iterrows()}
    sel_g_label = st.sidebar.selectbox("🏟️ Seleccionar Partido", list(g_map.keys()))
    sel_pk = g_map[sel_g_label]
    df_time = df_pool[df_pool["game_pk"] == sel_pk]
    suffix = f" - {sel_g_label.replace('📅 ', '')}"

# Selector de Jugador Principal (Leones)
counts = df_time[player_col].value_counts()
player_list = [f"{name} ({c} pitcheos)" for name, c in counts.items()]
player_map = {f"{name} ({c} pitcheos)": name for name, c in counts.items()}

all_label = f"🌟 Todos ({team_title})"
sel_player_display = st.sidebar.selectbox(
    f"👤 Seleccionar Jugador ({'Bateador' if rol_view == 'Bateadores de Leones' else 'Lanzador'})",
    [all_label] + player_list,
    key=f"player_sel_{rol_view}"
)

if sel_player_display == all_label:
    df_subject = df_time.copy()
    current_name = f"{team_title}{suffix}"
else:
    chosen = player_map[sel_player_display]
    df_subject = df_time[df_time[player_col] == chosen].copy()
    current_name = f"{chosen}{suffix}"

# Selector de Rival / Oponente Enfrentado
st.sidebar.markdown("---")
st.sidebar.header("⚔️ Rival Enfrentado")
opp_counts = df_subject[opp_col].value_counts()
opp_list = [f"{name} ({c} pitcheos)" for name, c in opp_counts.items()]
opp_map = {f"{name} ({c} pitcheos)": name for name, c in opp_counts.items()}

sel_opp_display = st.sidebar.selectbox(
    opp_label,
    [all_opp_label] + opp_list,
    key=f"opp_sel_{rol_view}"
)
if sel_opp_display != all_opp_label:
    chosen_opp = opp_map[sel_opp_display]
    df_subject = df_subject[df_subject[opp_col] == chosen_opp].copy()
    current_name += f" vs {chosen_opp}"

# Selector de Turno al Bate / Enfrentamiento
st.sidebar.markdown("---")
st.sidebar.header("🎯 Selección de Turnos")

# Construir opciones de turnos
at_bats_list = []
at_bats_dict = {}

if not df_subject.empty:
    # Agrupar ordenado por fecha e índice de turno
    grouped_ab = df_subject.groupby(["game_pk", "at_bat_index"], sort=False)
    for (g_pk, ab_idx), ab_df in grouped_ab:
        first = ab_df.iloc[0]
        try:
            d_str = pd.to_datetime(first["game_date"]).strftime("%d/%m")
        except:
            d_str = str(first.get("game_date", ""))
        inn = first.get("inning", 1)
        half_sym = "▲" if first.get("half") == "top" else "▼"
        opp_n = first.get(opp_col, "Rival")
        ev = first.get("play_event", "En juego")
        p_count = len(ab_df)
        label = f"📅 {d_str} | {half_sym}Inn {inn} vs {opp_n} ➔ {ev} ({p_count} lanz.)"
        
        at_bats_list.append(label)
        at_bats_dict[label] = {
            "game_pk": g_pk,
            "at_bat_index": ab_idx,
            "desc": first.get("play_desc", ""),
            "event": ev,
            "opp": opp_n,
            "batter": first.get("batter_name", ""),
            "pitcher": first.get("pitcher_name", ""),
            "inning": inn,
            "pitches": p_count
        }

all_turnos_label = f"🌟 Todos los turnos ({len(at_bats_list)} turnos)"
sel_turno_display = st.sidebar.selectbox(
    "🎯 Turno al Bate / Enfrentamiento",
    [all_turnos_label] + at_bats_list,
    key=f"turno_sel_{rol_view}"
)

selected_single_turno = None
if sel_turno_display != all_turnos_label and sel_turno_display in at_bats_dict:
    selected_single_turno = at_bats_dict[sel_turno_display]
    df_subject = df_subject[
        (df_subject["game_pk"] == selected_single_turno["game_pk"]) &
        (df_subject["at_bat_index"] == selected_single_turno["at_bat_index"])
    ].copy()
    current_name += f" (Turno Inn {selected_single_turno['inning']} - {selected_single_turno['event']})"

# Filtros adicionales
st.sidebar.markdown("---")
st.sidebar.header("🔍 Filtros de Situación")

# Conteo
conteo_opt = st.sidebar.selectbox(
    "Situación de Conteo",
    ["Todos los Conteos", "Con 2 Strikes (0-2, 1-2, 2-2, 3-2)", "Cuenta Llena (3-2)", "Primer Pitcheo (0-0)", "Conteo Favorable Bateador (2-0, 3-0, 3-1)"]
)

if conteo_opt == "Con 2 Strikes (0-2, 1-2, 2-2, 3-2)":
    df_subject = df_subject[df_subject["strikes"] == 2]
elif conteo_opt == "Cuenta Llena (3-2)":
    df_subject = df_subject[(df_subject["balls"] == 3) & (df_subject["strikes"] == 2)]
elif conteo_opt == "Primer Pitcheo (0-0)":
    df_subject = df_subject[(df_subject["balls"] == 0) & (df_subject["strikes"] == 0)]
elif conteo_opt == "Conteo Favorable Bateador (2-0, 3-0, 3-1)":
    df_subject = df_subject[df_subject["count_str"].isin(["2-0", "3-0", "3-1"])]

# Tipo de llamada
llamadas_disp = ["Whiff", "Called Strike", "In Play", "Foul", "Ball"]
llamadas_sel = st.sidebar.multiselect(
    "Resultado del Pitcheo",
    llamadas_disp,
    default=llamadas_disp
)
if llamadas_sel:
    df_subject = df_subject[df_subject["call_group"].isin(llamadas_sel)]

# Banner descriptivo si se escogió un turno individual
if selected_single_turno:
    opp_title = f"Lanzador que lanzaba: **{selected_single_turno['pitcher']}**" if rol_view == "Bateadores de Leones" else f"Bateador contrario: **{selected_single_turno['batter']}**"
    st.markdown(f"""
    <div class="atbat-banner">
        <h4 style="margin: 0 0 5px 0; color: #FDB827;">🎯 Detalle del Turno al Bate Seleccionado</h4>
        <p style="margin: 0 0 5px 0; font-size: 1.05rem;">
            <b>Inning {selected_single_turno['inning']}</b> | {opp_title} | 
            Resultado: <b style="color: #38bdf8;">{selected_single_turno['event']}</b> | 
            Total: <b>{selected_single_turno['pitches']} pitcheos</b>
        </p>
        <p style="margin: 0; font-size: 0.9rem; color: #cbd5e1; font-style: italic;">
            📝 {selected_single_turno['desc']}
        </p>
    </div>
    """, unsafe_allow_html=True)

# Cálculo de Métricas
m = calculate_discipline_metrics(df_subject)

# KPI Cards
st.markdown("### 📊 Métricas de Disciplina y Control en el Plato")
c1, c2, c3, c4, c5, c6 = st.columns(6)

with c1:
    st.metric("O-Swing % (Chase)", f"{m['o_swing_pct']}%", help="Porcentaje de swings a pitcheos fuera de la zona de strike (persecución).")
with c2:
    st.metric("Z-Swing % (Zona)", f"{m['z_swing_pct']}%", help="Porcentaje de swings a pitcheos dentro de la zona de strike.")
with c3:
    st.metric("Z-Contact %", f"{m['z_contact_pct']}%", help="Porcentaje de contacto cuando se hace swing a lanzamientos en zona.")
with c4:
    st.metric("Whiff % (Abanicado)", f"{m['whiff_pct']}%", help="Tasa de abanicados en blanco sobre total de swings.")
with c5:
    st.metric("SwStr % (Swing Blanco)", f"{m['swstr_pct']}%", help="Porcentaje de pitcheos totales que resultan en abanicados en blanco.")
with c6:
    st.metric("CSW % (Strikes+Whiffs)", f"{m['csw_pct']}%", help="Called Strikes + Whiffs sobre total de lanzamientos (Métrica reina para lanzadores).")

st.markdown("---")

# Visualización: Strike Zone + Métricas de Zona
col_left, col_right = st.columns([7, 5])

with col_left:
    fig_zone = create_strike_zone_figure(
        df_subject,
        title_player=current_name,
        rol_view=rol_view,
        show_sequence_numbers=(selected_single_turno is not None)
    )
    st.plotly_chart(fig_zone, use_container_width=True)

with col_right:
    st.markdown("#### 🎯 Distribución de Resultados")
    call_counts = df_subject["call_group"].value_counts().reset_index()
    call_counts.columns = ["Resultado", "Cantidad"]
    
    color_map = {
        "Whiff": "#e74c3c",
        "Called Strike": "#f39c12",
        "In Play": "#2ecc71",
        "Foul": "#3498db",
        "Ball": "#94a3b8"
    }
    
    fig_pie = px.pie(
        call_counts,
        names="Resultado",
        values="Cantidad",
        color="Resultado",
        color_discrete_map=color_map,
        hole=0.4
    )
    fig_pie.update_layout(
        template="plotly_dark",
        margin=dict(l=10, r=10, t=10, b=10),
        height=260,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig_pie, use_container_width=True)
    
    st.markdown("#### ⚡ Rendimiento en Zona vs Fuera de Zona")
    zone_comp_df = pd.DataFrame({
        "Métrica": ["En Zona (Z-Swing)", "Fuera de Zona (O-Swing)", "Contacto en Zona", "Contacto Fuera Zona"],
        "Porcentaje": [m["z_swing_pct"], m["o_swing_pct"], m["z_contact_pct"], m["o_contact_pct"]],
        "Color": ["#2ecc71", "#e74c3c", "#3498db", "#f39c12"]
    })
    fig_bar = px.bar(
        zone_comp_df,
        x="Métrica",
        y="Porcentaje",
        color="Métrica",
        color_discrete_map={
            "En Zona (Z-Swing)": "#2ecc71",
            "Fuera de Zona (O-Swing)": "#e74c3c",
            "Contacto en Zona": "#3498db",
            "Contacto Fuera Zona": "#f39c12"
        },
        text_auto=".1f"
    )
    fig_bar.update_layout(
        template="plotly_dark",
        showlegend=False,
        height=230,
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis_title="%"
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# Tabla expandible
with st.expander("📋 Registro Detallado de Lanzamientos y Secuencia", expanded=False):
    if not df_subject.empty:
        disp_cols = ["game_date", "inning", "pitch_number", "batter_name", "pitcher_name", "count_str", "call_es", "pitch_type", "play_event", "x_ft", "z_ft"]
        rename_map = {
            "game_date": "Fecha",
            "inning": "Inning",
            "pitch_number": "Pitcheo #",
            "batter_name": "Bateador",
            "pitcher_name": "Lanzador que lanzaba" if rol_view == "Bateadores de Leones" else "Lanzador (Leones)",
            "count_str": "Cuenta",
            "call_es": "Resultado Lanzamiento",
            "pitch_type": "Tipo Pitcheo",
            "play_event": "Resultado del Turno",
            "x_ft": "X (ft)",
            "z_ft": "Z (ft)"
        }
        valid_cols = [c for c in disp_cols if c in df_subject.columns]
        st_df = df_subject[valid_cols].rename(columns=rename_map)
        st.dataframe(st_df, use_container_width=True, hide_index=True)
        
        csv = st_df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Descargar lanzamientos en CSV", data=csv, file_name=f"pitches_{selected_season}.csv", mime="text/csv")

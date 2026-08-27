# pages/4_🎯_Spray_Charts.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from utils.supabase_client import get_available_seasons, get_current_season
from utils.teams import get_team_logo, get_team_name, get_team_abbr, LVBP_TEAMS, get_brand_logo
from utils.spray_chart import (
    fetch_season_batted_balls,
    create_spray_chart_figure,
    calculate_spray_stats,
    LEONES_TEAM_ID
)

st.set_page_config(
    page_title="Spray Charts - Leones del Caracas",
    page_icon="🎯",
    layout="wide"
)

try:
    from utils.styles import inject_custom_css
    inject_custom_css()
except:
    pass

# Título y Header
col_h_logo, col_h_txt = st.columns([1, 8])
with col_h_logo:
    st.image(get_brand_logo(), width=75)
with col_h_txt:
    st.title("🎯 Spray Charts — Mapa de Dispersión de Batazos")
    st.markdown("Visualiza dónde conecta cada jugador sus batazos, tendencias direccionales (% Pull / Center / Oppo) y calidad de contacto.")

# Sidebar - Configuración y Filtros
with st.sidebar:
    st.image(get_brand_logo(), width=200)
    st.markdown("---")
    st.header("⚙️ Configuración")

# Selector de temporada
available_seasons = get_available_seasons()
# Opciones de temporada formateadas
season_options = [f"{s}-{s+1}" for s in available_seasons]
# Seleccionar por defecto 2025-2026 si está disponible
default_idx = 0
for idx, s in enumerate(available_seasons):
    if s == 2025:
        default_idx = idx
        break

selected_season_str = st.sidebar.selectbox("⚾ Temporada", season_options, index=default_idx)
selected_season = int(selected_season_str.split("-")[0])

with st.spinner("Cargando datos de batazos de la temporada..."):
    df_raw = fetch_season_batted_balls(selected_season, team_id=LEONES_TEAM_ID)

if df_raw.empty:
    st.warning(f"⚠️ No se encontraron datos de pelotas en juego para la temporada {selected_season_str}.")
    st.info("Prueba seleccionando la temporada **2025-2026**.")
    st.stop()

# Conversión de fechas
df_raw["game_date_dt"] = pd.to_datetime(df_raw["game_date"])

# 📅 Filtro Temporal (Toda la temporada, Rango de fechas, Por Juego)
tipo_temporal = st.sidebar.radio(
    "📅 Alcance Temporal",
    ["Toda la Temporada", "Por Rango de Fechas", "Por Juego Específico"],
    index=0
)

df_filtered_time = df_raw.copy()
scope_title_suffix = ""
ver_ambos = False

if tipo_temporal == "Por Rango de Fechas":
    min_date = df_raw["game_date_dt"].min().date()
    max_date = df_raw["game_date_dt"].max().date()
    
    date_range = st.sidebar.date_input(
        "Selecciona el rango de fechas",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_d, end_d = date_range
        df_filtered_time = df_raw[(df_raw["game_date_dt"].dt.date >= start_d) & (df_raw["game_date_dt"].dt.date <= end_d)]
        scope_title_suffix = f" ({start_d.strftime('%d/%m/%Y')} al {end_d.strftime('%d/%m/%Y')})"
    elif isinstance(date_range, (list, tuple)) and len(date_range) == 1:
        start_d = date_range[0]
        df_filtered_time = df_raw[df_raw["game_date_dt"].dt.date == start_d]
        scope_title_suffix = f" ({start_d.strftime('%d/%m/%Y')})"

elif tipo_temporal == "Por Juego Específico":
    # Extraer juegos únicos ordenados por fecha descendente
    games_unique = df_raw.drop_duplicates(subset=["game_pk"]).sort_values("game_date", ascending=False)
    
    game_options = []
    game_map = {}
    for _, g in games_unique.iterrows():
        away_name = g.get('away_team') if pd.notna(g.get('away_team')) else 'Visitante'
        home_name = g.get('home_team') if pd.notna(g.get('home_team')) else 'Home'
        date_str = g.get('game_date') if pd.notna(g.get('game_date')) else ''
        label = f"📅 {date_str} | {away_name} @ {home_name}"
        game_options.append(label)
        game_map[label] = g["game_pk"]
        
    selected_game_label = st.sidebar.selectbox("🏟️ Seleccionar Partido", game_options)
    selected_game_pk = game_map[selected_game_label]
    
    ver_ambos = st.sidebar.checkbox("Mostrar batazos de ambos equipos", value=False)
    
    if ver_ambos:
        df_filtered_time = df_raw[df_raw["game_pk"] == selected_game_pk]
    else:
        df_filtered_time = df_raw[(df_raw["game_pk"] == selected_game_pk) & (df_raw["is_leones"] == True)]
        
    scope_title_suffix = f" - {selected_game_label.replace('📅 ', '')}"

# Filtro de ámbito de bateadores sobre el subconjunto de tiempo
if tipo_temporal == "Por Juego Específico" and ver_ambos:
    pool_batters_df = df_filtered_time
else:
    pool_batters_df = df_filtered_time[df_filtered_time["is_leones"] == True]
    if pool_batters_df.empty:
        pool_batters_df = df_filtered_time

# Conteo de batazos por jugador para ordenar el dropdown
batter_counts = pool_batters_df["batter_name"].value_counts()
batter_list = [f"{name} ({count} contactos)" for name, count in batter_counts.items()]
batter_name_map = {f"{name} ({count} contactos)": name for name, count in batter_counts.items()}

# Selector de Jugador
team_label = "🌟 Todos los Bateadores del Juego" if (tipo_temporal == "Por Juego Específico" and ver_ambos) else "🌟 Todos los Leones del Caracas"
selected_batter_display = st.sidebar.selectbox("👤 Seleccionar Bateador", [team_label] + batter_list)

if selected_batter_display == team_label:
    df_player = pool_batters_df.copy()
    current_player_name = f"Leones del Caracas{scope_title_suffix}"
else:
    chosen_name = batter_name_map[selected_batter_display]
    df_player = pool_batters_df[pool_batters_df["batter_name"] == chosen_name].copy()
    current_player_name = f"{chosen_name}{scope_title_suffix}"

st.sidebar.markdown("---")
st.sidebar.header("🔍 Filtros de Batazos")

# Filtro 1: Resultado
resultado_opt = st.sidebar.radio(
    "Resultado del batazo",
    ["Todos los contactos", "Solo Hits (1B, 2B, 3B, HR)", "Extra-bases (2B, 3B, HR)", "Solo Outs"],
    index=0
)

if resultado_opt == "Solo Hits (1B, 2B, 3B, HR)":
    df_player = df_player[df_player["is_hit"] == True]
elif resultado_opt == "Extra-bases (2B, 3B, HR)":
    df_player = df_player[df_player["event"].isin(["Double", "Triple", "Home Run"])]
elif resultado_opt == "Solo Outs":
    df_player = df_player[df_player["is_hit"] == False]

# Filtro 2: Trayectoria
trayectorias_disponibles = [
    ("line_drive", "Líneas (LD)"),
    ("fly_ball", "Elevados (FB)"),
    ("ground_ball", "Rollings (GB)"),
    ("popup", "Pop ups (PU)")
]
traj_selected = st.sidebar.multiselect(
    "Trayectoria",
    options=[t[0] for t in trayectorias_disponibles],
    format_func=lambda x: dict(trayectorias_disponibles).get(x, x),
    default=[t[0] for t in trayectorias_disponibles]
)
if traj_selected:
    df_player = df_player[df_player["trajectory"].isin(traj_selected)]

# Filtro 3: Dureza de contacto
durezas_disponibles = [
    ("hard", "Fuerte (Hard)"),
    ("medium", "Medio (Medium)"),
    ("soft", "Suave (Soft)")
]
dureza_selected = st.sidebar.multiselect(
    "Dureza de Contacto",
    options=[d[0] for d in durezas_disponibles],
    format_func=lambda x: dict(durezas_disponibles).get(x, x),
    default=[d[0] for d in durezas_disponibles]
)
if dureza_selected:
    df_player = df_player[df_player["hardness"].isin(dureza_selected)]

# Filtro 4: Mano del lanzador
mano_pitcher = st.sidebar.selectbox(
    "Mano del Lanzador Rival",
    ["Todos", "vs Lanzadores Derechos (RHP)", "vs Lanzadores Zurdos (LHP)"]
)
if mano_pitcher == "vs Lanzadores Derechos (RHP)":
    df_player = df_player[df_player["pitch_hand"] == "R"]
elif mano_pitcher == "vs Lanzadores Zurdos (LHP)":
    df_player = df_player[df_player["pitch_hand"] == "L"]

# Selector de color del mapa
color_mode = st.sidebar.radio("Esquema de Colores", ["Por Resultado", "Por Trayectoria", "Por Dureza"], horizontal=True)
color_key = "event" if color_mode == "Por Resultado" else ("trajectory" if color_mode == "Por Trayectoria" else "hardness")

# Cálculo de estadísticas
stats = calculate_spray_stats(df_player)

# Métricas Principales (KPI Cards)
st.markdown("### 📊 Métricas de Contacto")
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric("Contactos", f"{stats['total_batted']}")
with col2:
    st.metric("Hits", f"{stats['total_hits']}")
with col3:
    st.metric("BABIP en Juego", f"{stats['babip']:.3f}")
with col4:
    st.metric("Pull % (Halado)", f"{stats['pct_pull']}%")
with col5:
    st.metric("Cent % (Centro)", f"{stats['pct_center']}%")
with col6:
    st.metric("Oppo % (Opuesta)", f"{stats['pct_oppo']}%")

st.markdown("---")

# Sección Principal: Gráfico de Campo + Desgloses
col_chart, col_side = st.columns([7, 5])

with col_chart:
    fig_spray = create_spray_chart_figure(df_player, player_name=current_player_name, color_mode=color_key)
    st.plotly_chart(fig_spray, use_container_width=True)

with col_side:
    st.markdown("#### 🎯 Distribución Direccional")
    
    # Gráfico de Donut de Dirección
    dir_data = pd.DataFrame({
        "Dirección": ["Pull (Halado)", "Center (Centro)", "Oppo (Banda Opuesta)"],
        "Porcentaje": [stats["pct_pull"], stats["pct_center"], stats["pct_oppo"]],
        "Color": ["#e74c3c", "#3498db", "#2ecc71"]
    })
    fig_dir = px.pie(
        dir_data,
        names="Dirección",
        values="Porcentaje",
        color="Dirección",
        color_discrete_map={
            "Pull (Halado)": "#e74c3c",
            "Center (Centro)": "#3498db",
            "Oppo (Banda Opuesta)": "#2ecc71"
        },
        hole=0.45
    )
    fig_dir.update_layout(
        template="plotly_dark",
        margin=dict(l=10, r=10, t=20, b=20),
        height=240,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig_dir, use_container_width=True)
    
    st.markdown("#### 🚀 Calidad y Tipo de Contacto")
    tab_traj, tab_hard = st.tabs(["Trayectoria", "Dureza"])
    
    with tab_traj:
        traj_df = pd.DataFrame({
            "Tipo": ["Líneas (LD)", "Elevados (FB)", "Rollings (GB)", "Pop ups (PU)"],
            "Porcentaje": [stats["pct_ld"], stats["pct_fb"], stats["pct_gb"], stats["pct_pu"]],
            "Color": ["#3498db", "#e67e22", "#2ecc71", "#9b59b6"]
        })
        fig_traj = px.bar(
            traj_df,
            x="Tipo",
            y="Porcentaje",
            color="Tipo",
            color_discrete_map={
                "Líneas (LD)": "#3498db",
                "Elevados (FB)": "#e67e22",
                "Rollings (GB)": "#2ecc71",
                "Pop ups (PU)": "#9b59b6"
            },
            text_auto=".1f"
        )
        fig_traj.update_layout(
            template="plotly_dark",
            showlegend=False,
            height=220,
            margin=dict(l=10, r=10, t=10, b=10),
            yaxis_title="%"
        )
        st.plotly_chart(fig_traj, use_container_width=True)
        
    with tab_hard:
        hard_df = pd.DataFrame({
            "Dureza": ["Fuerte (Hard)", "Medio (Med)", "Suave (Soft)"],
            "Porcentaje": [stats["pct_hard"], stats["pct_medium"], stats["pct_soft"]],
            "Color": ["#e74c3c", "#f39c12", "#95a5a6"]
        })
        fig_hard = px.bar(
            hard_df,
            x="Dureza",
            y="Porcentaje",
            color="Dureza",
            color_discrete_map={
                "Fuerte (Hard)": "#e74c3c",
                "Medio (Med)": "#f39c12",
                "Suave (Soft)": "#95a5a6"
            },
            text_auto=".1f"
        )
        fig_hard.update_layout(
            template="plotly_dark",
            showlegend=False,
            height=220,
            margin=dict(l=10, r=10, t=10, b=10),
            yaxis_title="%"
        )
        st.plotly_chart(fig_hard, use_container_width=True)

# Sección Inferior: Tabla de Detalle
with st.expander("📋 Ver Registro Detallado de Contactos (Jugada por Jugada)", expanded=False):
    if not df_player.empty:
        display_cols = [
            "game_date", "opposing_team", "batter_name", "bat_side",
            "pitcher_name", "pitch_hand", "event_es", "trajectory_es",
            "hardness_es", "distance_ft", "description"
        ]
        rename_dict = {
            "game_date": "Fecha",
            "opposing_team": "Rival",
            "batter_name": "Bateador",
            "bat_side": "Batea",
            "pitcher_name": "Lanzador",
            "pitch_hand": "Lanza",
            "event_es": "Resultado",
            "trajectory_es": "Trayectoria",
            "hardness_es": "Dureza",
            "distance_ft": "Distancia (ft)",
            "description": "Descripción de la Jugada"
        }
        
        valid_cols = [c for c in display_cols if c in df_player.columns]
        table_df = df_player[valid_cols].rename(columns=rename_dict)
        st.dataframe(table_df, use_container_width=True, hide_index=True)
        
        csv_data = table_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Descargar datos en CSV",
            data=csv_data,
            file_name=f"spray_data_{selected_season}_{current_player_name.replace(' ', '_')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No hay jugadas que coincidan con los filtros seleccionados.")

# Glosario y Leyenda de Spray Charts y Contacto
with st.expander("📖 Guía y Glosario: ¿Cómo entender los Spray Charts y Métricas de Contacto?", expanded=False):
    st.markdown(r"""
    ### 🎯 ¿Qué nos enseña el Spray Chart?
    El gráfico de dispersión espacial (*Spray Chart*) mapea las coordenadas exactas $(x, y)$ donde cayó cada batazo en el terreno de juego, revelando las tendencias del bateador y cómo los rivales deben posicionar sus formaciones defensivas (*defensive shifts*).

    | Concepto / Métrica | ¿Qué significa? | ¿Cómo interpretarlo? |
    |---|---|---|
    | **Pull% (Halar)** | Batazos dirigidos a su banda natural (Left Field para derechos; Right Field para zurdos). | Donde se genera la mayor cantidad de jonrones y poder. |
    | **Cent% (Centro)** | Batazos dirigidos hacia el Center Field. | Refleja un swing balanceado y contacto directo con la pelota. |
    | **Oppo% (Banda Contraria)** | Batazos dirigidos hacia el campo opuesto (Right Field para derechos; Left Field para zurdos). | Mide la habilidad para batear lanzamientos afuera y aprovechar huecos defensivos. |
    | **Hard% (Contacto Fuerte)** | Batazos conectados a gran velocidad de salida ($\ge 95\text{ mph}$). | Mayor probabilidad de convertirse en extrabases y hits. |
    | **Med% (Contacto Medio)** | Batazos conectados con velocidad moderada. | Contacto promedio en bolas en juego. |
    | **Soft% (Contacto Débil)** | Batazos mal conectados o rozados. | Facilidad para que la defensa retire al bateador. |
    | **Line Drive (Línea)** | Batazo recto y tenso con ángulo de lanzamiento ideal ($10^\circ - 25^\circ$). | El tipo de batazo con mayor porcentaje de convertirse en hit ($>.600\text{ AVG}$). |
    | **Flyball (Elevado)** | Batazo por el aire ($25^\circ - 50^\circ$). | Oportunidad de jonrón si se conecta con fuerza; out fácil si es débil. |
    | **Groundball (Rolling)** | Batazo por el suelo ($< 10^\circ$). | Menor probabilidad de extrabase; riesgo de doble play. |
    | **Pop Up (Elevado al Cuadro)** | Elevado altísimo dentro del infield ($> 50^\circ$). | Prácticamente un out seguro ($99\%$ de outs). |
    """)

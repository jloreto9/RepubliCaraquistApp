# pages/2_⚾_Estadisticas_Individuales.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys
import os

# Agregar el directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar funciones
from utils.supabase_client import (
    get_batting_stats,
    get_pitching_stats,
    get_individual_fielding_stats,
    get_current_season,
    get_available_seasons,
    init_supabase
)
from utils.teams import get_team_logo, get_team_name, get_team_abbr, LVBP_TEAMS, LVBP_ABBR, get_brand_logo
from utils.matchup_card import build_matchup_image

st.set_page_config(page_title="Estadísticas Individuales - RepubliCaraquistApp", page_icon="⚾", layout="wide")

try:
    from utils.styles import inject_custom_css
    inject_custom_css()
except:
    pass

# Colores de los Leones
LEONES_GOLD = "#FDB827"
LEONES_RED = "#CE1141"

# Sidebar con Logo Oficial República Caraquista
with st.sidebar:
    st.image(get_brand_logo(), width=200)
    st.markdown("---")

# Header
col_h_logo, col_h_txt = st.columns([1, 8])
with col_h_logo:
    st.image(get_brand_logo(), width=75)
with col_h_txt:
    st.title("⚾ Estadísticas Individuales")
    st.markdown("### Líderes de Bateo, Pitcheo y Fildeo — Leones del Caracas")

# Selector de temporada
col1, col2 = st.columns([3, 1])

with col1:
    current_season = get_current_season()
    available_seasons = get_available_seasons()

    if not available_seasons:
        available_seasons = [current_season]

    # Crear diccionario para el selector
    season_options = {}
    for season in available_seasons:
        display_text = f"{season}-{season+1}"
        season_options[display_text] = season

    # Determinar índice de la temporada actual
    current_season_display = f"{current_season}-{current_season+1}"
    season_list = list(season_options.keys())
    default_index = season_list.index(current_season_display) if current_season_display in season_list else 0

    selected_season_display = st.selectbox(
        "⚾ Seleccionar Temporada",
        options=season_list,
        index=default_index
    )

    selected_season = season_options[selected_season_display]

# Tabs principales
tab1, tab2, tab_def, tab3 = st.tabs(["🏏 Bateo", "⚾ Pitcheo", "🧤 Fildeo / Defensa", "⚔️ Matchup 360 H2H"])

# ==================== TAB 1: BATEO ====================
with tab1:
    st.markdown("### 🏏 Estadísticas de Bateo")

    # Obtener datos de bateo para la temporada seleccionada (ya vienen agregados)
    batting_df = get_batting_stats(team_id=695, limit=100, season=selected_season).copy()

    if not batting_df.empty:
        # Los datos ya vienen con player_name y todas las estadísticas calculadas
        # Solo filtrar por AB mínimo si el usuario lo especifica

        # Filtro de búsqueda
        search = st.text_input("🔍 Buscar jugador", placeholder="Nombre del jugador...")

        if search:
            batting_df = batting_df[
                batting_df['player_name'].str.contains(search, case=False, na=False)
            ]

        # Filtro de mínimo de AB
        min_ab = st.slider("Mínimo de turnos al bate (AB)", 0, 100, 10)
        batting_filtered = batting_df[batting_df['ab'] >= min_ab].copy()

        if not batting_filtered.empty:
            # Líderes en métricas clave
            st.markdown("#### 🏆 Líderes en Categorías Principales")

            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                top_avg = batting_filtered.nlargest(1, 'avg').iloc[0]
                avg_display = "1.000" if top_avg['avg'] >= 1.0 else f".{int(top_avg['avg']*1000):03d}"
                st.metric(
                    "AVG Líder",
                    avg_display,
                    top_avg['player_name']
                )

            with col2:
                top_hr = batting_filtered.nlargest(1, 'hr').iloc[0]
                st.metric(
                    "HR Líder",
                    int(top_hr['hr']),
                    top_hr['player_name']
                )

            with col3:
                top_rbi = batting_filtered.nlargest(1, 'rbi').iloc[0]
                st.metric(
                    "RBI Líder",
                    int(top_rbi['rbi']),
                    top_rbi['player_name']
                )

            with col4:
                top_ops = batting_filtered.nlargest(1, 'ops').iloc[0]
                st.metric(
                    "OPS Líder",
                    f"{top_ops['ops']:.3f}",
                    top_ops['player_name']
                )

            with col5:
                top_h = batting_filtered.nlargest(1, 'h').iloc[0]
                st.metric(
                    "Hits Líder",
                    int(top_h['h']),
                    top_h['player_name']
                )

            st.markdown("---")

            # Tabla completa de estadísticas
            st.markdown("#### 📋 Tabla Completa de Bateo")

            # Preparar datos para mostrar
            display_cols = ['player_name', 'ab', 'r', 'h', 'doubles', 'triples', 'hr', 'rbi', 'bb', 'so', 'sb', 'avg', 'obp', 'slg', 'ops']
            available_cols = [col for col in display_cols if col in batting_filtered.columns]

            display_df = batting_filtered[available_cols].copy()

            # Renombrar columnas para mejor visualización
            column_names = {
                'player_name': 'Jugador',
                'ab': 'AB',
                'r': 'R',
                'h': 'H',
                'doubles': '2B',
                'triples': '3B',
                'hr': 'HR',
                'rbi': 'RBI',
                'bb': 'BB',
                'so': 'SO',
                'sb': 'SB',
                'avg': 'AVG',
                'obp': 'OBP',
                'slg': 'SLG',
                'ops': 'OPS'
            }

            display_df = display_df.rename(columns=column_names)

            # Formatear números
            for col in ['AVG', 'OBP', 'SLG', 'OPS']:
                if col in display_df.columns:
                    display_df[col] = display_df[col].apply(lambda x: f"{x:.3f}")

            # Ordenar por OPS
            if 'OPS' in display_df.columns:
                display_df = display_df.sort_values('OPS', ascending=False)

            # Mostrar tabla
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                height=400
            )

            st.markdown("---")

            # Gráficos
            st.markdown("#### 📈 Visualizaciones")

            viz_col1, viz_col2 = st.columns(2)

            with viz_col1:
                # Top 10 AVG
                top_10_avg = batting_filtered.nlargest(10, 'avg')[['player_name', 'avg']].copy()
                fig_avg = px.bar(
                    top_10_avg,
                    x='avg',
                    y='player_name',
                    orientation='h',
                    title='Top 10 - Promedio de Bateo (AVG)',
                    labels={'avg': 'AVG', 'player_name': 'Jugador'},
                    color='avg',
                    color_continuous_scale=['#CE1141', '#FDB827']
                )
                fig_avg.update_layout(
                    yaxis={'categoryorder': 'total ascending'},
                    showlegend=False,
                    height=400
                )
                st.plotly_chart(fig_avg, use_container_width=True)

            with viz_col2:
                # Top 10 HR
                top_10_hr = batting_filtered.nlargest(10, 'hr')[['player_name', 'hr']].copy()
                fig_hr = px.bar(
                    top_10_hr,
                    x='hr',
                    y='player_name',
                    orientation='h',
                    title='Top 10 - Jonrones (HR)',
                    labels={'hr': 'HR', 'player_name': 'Jugador'},
                    color='hr',
                    color_continuous_scale=['#CE1141', '#FDB827']
                )
                fig_hr.update_layout(
                    yaxis={'categoryorder': 'total ascending'},
                    showlegend=False,
                    height=400
                )
                st.plotly_chart(fig_hr, use_container_width=True)

            viz_col3, viz_col4 = st.columns(2)

            with viz_col3:
                # Top 10 RBI
                top_10_rbi = batting_filtered.nlargest(10, 'rbi')[['player_name', 'rbi']].copy()
                fig_rbi = px.bar(
                    top_10_rbi,
                    x='rbi',
                    y='player_name',
                    orientation='h',
                    title='Top 10 - Carreras Impulsadas (RBI)',
                    labels={'rbi': 'RBI', 'player_name': 'Jugador'},
                    color='rbi',
                    color_continuous_scale=['#CE1141', '#FDB827']
                )
                fig_rbi.update_layout(
                    yaxis={'categoryorder': 'total ascending'},
                    showlegend=False,
                    height=400
                )
                st.plotly_chart(fig_rbi, use_container_width=True)

            with viz_col4:
                # Top 10 OPS
                top_10_ops = batting_filtered.nlargest(10, 'ops')[['player_name', 'ops']].copy()
                fig_ops = px.bar(
                    top_10_ops,
                    x='ops',
                    y='player_name',
                    orientation='h',
                    title='Top 10 - OPS (On-base Plus Slugging)',
                    labels={'ops': 'OPS', 'player_name': 'Jugador'},
                    color='ops',
                    color_continuous_scale=['#CE1141', '#FDB827']
                )
                fig_ops.update_layout(
                    yaxis={'categoryorder': 'total ascending'},
                    showlegend=False,
                    height=400
                )
                st.plotly_chart(fig_ops, use_container_width=True)

            # Glosario y Leyenda de Bateo
            with st.expander("📖 Guía y Glosario: ¿Cómo entender las Estadísticas de Bateo?", expanded=False):
                st.markdown(r"""
                ### 🏏 Guía Completa de Métricas Ofensivas

                | Abreviatura | Nombre Completo | ¿Qué significa y cómo se calcula? | ¿Cómo interpretarlo? (Escala de Calidad) |
                |---|---|---|---|
                | **PA** | Apariciones al Plato (Plate Appearances) | Total de visitas a la caja de bateo: $AB + BB + HBP + SF + SH + \text{Interferencias}$. | Mide el tiempo de juego y oportunidades del bateador. |
                | **AB** | Turnos Oficiales al Bate (At Bats) | Viajes al plato donde no hubo boleto, pelotazo ni sacrificio. Es la base para calcular el promedio (AVG). | Menor que las PA; no castiga al bateador por recibir bases por bolas. |
                | **H** | Hits (Imparables) | Batazos en terreno bueno que permiten al bateador llegar a base sin error ni jugada de selección. | $H = 1B + 2B + 3B + HR$. |
                | **2B / 3B** | Dobles / Triples | Imparables de dos o tres bases. | Mide la velocidad y habilidad de extrabase del bateador. |
                | **HR** | Jonrones (Home Runs) | Batazos fuera del parque o cuadrangulares dentro del campo. | Principal métrica de poder absoluto. |
                | **RBI / CI** | Carreras Impulsadas (Runs Batted In) | Carreras anotadas por compañeros directamente gracias al batazo o boleto del bateador. | Mide la capacidad de remolque con corredores en base. |
                | **R / CA** | Carreras Anotadas (Runs) | Veces que el jugador cruzó el plato de home. | Refleja la capacidad de embasarse y el buen corrido de bases. |
                | **BB** | Boletos / Bases por Bolas (Walks) | Turnos con 4 lanzamientos fuera de la zona de strike. | Refleja disciplina y paciencia en el plato. |
                | **SO / K** | Ponches (Strikeouts) | Turnos donde el bateador acumula 3 strikes (tirándole o mirando). | Menos es mejor; indica contacto y control del strike zone. |
                | **BR / SB** | Bases Robadas (Stolen Bases) | Avances de base exitosos durante el movimiento del lanzador sin mediar hit. | Mide velocidad y agresividad en las almohadillas. |
                | **CR / CS** | Atrapado Robando (Caught Stealing) | Corredor puesto out intentando robar base. | Menos es mejor. |
                | **AVG** | Promedio de Bateo (Batting Average) | $\text{AVG} = \frac{H}{AB}$. Frecuencia con la que conecta de hit. | **Élite:** $>.300$ | **Bueno:** $.270 - .299$ | **Promedio:** $.250$ | **Bajo:** $<.220$. |
                | **OBP** | Porcentaje de Embasado (On-Base Pct) | $\text{OBP} = \frac{H + BB + HBP}{AB + BB + HBP + SF}$. Probabilidad de llegar a base vivo por cualquier vía. | **Élite:** $>.400$ | **Muy Bueno:** $.360 - .399$ | **Promedio:** $.320$ | **Bajo:** $<.300$. |
                | **SLG** | Promedio de Slugging (Poder) | $\text{SLG} = \frac{1B + 2(2B) + 3(3B) + 4(HR)}{AB}$. Total de bases alcanzadas por turno. | **Élite:** $>.500$ | **Bueno:** $.420 - .499$ | **Promedio:** $.380$ | **Bajo:** $<.350$. |
                | **OPS** | On-Base Plus Slugging | $\text{OPS} = OBP + SLG$. **La métrica reina ofensiva:** mide capacidad de embasarse + poder simultáneamente. | **Monstruo:** $>.900$ | **Gran Bateador:** $.800 - .899$ | **Promedio:** $.700 - .799$ | **Débil:** $<.650$. |
                """)

        else:
            st.warning(f"No hay jugadores con al menos {min_ab} turnos al bate.")

    else:
        st.info("📊 No hay datos de bateo disponibles para esta temporada.")
        st.markdown("""
        Las estadísticas de bateo se actualizarán automáticamente cuando:
        - Se carguen juegos de la temporada seleccionada
        - El proceso de actualización diaria se ejecute
        - Se sincronicen los datos con la base de datos
        """)

# ==================== TAB 2: PITCHEO ====================
with tab2:
    st.markdown("### ⚾ Estadísticas de Pitcheo")

    # Obtener datos de pitcheo para la temporada seleccionada (ya vienen agregados)
    pitching_df = get_pitching_stats(team_id=695, limit=100, season=selected_season).copy()

    if not pitching_df.empty:
        # Los datos ya vienen con player_name y todas las estadísticas calculadas

        # Filtro de búsqueda
        search = st.text_input("🔍 Buscar lanzador", placeholder="Nombre del lanzador...")

        if search:
            pitching_df = pitching_df[
                pitching_df['player_name'].str.contains(search, case=False, na=False)
            ]

        # Filtro de mínimo de IP
        min_ip = st.slider("Mínimo de innings lanzados (IP)", 0.0, 50.0, 5.0, 0.1)
        pitching_filtered = pitching_df[pitching_df['ip'] >= min_ip].copy()

        if not pitching_filtered.empty:
            # Líderes en métricas clave
            st.markdown("#### 🏆 Líderes en Categorías Principales")

            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                top_era = pitching_filtered.nsmallest(1, 'era').iloc[0]
                st.metric(
                    "ERA Líder",
                    f"{top_era['era']:.2f}",
                    top_era['player_name']
                )

            with col2:
                top_k = pitching_filtered.nlargest(1, 'so').iloc[0]
                st.metric(
                    "K Líder",
                    int(top_k['so']),
                    top_k['player_name']
                )

            with col3:
                top_wins = pitching_filtered.nlargest(1, 'w').iloc[0]
                st.metric(
                    "Victorias Líder",
                    int(top_wins['w']),
                    top_wins['player_name']
                )

            with col4:
                top_whip = pitching_filtered.nsmallest(1, 'whip').iloc[0]
                st.metric(
                    "WHIP Líder",
                    f"{top_whip['whip']:.2f}",
                    top_whip['player_name']
                )

            with col5:
                if 'sv' in pitching_filtered.columns:
                    top_sv = pitching_filtered.nlargest(1, 'sv').iloc[0]
                    st.metric(
                        "Salvados Líder",
                        int(top_sv['sv']),
                        top_sv['player_name']
                    )
                else:
                    st.metric("Salvados", "N/A", "Sin datos")

            st.markdown("---")

            # Tabla completa de estadísticas
            st.markdown("#### 📋 Tabla Completa de Pitcheo")

            # Preparar datos para mostrar
            display_cols = ['player_name', 'w', 'l', 'era', 'g', 'gs', 'sv', 'ip', 'h', 'r', 'er', 'bb', 'so', 'whip']
            available_cols = [col for col in display_cols if col in pitching_filtered.columns]

            display_df = pitching_filtered[available_cols].copy()

            # Renombrar columnas
            column_names = {
                'player_name': 'Jugador',
                'w': 'W',
                'l': 'L',
                'era': 'ERA',
                'g': 'G',
                'gs': 'GS',
                'sv': 'SV',
                'ip': 'IP',
                'h': 'H',
                'r': 'R',
                'er': 'ER',
                'bb': 'BB',
                'so': 'SO',
                'whip': 'WHIP'
            }

            display_df = display_df.rename(columns=column_names)

            # Formatear números
            for col in ['ERA', 'WHIP', 'IP']:
                if col in display_df.columns:
                    display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}")

            # Ordenar por ERA
            if 'ERA' in display_df.columns:
                # Convertir de vuelta a float para ordenar
                display_df['ERA_sort'] = display_df['ERA'].astype(float)
                display_df = display_df.sort_values('ERA_sort')
                display_df = display_df.drop('ERA_sort', axis=1)

            # Mostrar tabla
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                height=400
            )

            # Acceso directo al módulo de Pitching Summary & Telemetría
            st.markdown("##### 🔥 Telemetría y Tarjetas HD de Pitcheo")
            col_insp1, col_insp2 = st.columns([3, 1])
            with col_insp1:
                pitcher_opts = {
                    f"{row['player_name']} ({row.get('w', 0)}W-{row.get('l', 0)}L, {float(row.get('era', 0.0)):.2f} ERA, {row.get('so', 0)} K)": row['player_id']
                    for _, row in pitching_filtered.iterrows()
                    if 'player_id' in row and pd.notna(row['player_id'])
                }
                if pitcher_opts:
                    sel_p_lbl = st.selectbox(
                        "Seleccionar lanzador para analizar telemetría y generar tarjeta gráfica Nestico (300 DPI):",
                        list(pitcher_opts.keys()),
                        key="sb_inspect_pitcher"
                    )
                    sel_p_id = pitcher_opts[sel_p_lbl]
            with col_insp2:
                if pitcher_opts:
                    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                    if st.button("🔥 Abrir Pitching Summary", key="btn_go_pitching", use_container_width=True):
                        st.session_state["selected_pitcher_id"] = int(sel_p_id)
                        st.switch_page("pages/9_🔥_Pitching_Summary.py")

            st.markdown("---")

            # Gráficos
            st.markdown("#### 📈 Visualizaciones")

            viz_col1, viz_col2 = st.columns(2)

            with viz_col1:
                # Top 10 Mejor ERA (menor es mejor)
                top_10_era = pitching_filtered.nsmallest(10, 'era')[['player_name', 'era']].copy()
                fig_era = px.bar(
                    top_10_era,
                    x='era',
                    y='player_name',
                    orientation='h',
                    title='Top 10 - Mejor ERA',
                    labels={'era': 'ERA', 'player_name': 'Lanzador'},
                    color='era',
                    color_continuous_scale=['#FDB827', '#CE1141']  # Invertido porque menor es mejor
                )
                fig_era.update_layout(
                    yaxis={'categoryorder': 'total descending'},
                    showlegend=False,
                    height=400
                )
                st.plotly_chart(fig_era, use_container_width=True)

            with viz_col2:
                # Top 10 Ponches
                top_10_k = pitching_filtered.nlargest(10, 'so')[['player_name', 'so']].copy()
                fig_k = px.bar(
                    top_10_k,
                    x='so',
                    y='player_name',
                    orientation='h',
                    title='Top 10 - Ponches (SO)',
                    labels={'so': 'SO', 'player_name': 'Lanzador'},
                    color='so',
                    color_continuous_scale=['#CE1141', '#FDB827']
                )
                fig_k.update_layout(
                    yaxis={'categoryorder': 'total ascending'},
                    showlegend=False,
                    height=400
                )
                st.plotly_chart(fig_k, use_container_width=True)

            viz_col3, viz_col4 = st.columns(2)

            with viz_col3:
                # Top 10 Victorias
                top_10_w = pitching_filtered.nlargest(10, 'w')[['player_name', 'w']].copy()
                fig_w = px.bar(
                    top_10_w,
                    x='w',
                    y='player_name',
                    orientation='h',
                    title='Top 10 - Victorias (W)',
                    labels={'w': 'W', 'player_name': 'Lanzador'},
                    color='w',
                    color_continuous_scale=['#CE1141', '#FDB827']
                )
                fig_w.update_layout(
                    yaxis={'categoryorder': 'total ascending'},
                    showlegend=False,
                    height=400
                )
                st.plotly_chart(fig_w, use_container_width=True)

            with viz_col4:
                # Top 10 Mejor WHIP
                top_10_whip = pitching_filtered.nsmallest(10, 'whip')[['player_name', 'whip']].copy()
                fig_whip = px.bar(
                    top_10_whip,
                    x='whip',
                    y='player_name',
                    orientation='h',
                    title='Top 10 - Mejor WHIP',
                    labels={'whip': 'WHIP', 'player_name': 'Lanzador'},
                    color='whip',
                    color_continuous_scale=['#FDB827', '#CE1141']  # Invertido
                )
                fig_whip.update_layout(
                    yaxis={'categoryorder': 'total descending'},
                    showlegend=False,
                    height=400
                )
                st.plotly_chart(fig_whip, use_container_width=True)

            # Glosario y Leyenda de Pitcheo
            with st.expander("📖 Guía y Glosario: ¿Cómo entender las Estadísticas de Pitcheo?", expanded=False):
                st.markdown(r"""
                ### ⚾ Guía Completa de Métricas de Lanzadores

                | Abreviatura | Nombre Completo | ¿Qué significa y cómo se calcula? | ¿Cómo interpretarlo? (Escala de Calidad) |
                |---|---|---|---|
                | **IP** | Entradas Lanzadas (Innings Pitched) | Cantidad de outs conseguidos divididos entre 3 ($1\text{ out} = .1$, $2\text{ outs} = .2$, $3\text{ outs} = 1.0$). | Mide la durabilidad y volumen de trabajo del lanzador. |
                | **ERA / EFE** | Efectividad (Earned Run Average) | $\text{ERA} = \frac{CL \times 9}{IP}$. Promedio de carreras limpias que permitiría en un juego de 9 entradas completas. | **Menor es mejor:**<br>• **As / Élite:** $< 3.00$<br>• **Bueno:** $3.00 - 3.99$<br>• **Promedio LVBP:** $4.20 - 4.80$<br>• **Elevado / Vulnerable:** $> 5.50$. |
                | **WHIP** | Embasados por Entrada | $\text{WHIP} = \frac{H + BB}{IP}$. Cantidad de corredores que se le embasan en promedio por cada inning. | **Menor es mejor:**<br>• **Dominante:** $< 1.15$<br>• **Bueno:** $1.15 - 1.30$<br>• **Promedio:** $1.35 - 1.45$<br>• **Peligro de tráfico:** $> 1.55$. |
                | **W / L** | Ganados y Perdidos | Decisiones oficiales acreditadas según las reglas de anotación de béisbol. | Mide victorias del equipo donde el lanzador fue factor decisivo. |
                | **SV** | Juegos Salvados (Saves) | Partidos cerrados exitosamente por el relevista en ventaja de 3 o menos carreras lanzando el 9no inning. | Métrica clave para el cerrador de cabecera. |
                | **HLD** | Ventajas Preservadas (Holds) | Relevista intermedio que entra en situación de salvado, saca outs y entrega el juego en ventaja. | Métrica clave para preparadores de mesa (8vo inning). |
                | **BS** | Oportunidades de Salvado Desperdiciadas (Blown Saves) | El relevista permitió que el rival empatara o se fuera arriba en el marcador. | Menos es mejor. |
                | **CL / ER** | Carreras Limpias (Earned Runs) | Carreras anotadas sin haber mediado errores defensivos ni passed balls. | Base para calcular la efectividad (ERA). |
                | **K / SO** | Ponches Propinados (Strikeouts) | Bateadores retirados por la vía de los tres strikes. | Mide la capacidad de generar swings fallidos y dominio puro. |
                | **BB** | Boletos Otorgados (Walks) | Bases por bolas regaladas a los rivales. | Menos es mejor; mide el control del monticulista. |
                | **K/9** | Ponches por 9 Entradas | $\frac{K \times 9}{IP}$. Promedio de ponches que conseguiría en un juego completo. | **Élite:** $> 9.0$ (más de 1 K por inning). |
                | **BB/9** | Boletos por 9 Entradas | $\frac{BB \times 9}{IP}$. Frecuencia con la que regala bases. | **Gran control:** $< 2.5$ | **Problemas de comando:** $> 4.5$. |
                | **K/BB** | Relación Ponches / Boletos | $\frac{K}{BB}$. Cuántos ponches logra por cada boleto otorgado. | **Excelente:** $> 3.0$ | **Promedio:** $2.0$ | **Pobre:** $< 1.5$. |
                | **BAA** | Promedio de Bateo en Contra | $\frac{H_{\text{permitidos}}}{AB_{\text{enfrentados}}}$. Efectividad con la que los rivales le batean de hit. | **Dominante:** $< .230$ | **Vulnerable:** $> .285$. |
                """)

        else:
            st.warning(f"No hay lanzadores con al menos {min_ip} innings lanzados.")

    else:
        st.info("📊 No hay datos de pitcheo disponibles para esta temporada.")
        st.markdown("""
        Las estadísticas de pitcheo se actualizarán automáticamente cuando:
        - Se carguen juegos de la temporada seleccionada
        - El proceso de actualización diaria se ejecute
        - Se sincronicen los datos con la base de datos
        """)

# ==================== TAB DEF: FILDEO / DEFENSA ====================
with tab_def:
    st.markdown("### 🧤 Estadísticas de Fildeo y Rendimiento Defensivo")
    st.markdown("Analiza la solvencia defensiva, asistencias, dobles matanzas y porcentaje de fildeo de los peloteros en la LVBP.")

    team_opts = {
        "🦁 Leones del Caracas": 695,
        "🌐 Toda la LVBP (Overall)": None,
        "⚓ Navegantes del Magallanes": 696,
        "🦈 Tiburones de La Guaira": 698,
        "🐯 Tigres de Aragua": 699,
        "🐦 Cardenales de Lara": 693,
        "🦅 Águilas del Zulia": 692,
        "🏹 Caribes de Anzoátegui": 694,
        "🏝️ Bravos de Margarita": 697,
    }
    col_t_def, col_f1, col_f2 = st.columns([2, 2, 2])
    with col_t_def:
        sel_team_f_name = st.selectbox("Franquicia / Alcance", list(team_opts.keys()), index=0, key="sb_field_team")
        sel_team_f_id = team_opts[sel_team_f_name]

    fielding_df = get_individual_fielding_stats(selected_season, team_id=sel_team_f_id).copy()

    if not fielding_df.empty:
        # Convertir columnas numéricas de inmediato
        num_cols = ['games', 'games_started', 'putouts', 'assists', 'errors', 'chances', 'double_plays', 'triple_plays', 'caught_stealing', 'stolen_bases', 'passed_balls']
        for col in num_cols:
            if col in fielding_df.columns:
                fielding_df[col] = pd.to_numeric(fielding_df[col], errors='coerce').fillna(0).astype(int)

        for col in ['fielding_pct', 'range_factor_per_9', 'caught_stealing_pct']:
            if col in fielding_df.columns:
                fielding_df[col] = pd.to_numeric(fielding_df[col], errors='coerce').fillna(0.0).astype(float)

        # Filtros
        with col_f1:
            search_f = st.text_input("🔍 Buscar defensor", placeholder="Nombre del jugador...", key="search_fielding")
        with col_f2:
            positions_available = ["Todas"] + sorted([p for p in fielding_df['position'].unique() if p])
            selected_pos = st.selectbox("📍 Filtrar por Posición", positions_available, index=0)

        # Aplicar filtros
        filtered_f = fielding_df.copy()
        if search_f:
            filtered_f = filtered_f[filtered_f['player_name'].str.contains(search_f, case=False, na=False)]
        if selected_pos != "Todas":
            filtered_f = filtered_f[filtered_f['position'] == selected_pos]

        # Leader cards
        f_card1, f_card2, f_card3, f_card4 = st.columns(4)
        
        # Mejor FPCT con al menos 15 lances
        qual_f = fielding_df[fielding_df['chances'] >= 15]
        if not qual_f.empty:
            best_fpct = qual_f.sort_values(['fielding_pct', 'chances'], ascending=[False, False]).iloc[0]
            val_fpct = float(best_fpct['fielding_pct'])
            with f_card1:
                st.metric("🎯 Mejor % Fildeo (Mín 15 TC)", f"{val_fpct:.3f}", f"{best_fpct['player_name']} ({best_fpct['position']})")
        else:
            with f_card1:
                st.metric("🎯 % Fildeo", "N/A")

        # Líder en Asistencias
        if not fielding_df.empty:
            lead_a = fielding_df.sort_values('assists', ascending=False).iloc[0]
            with f_card2:
                st.metric("🧤 Líder en Asistencias", f"{int(lead_a['assists'])}", f"{lead_a['player_name']} ({lead_a['position']})")

        # Líder en Doble Plays
        if not fielding_df.empty:
            lead_dp = fielding_df.sort_values('double_plays', ascending=False).iloc[0]
            with f_card3:
                st.metric("⚡ Líder en Doble Plays", f"{int(lead_dp['double_plays'])}", f"{lead_dp['player_name']} ({lead_dp['position']})")

        # Líder en Putouts
        if not fielding_df.empty:
            lead_po = fielding_df.sort_values('putouts', ascending=False).iloc[0]
            with f_card4:
                st.metric("🛡️ Líder en Outs Realizados", f"{int(lead_po['putouts'])}", f"{lead_po['player_name']} ({lead_po['position']})")

        st.markdown("---")

        # Preparar tabla para visualización
        display_f = filtered_f.copy()
        
        # Mapeo de columnas amigables
        cols_map = {
            'player_name': 'Jugador',
            'position': 'Pos',
            'games': 'JJ',
            'games_started': 'JI',
            'innings': 'Inn',
            'putouts': 'PO',
            'assists': 'A',
            'errors': 'E',
            'chances': 'TC',
            'fielding_pct': 'FPCT',
            'double_plays': 'DP',
            'range_factor_per_9': 'RF/9',
            'caught_stealing': 'CS',
            'stolen_bases': 'SB',
            'caught_stealing_pct': 'CS%',
            'passed_balls': 'PB'
        }

        # Si no es receptor, mostrar columnas estándar
        if selected_pos == "C":
            cols_to_show = ['player_name', 'position', 'games', 'games_started', 'innings', 'putouts', 'assists', 'errors', 'chances', 'fielding_pct', 'caught_stealing', 'stolen_bases', 'caught_stealing_pct', 'passed_balls', 'double_plays']
        else:
            cols_to_show = ['player_name', 'position', 'games', 'games_started', 'innings', 'putouts', 'assists', 'errors', 'chances', 'fielding_pct', 'double_plays', 'range_factor_per_9']

        cols_avail = [c for c in cols_to_show if c in display_f.columns]
        display_table = display_f[cols_avail].rename(columns=cols_map).sort_values('TC' if 'TC' in cols_map.values() else 'PO', ascending=False)

        # Formatear números
        if 'FPCT' in display_table.columns:
            display_table['FPCT'] = display_table['FPCT'].apply(lambda x: f"{float(x):.3f}" if pd.notnull(x) else ".000")
        if 'RF/9' in display_table.columns:
            display_table['RF/9'] = display_table['RF/9'].apply(lambda x: f"{float(x):.2f}" if pd.notnull(x) else "0.00")
        if 'CS%' in display_table.columns:
            display_table['CS%'] = display_table['CS%'].apply(lambda x: f"{float(x):.3f}" if pd.notnull(x) else ".000")

        st.dataframe(
            display_table,
            use_container_width=True,
            hide_index=True
        )

        # Gráficos defensivos
        st.markdown("#### 📊 Comparativas Defensivas")
        g_col1, g_col2 = st.columns(2)

        with g_col1:
            top_assists = filtered_f.nlargest(10, 'assists')
            if not top_assists.empty and top_assists['assists'].sum() > 0:
                fig_a = px.bar(
                    top_assists,
                    x='assists',
                    y='player_name',
                    orientation='h',
                    title='Top 10 — Líderes en Asistencias',
                    labels={'assists': 'Asistencias', 'player_name': 'Jugador'},
                    color='assists',
                    color_continuous_scale=['#1a1a2e', '#FDB827']
                )
                fig_a.update_layout(yaxis={'categoryorder': 'total ascending'}, template="plotly_dark", height=380)
                st.plotly_chart(fig_a, use_container_width=True)

        with g_col2:
            top_dp = filtered_f.nlargest(10, 'double_plays')
            if not top_dp.empty and top_dp['double_plays'].sum() > 0:
                fig_dp = px.bar(
                    top_dp,
                    x='double_plays',
                    y='player_name',
                    orientation='h',
                    title='Top 10 — Participación en Double Plays',
                    labels={'double_plays': 'Double Plays', 'player_name': 'Jugador'},
                    color='double_plays',
                    color_continuous_scale=['#1a1a2e', '#CE1141']
                )
                fig_dp.update_layout(yaxis={'categoryorder': 'total ascending'}, template="plotly_dark", height=380)
                st.plotly_chart(fig_dp, use_container_width=True)

        # Glosario y Leyenda de Fildeo / Defensa
        with st.expander("📖 Guía y Glosario: ¿Cómo entender las Estadísticas Defensivas y de Fildeo?", expanded=False):
            st.markdown(r"""
            ### 🧤 Guía Completa de Métricas Defensivas

            | Abreviatura | Nombre Completo | ¿Qué significa y cómo se calcula? | ¿Cómo interpretarlo? |
            |---|---|---|---|
            | **PO** | Outs Realizados (Putouts) | Outs conseguidos directamente por el fildeador (atrapar un fly, pisar la base en jugada forzada, o el receptor recibiendo el 3er strike). | Los inicialistas (1B) y receptores (C) acumulan la mayor cantidad. |
            | **A** | Asistencias (Assists) | Pases o tiros realizados por el defensor que resultan en un out (ej. el tiro del shortstop al 1B). | Clave para evaluar a los defensores del cuadro interior (SS, 2B, 3B) y outfielders con brazo potente. |
            | **E** | Errores Cometidos | Jugadas fallidas que permitieron a un bateador embasarse o avanzar base debiendo ser out. | Menos es mejor; indica seguridad de manos. |
            | **TC** | Total de Lances / Oportunidades (Total Chances) | $\text{TC} = PO + A + E$. Cantidad total de jugadas defensivas en las que intervino el jugador. | Mide el volumen de actividad defensiva en su posición. |
            | **FPCT / % FLD** | Porcentaje de Fildeo (Fielding Pct) | $\text{FPCT} = \frac{PO + A}{TC}$. Proporción de jugadas completadas exitosamente sin cometer error. | **Guante de Oro / Impecable:** $1.000$ (sin errores).<br>**Excelente:** $>.980$.<br>**Vulnerable:** $<.950$ (comete muchos errores). |
            | **DP** | Dobles Matanzas (Double Plays) | Jugadas de 2 outs en las que participó el defensor. | Fundamental para intermedistas (2B) y campocortos (SS). |
            | **RF/9** | Factor de Rango por 9 Entradas | $\text{RF/9} = \frac{(PO + A) \times 9}{Inn}$. Cantidad de outs en los que participa por cada 9 innings jugados. | Mide el **alcance y cobertura de terreno** (a mayor RF/9, mayor terreno cubre el defensor). |
            | **CS** | Corredores Atrapados Robando (Caught Stealing) | Corredores puestos out por el tiro del receptor intentando robar base. | Métrica exclusiva para catchers. |
            | **SB** | Bases Robadas Permitidas | Corredores que le estafaron almohadillas al receptor y lanzador. | Menos es mejor. |
            | **CS%** | Porcentaje de Captura de Receptores | $\text{CS\%} = \frac{CS}{CS + SB}$. Porcentaje de corredores que fusiló el receptor. | **Brazo de Cañón / Élite:** $> 35.0\%$ | **Bueno:** $28.0\% - 34.0\%$ | **Vulnerable:** $< 20.0\%$ |
            | **PB** | Passed Balls | Lanzamientos normales que se le escapan al receptor permitiendo avance de corredores. | Menos es mejor. |
            """)

    else:
        st.info("🧤 No hay datos de fildeo disponibles para esta temporada.")

# ==================== TAB 3: MATCHUP 360 H2H ====================
with tab3:
    st.markdown("### ⚔️ Matchup 360 Head-to-Head (H2H)")
    st.caption("Comparativa sabermétrica multidimensional cara a cara con radar polar de 8 ejes, percentiles relativos (0-100%) y tarjeta gráfica oficial descargable en PNG (300 DPI).")

    # Controles superiores de Matchup
    ctrl_col1, ctrl_col2 = st.columns([1, 1])
    with ctrl_col1:
        m360_type = st.radio("Perfil de Jugadores", ["🏏 Bateadores", "⚾ Lanzadores"], horizontal=True, key="m360_radio_type")
        is_batter = (m360_type == "🏏 Bateadores")
    with ctrl_col2:
        sync_phases = st.checkbox("🔄 Sincronizar Fases de Campeonato", value=True, key="m360_sync_phases")

    phase_map = {
        "Temporada Regular": "R",
        "Round Robin": "L",
        "Serie Final": "F",
        "Todas las Fases": "all",
    }
    phase_labels = list(phase_map.keys())

    team_options_m360 = {
        "🌐 Toda la LVBP": None,
        "🦁 Leones del Caracas": 695,
        "⚓ Navegantes del Magallanes": 696,
        "🦈 Tiburones de La Guaira": 698,
        "🐯 Tigres de Aragua": 699,
        "🐦 Cardenales de Lara": 693,
        "🦅 Águilas del Zulia": 692,
        "🏹 Caribes de Anzoátegui": 694,
        "🏝️ Bravos de Margarita": 697,
    }

    # Selectores independientes para Jugador 1 y Jugador 2
    col_p1, col_p2 = st.columns(2)

    with col_p1:
        st.markdown("#### 🔴 Jugador 1")
        col_t1, col_ph1 = st.columns(2)
        with col_t1:
            team1_label = st.selectbox("Franquicia 1", list(team_options_m360.keys()), index=1, key="sb_m360_t1")
            team1_id = team_options_m360[team1_label]
        with col_ph1:
            phase1_label = st.selectbox("Fase 1", phase_labels, index=0, key="sb_m360_ph1")
            phase1_code = phase_map[phase1_label]

    with col_p2:
        st.markdown("#### 🔵 Jugador 2")
        col_t2, col_ph2 = st.columns(2)
        with col_t2:
            team2_label = st.selectbox("Franquicia 2", list(team_options_m360.keys()), index=0, key="sb_m360_t2")
            team2_id = team_options_m360[team2_label]
        with col_ph2:
            if sync_phases:
                phase2_label = phase1_label
                phase2_code = phase1_code
                st.selectbox("Fase 2 (Sincronizada)", [phase1_label], disabled=True, key="sb_m360_ph2_sync")
            else:
                phase2_label = st.selectbox("Fase 2", phase_labels, index=0, key="sb_m360_ph2")
                phase2_code = phase_map[phase2_label]

    # Cargar datos para cada fase
    if is_batter:
        pool_all_1 = get_batting_stats(team_id=None, limit=None, season=selected_season, phase=phase1_code)
        pool_all_2 = pool_all_1 if phase1_code == phase2_code else get_batting_stats(team_id=None, limit=None, season=selected_season, phase=phase2_code)
        
        df_p1 = pool_all_1 if team1_id is None else pool_all_1[pool_all_1['team_id'] == team1_id]
        df_p2 = pool_all_2 if team2_id is None else pool_all_2[pool_all_2['team_id'] == team2_id]
    else:
        pool_all_1 = get_pitching_stats(team_id=None, limit=None, season=selected_season, phase=phase1_code)
        pool_all_2 = pool_all_1 if phase1_code == phase2_code else get_pitching_stats(team_id=None, limit=None, season=selected_season, phase=phase2_code)

        df_p1 = pool_all_1 if team1_id is None else pool_all_1[pool_all_1['team_id'] == team1_id]
        df_p2 = pool_all_2 if team2_id is None else pool_all_2[pool_all_2['team_id'] == team2_id]

    # Selectboxes para los jugadores
    with col_p1:
        if not df_p1.empty:
            p1_names = df_p1['player_name'].unique().tolist()
            sel_player_1 = st.selectbox("Seleccionar Jugador 1", p1_names, index=0, key="sb_m360_p1")
            row1 = df_p1[df_p1['player_name'] == sel_player_1].iloc[0].to_dict()
        else:
            st.warning("No hay datos para esta franquicia/fase.")
            row1 = {}

    with col_p2:
        if not df_p2.empty:
            p2_names = df_p2['player_name'].unique().tolist()
            default_p2_idx = 1 if len(p2_names) > 1 and p2_names[0] == row1.get('player_name') else 0
            sel_player_2 = st.selectbox("Seleccionar Jugador 2", p2_names, index=default_p2_idx, key="sb_m360_p2")
            row2 = df_p2[df_p2['player_name'] == sel_player_2].iloc[0].to_dict()
        else:
            st.warning("No hay datos para esta franquicia/fase.")
            row2 = {}

    if row1 and row2:
        st.markdown("---")
        # Computar Percentiles Sabermétricos (8 ejes)
        if is_batter:
            axes = [
                ("Contacto (AVG)", "avg", True),
                ("Embasado (OBP)", "obp", True),
                ("Poder (SLG)", "slg", True),
                ("Producción (OPS)", "ops", True),
                ("wOBA", "woba", True),
                ("wRC+", "wrc_plus", True),
                ("Extrabases (ISO)", "iso", True),
                ("Paciencia (BB%)", "bb_pct", True),
            ]
            for r in [row1, row2]:
                ab_val = r.get("ab", 0)
                h_val = r.get("h", 0)
                bb_val = r.get("bb", 0)
                d_val = r.get("doubles", 0)
                t_val = r.get("triples", 0)
                hr_val = r.get("hr", 0)
                singles = max(0, h_val - d_val - t_val - hr_val)
                tb = singles + 2*d_val + 3*t_val + 4*hr_val
                r["iso"] = round((tb - h_val) / ab_val, 3) if ab_val > 0 else 0.0
                pa = ab_val + bb_val + r.get("hbp", 0) + r.get("sf", 0)
                r["bb_pct"] = round((bb_val / pa) * 100, 1) if pa > 0 else 0.0
                woba_val = (0.69*bb_val + 0.89*singles + 1.27*d_val + 1.62*t_val + 2.10*hr_val) / pa if pa > 0 else 0.0
                r["woba"] = round(woba_val, 3)
                r["wrc_plus"] = int(max(20, min(220, round(100 + (woba_val - 0.320) / 0.320 * 100)))) if pa > 0 else 100

            pool1 = pool_all_1[pool_all_1['ab'] >= 5].to_dict('records') or pool_all_1.to_dict('records')
            pool2 = pool_all_2[pool_all_2['ab'] >= 5].to_dict('records') or pool_all_2.to_dict('records')

            for p_item in pool1 + pool2:
                ab_v = p_item.get("ab", 0)
                h_v = p_item.get("h", 0)
                bb_v = p_item.get("bb", 0)
                d_v = p_item.get("doubles", 0)
                t_v = p_item.get("triples", 0)
                hr_v = p_item.get("hr", 0)
                s_v = max(0, h_v - d_v - t_v - hr_v)
                tb_v = s_v + 2*d_v + 3*t_v + 4*hr_v
                p_item["iso"] = round((tb_v - h_v) / ab_v, 3) if ab_v > 0 else 0.0
                pa_v = ab_v + bb_v + p_item.get("hbp", 0) + p_item.get("sf", 0)
                p_item["bb_pct"] = round((bb_v / pa_v) * 100, 1) if pa_v > 0 else 0.0
                woba_v = (0.69*bb_v + 0.89*s_v + 1.27*d_v + 1.62*t_v + 2.10*hr_v) / pa_v if pa_v > 0 else 0.0
                p_item["woba"] = round(woba_v, 3)
                p_item["wrc_plus"] = int(max(20, min(220, round(100 + (woba_v - 0.320) / 0.320 * 100)))) if pa_v > 0 else 100

        else:
            axes = [
                ("Efectividad (ERA)", "era", False),
                ("Control (WHIP)", "whip", False),
                ("FIP Independiente", "fip", False),
                ("Dominio (K/9)", "k9", True),
                ("Comando (BB/9)", "bb9", False),
                ("Relación K/BB", "k_bb", True),
                ("Innings (IP)", "ip", True),
                ("Ponches (SO)", "so", True),
            ]
            for r in [row1, row2]:
                ip_v = float(r.get("ip", 0.0))
                so_v = float(r.get("so", 0))
                bb_v = float(r.get("bb", 0))
                hr_v = float(r.get("hr", 0))
                r["k9"] = round((so_v * 9.0) / ip_v, 2) if ip_v > 0 else 0.0
                r["bb9"] = round((bb_v * 9.0) / ip_v, 2) if ip_v > 0 else 0.0
                r["k_bb"] = round(so_v / bb_v, 2) if bb_v > 0 else (round(so_v, 2) if so_v > 0 else 1.0)
                r["fip"] = round(((13*hr_v + 3*bb_v - 2*so_v) / ip_v) + 3.80, 2) if ip_v > 0 else 4.50

            pool1 = pool_all_1[pool_all_1['ip'] >= 2.0].to_dict('records') or pool_all_1.to_dict('records')
            pool2 = pool_all_2[pool_all_2['ip'] >= 2.0].to_dict('records') or pool_all_2.to_dict('records')

            for p_item in pool1 + pool2:
                ip_v = float(p_item.get("ip", 0.0))
                so_v = float(p_item.get("so", 0))
                bb_v = float(p_item.get("bb", 0))
                hr_v = float(p_item.get("hr", 0))
                p_item["k9"] = round((so_v * 9.0) / ip_v, 2) if ip_v > 0 else 0.0
                p_item["bb9"] = round((bb_v * 9.0) / ip_v, 2) if ip_v > 0 else 0.0
                p_item["k_bb"] = round(so_v / bb_v, 2) if bb_v > 0 else (round(so_v, 2) if so_v > 0 else 1.0)
                p_item["fip"] = round(((13*hr_v + 3*bb_v - 2*so_v) / ip_v) + 3.80, 2) if ip_v > 0 else 4.50

        def _get_pct(val, key, higher_better, pool):
            vals = [float(x.get(key, 0.0) or 0.0) for x in pool]
            if not vals:
                return 50
            if higher_better:
                return min(100, max(5, int((sum(1 for v in vals if v <= val) / len(vals)) * 100)))
            else:
                return min(100, max(5, int((sum(1 for v in vals if v >= val) / len(vals)) * 100)))

        r1_pcts = [_get_pct(float(row1.get(k, 0.0) or 0.0), k, hb, pool1) for _, k, hb in axes]
        r2_pcts = [_get_pct(float(row2.get(k, 0.0) or 0.0), k, hb, pool2) for _, k, hb in axes]
        theta_names = [a[0] for a in axes]

        # Comparativa y líder por métrica
        h2h_rows = []
        p1_wins = 0
        p2_wins = 0
        for i, (name, key, hb) in enumerate(axes):
            pct1 = r1_pcts[i]
            pct2 = r2_pcts[i]
            v1_raw = row1.get(key, 0)
            v2_raw = row2.get(key, 0)
            if pct1 > pct2:
                leader = f"{row1['player_name']} ({row1.get('team_abbr', 'CAR')})"
                p1_wins += 1
            elif pct2 > pct1:
                leader = f"{row2['player_name']} ({row2.get('team_abbr', 'LVBP')})"
                p2_wins += 1
            else:
                leader = "Empate"

            h2h_rows.append({
                "metric": name,
                "val_1": f"{v1_raw:.3f}" if isinstance(v1_raw, float) else str(v1_raw),
                "pct_1": pct1,
                "pct_1_str": f"P{pct1}",
                "val_2": f"{v2_raw:.3f}" if isinstance(v2_raw, float) else str(v2_raw),
                "pct_2": pct2,
                "pct_2_str": f"P{pct2}",
                "leader": leader,
            })

        # Banner de Veredicto
        if p1_wins > p2_wins:
            st.success(f"🏆 **Veredicto Sabermétrico:** **{row1['player_name']}** domina **{p1_wins} de {len(axes)}** dimensiones frente a **{row2['player_name']}**.")
        elif p2_wins > p1_wins:
            st.info(f"🏆 **Veredicto Sabermétrico:** **{row2['player_name']}** domina **{p2_wins} de {len(axes)}** dimensiones frente a **{row1['player_name']}**.")
        else:
            st.warning(f"🤝 **Veredicto Sabermétrico:** **Empate técnico total** ({p1_wins} a {p2_wins}) en las 8 dimensiones sabermétricas.")

        # Radar Polar y Tabla Comparativa
        col_radar, col_tbl = st.columns([1, 1])

        with col_radar:
            fig_rad = go.Figure()
            r1_closed = r1_pcts + [r1_pcts[0]]
            r2_closed = r2_pcts + [r2_pcts[0]]
            theta_closed = theta_names + [theta_names[0]]

            fig_rad.add_trace(go.Scatterpolar(
                r=r1_closed,
                theta=theta_closed,
                fill='toself',
                name=f"🔴 {row1['player_name']} ({row1.get('team_abbr', 'CAR')})",
                line=dict(color="#FDB827", width=2.5),
                fillcolor="rgba(253, 184, 39, 0.25)",
            ))
            fig_rad.add_trace(go.Scatterpolar(
                r=r2_closed,
                theta=theta_closed,
                fill='toself',
                name=f"🔵 {row2['player_name']} ({row2.get('team_abbr', 'LVBP')})",
                line=dict(color="#3B82F6", width=2.5),
                fillcolor="rgba(59, 130, 246, 0.25)",
            ))
            fig_rad.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=10, color="#94A3B8"), gridcolor="rgba(255,255,255,0.1)"),
                    angularaxis=dict(tickfont=dict(size=11, color="#F8FAFC", family="Inter, sans-serif"), gridcolor="rgba(255,255,255,0.1)"),
                    bgcolor="#0D152B"
                ),
                paper_bgcolor="#070B19",
                font=dict(color="#94A3B8"),
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
                height=450,
                margin=dict(l=40, r=40, t=60, b=40)
            )
            st.plotly_chart(fig_rad, use_container_width=True)

        with col_tbl:
            st.markdown("##### 📊 Desglose de Percentiles Relativos:")
            df_comp_display = pd.DataFrame(h2h_rows)[["metric", "val_1", "pct_1_str", "val_2", "pct_2_str", "leader"]]
            df_comp_display.columns = [
                "Dimensión",
                f"{row1['player_name']} (Valor)",
                "Percentil J1",
                f"{row2['player_name']} (Valor)",
                "Percentil J2",
                "Líder"
            ]
            st.dataframe(df_comp_display, use_container_width=True, hide_index=True)

        # Generador y Descarga de Tarjeta Matchup 360 HD (300 DPI)
        st.markdown("---")
        st.markdown("##### 🖼️ Tarjeta Matchup 360 en Alta Resolución (PNG 300 DPI)")
        p1_for_card = {
            "name": row1['player_name'],
            "team": row1.get('team_name', 'Leones del Caracas'),
            "team_abbr": row1.get('team_abbr', 'CAR'),
            "photo_url": f"https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current/w_213,q_auto:best/v1/people/{row1.get('player_id', 0)}/headshot/67/current",
            "phase": phase1_label,
            "color_hex": "#FDB827",
        }
        p2_for_card = {
            "name": row2['player_name'],
            "team": row2.get('team_name', 'Equipo LVBP'),
            "team_abbr": row2.get('team_abbr', 'LVBP'),
            "photo_url": f"https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current/w_213,q_auto:best/v1/people/{row2.get('player_id', 0)}/headshot/67/current",
            "phase": phase2_label,
            "color_hex": "#3B82F6",
        }

        with st.spinner("Construyendo tarjeta gráfica HD..."):
            try:
                card_png_bytes = build_matchup_image(
                    player_1=p1_for_card,
                    player_2=p2_for_card,
                    h2h_rows=h2h_rows,
                    is_batter=is_batter,
                    season=selected_season,
                    phase=phase1_label,
                    phase_1=phase1_label,
                    phase_2=phase2_label,
                    scale=2.0
                )
            except Exception as e:
                card_png_bytes = None

        if card_png_bytes:
            st.image(card_png_bytes, use_container_width=True)
            safe_n1 = "".join(c for c in row1['player_name'] if c.isalnum() or c == "_")
            safe_n2 = "".join(c for c in row2['player_name'] if c.isalnum() or c == "_")
            st.download_button(
                "📥 Descargar Tarjeta Matchup 360 (PNG 300 DPI)",
                data=card_png_bytes,
                file_name=f"Matchup360_{safe_n1}_vs_{safe_n2}_{selected_season}.png",
                mime="image/png",
                use_container_width=True,
                key="btn_dl_m360"
            )

    st.markdown("---")

    # Análisis de equipo (Resumen General Preservado)
    st.markdown("#### 🦁 Análisis General del Equipo")
    analysis_col1, analysis_col2 = st.columns(2)

    with analysis_col1:
        st.markdown("##### 🏏 Resumen Ofensivo")
        if not batting_df.empty:
            total_hr = batting_df['hr'].sum() if 'hr' in batting_df.columns else 0
            total_rbi = batting_df['rbi'].sum() if 'rbi' in batting_df.columns else 0
            total_h = batting_df['h'].sum() if 'h' in batting_df.columns else 0
            total_ab = batting_df['ab'].sum() if 'ab' in batting_df.columns else 0
            team_avg = (total_h / total_ab) if total_ab > 0 else 0.0

            metric_col1, metric_col2 = st.columns(2)
            with metric_col1:
                st.metric("Total HR", int(total_hr))
                st.metric("Total Hits", int(total_h))
            with metric_col2:
                st.metric("Total RBI", int(total_rbi))
                st.metric("AVG Equipo", f"{team_avg:.3f}")

    with analysis_col2:
        st.markdown("##### ⚾ Resumen de Pitcheo")
        if not pitching_df.empty:
            total_ip = pitching_df['ip'].sum() if 'ip' in pitching_df.columns else 0.0
            total_er = pitching_df['er'].sum() if 'er' in pitching_df.columns else 0
            total_p_h = pitching_df['h'].sum() if 'h' in pitching_df.columns else 0
            total_p_bb = pitching_df['bb'].sum() if 'bb' in pitching_df.columns else 0
            total_so = pitching_df['so'].sum() if 'so' in pitching_df.columns else 0
            total_wins = pitching_df['w'].sum() if 'w' in pitching_df.columns else 0

            team_era = ((total_er * 9.0) / total_ip) if total_ip > 0 else 0.0
            team_whip = ((total_p_h + total_p_bb) / total_ip) if total_ip > 0 else 0.0

            metric_col1, metric_col2 = st.columns(2)
            with metric_col1:
                st.metric("ERA Equipo", f"{team_era:.2f}")
                st.metric("Total Ponches", int(total_so))
            with metric_col2:
                st.metric("Total Victorias", int(total_wins))
                st.metric("WHIP Equipo", f"{team_whip:.2f}")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #94A3B8; padding: 1rem;'>
    <p>📊 Estadísticas actualizadas diariamente | 🦁 Leones del Caracas - LVBP</p>
    <p style='font-size: 0.8rem;'>Los datos se sincronizan automáticamente con la base de datos</p>
</div>
""", unsafe_allow_html=True)

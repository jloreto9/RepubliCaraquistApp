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
try:
    from utils.supabase_client import (
        get_batting_stats,
        get_pitching_stats,
        get_current_season,
        get_available_seasons,
        init_supabase
    )
except:
    from streamlit_app.utils.supabase_client import (
        get_batting_stats,
        get_pitching_stats,
        get_current_season,
        get_available_seasons,
        init_supabase
    )

st.set_page_config(page_title="Estadísticas Individuales - RepubliCaraquistApp", page_icon="⚾", layout="wide")

# Colores de los Leones
LEONES_GOLD = "#FDB827"
LEONES_RED = "#CE1141"

# Header
st.title("⚾ Estadísticas Individuales")
st.markdown("### Líderes de Bateo y Pitcheo - Leones del Caracas")

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
        display_text = f"{season-1}-{season}"
        season_options[display_text] = season

    selected_season_display = st.selectbox(
        "⚾ Seleccionar Temporada",
        options=list(season_options.keys()),
        index=0
    )

    selected_season = season_options[selected_season_display]

# Tabs principales
tab1, tab2, tab3 = st.tabs(["🏏 Bateo", "⚾ Pitcheo", "📊 Comparaciones"])

# ==================== TAB 1: BATEO ====================
with tab1:
    st.markdown("### 🏏 Estadísticas de Bateo")

    # Obtener datos de bateo
    batting_df = get_batting_stats(team_id=695, limit=100)

    if not batting_df.empty:
        # Calcular estadísticas adicionales si no existen
        if 'avg' not in batting_df.columns and 'ab' in batting_df.columns and 'h' in batting_df.columns:
            batting_df['avg'] = batting_df.apply(
                lambda x: round(x['h'] / x['ab'], 3) if x['ab'] > 0 else 0.000,
                axis=1
            )

        if 'obp' not in batting_df.columns:
            batting_df['obp'] = batting_df.apply(
                lambda x: round((x['h'] + x.get('bb', 0)) / (x['ab'] + x.get('bb', 0)), 3)
                if (x['ab'] + x.get('bb', 0)) > 0 else 0.000,
                axis=1
            )

        if 'slg' not in batting_df.columns:
            batting_df['slg'] = batting_df.apply(
                lambda x: round((x['h'] + x.get('doubles', 0) + 2*x.get('triples', 0) + 3*x.get('hr', 0)) / x['ab'], 3)
                if x['ab'] > 0 else 0.000,
                axis=1
            )

        if 'ops' not in batting_df.columns:
            batting_df['ops'] = (batting_df['obp'] + batting_df['slg']).round(3)

        # Extraer nombre del jugador si está en formato nested
        if 'players' in batting_df.columns:
            batting_df['player_name'] = batting_df['players'].apply(
                lambda x: x.get('full_name', 'N/A') if isinstance(x, dict) else 'N/A'
            )
        elif 'player_name' not in batting_df.columns:
            batting_df['player_name'] = 'Jugador ' + batting_df.index.astype(str)

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
                st.metric(
                    "AVG Líder",
                    f".{int(top_avg['avg']*1000):03d}",
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

    # Obtener datos de pitcheo
    pitching_df = get_pitching_stats(team_id=695, limit=100)

    if not pitching_df.empty:
        # Calcular estadísticas adicionales si no existen
        if 'era' not in pitching_df.columns and 'er' in pitching_df.columns and 'ip' in pitching_df.columns:
            pitching_df['era'] = pitching_df.apply(
                lambda x: round((x['er'] * 9) / x['ip'], 2) if x['ip'] > 0 else 0.00,
                axis=1
            )

        if 'whip' not in pitching_df.columns:
            pitching_df['whip'] = pitching_df.apply(
                lambda x: round((x.get('h', 0) + x.get('bb', 0)) / x['ip'], 2) if x['ip'] > 0 else 0.00,
                axis=1
            )

        # Extraer nombre del jugador
        if 'players' in pitching_df.columns:
            pitching_df['player_name'] = pitching_df['players'].apply(
                lambda x: x.get('full_name', 'N/A') if isinstance(x, dict) else 'N/A'
            )
        elif 'player_name' not in pitching_df.columns:
            pitching_df['player_name'] = 'Lanzador ' + pitching_df.index.astype(str)

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

# ==================== TAB 3: COMPARACIONES ====================
with tab3:
    st.markdown("### 📊 Comparaciones y Análisis")

    # Verificar si hay datos
    batting_df = get_batting_stats(team_id=695, limit=100)
    pitching_df = get_pitching_stats(team_id=695, limit=100)

    if not batting_df.empty and not pitching_df.empty:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### ⚔️ Comparar Bateadores")

            # Extraer nombres de jugadores
            if 'players' in batting_df.columns:
                batting_df['player_name'] = batting_df['players'].apply(
                    lambda x: x.get('full_name', 'N/A') if isinstance(x, dict) else 'N/A'
                )

            player_names = batting_df['player_name'].unique().tolist()

            selected_batters = st.multiselect(
                "Seleccionar bateadores (2-5)",
                options=player_names,
                max_selections=5
            )

            if len(selected_batters) >= 2:
                # Filtrar datos
                comparison_df = batting_df[batting_df['player_name'].isin(selected_batters)]

                # Preparar datos para comparación
                metrics = ['avg', 'hr', 'rbi', 'ops']
                available_metrics = [m for m in metrics if m in comparison_df.columns]

                if available_metrics:
                    # Gráfico de radar
                    fig_radar = go.Figure()

                    for player in selected_batters:
                        player_data = comparison_df[comparison_df['player_name'] == player].iloc[0]
                        values = [player_data.get(m, 0) for m in available_metrics]

                        fig_radar.add_trace(go.Scatterpolar(
                            r=values,
                            theta=[m.upper() for m in available_metrics],
                            fill='toself',
                            name=player
                        ))

                    fig_radar.update_layout(
                        polar=dict(radialaxis=dict(visible=True)),
                        showlegend=True,
                        title="Comparación de Bateadores",
                        height=400
                    )

                    st.plotly_chart(fig_radar, use_container_width=True)

                    # Tabla comparativa
                    st.markdown("##### Tabla Comparativa")
                    compare_cols = ['player_name', 'ab', 'h', 'avg', 'hr', 'rbi', 'ops']
                    available_compare = [c for c in compare_cols if c in comparison_df.columns]
                    st.dataframe(
                        comparison_df[available_compare],
                        use_container_width=True,
                        hide_index=True
                    )

        with col2:
            st.markdown("#### ⚔️ Comparar Lanzadores")

            # Extraer nombres de lanzadores
            if 'players' in pitching_df.columns:
                pitching_df['player_name'] = pitching_df['players'].apply(
                    lambda x: x.get('full_name', 'N/A') if isinstance(x, dict) else 'N/A'
                )

            pitcher_names = pitching_df['player_name'].unique().tolist()

            selected_pitchers = st.multiselect(
                "Seleccionar lanzadores (2-5)",
                options=pitcher_names,
                max_selections=5
            )

            if len(selected_pitchers) >= 2:
                # Filtrar datos
                comparison_df_p = pitching_df[pitching_df['player_name'].isin(selected_pitchers)]

                # Preparar datos
                metrics_p = ['w', 'so', 'ip']
                available_metrics_p = [m for m in metrics_p if m in comparison_df_p.columns]

                if available_metrics_p:
                    # Gráfico de radar
                    fig_radar_p = go.Figure()

                    for pitcher in selected_pitchers:
                        pitcher_data = comparison_df_p[comparison_df_p['player_name'] == pitcher].iloc[0]
                        values_p = [pitcher_data.get(m, 0) for m in available_metrics_p]

                        fig_radar_p.add_trace(go.Scatterpolar(
                            r=values_p,
                            theta=[m.upper() for m in available_metrics_p],
                            fill='toself',
                            name=pitcher
                        ))

                    fig_radar_p.update_layout(
                        polar=dict(radialaxis=dict(visible=True)),
                        showlegend=True,
                        title="Comparación de Lanzadores",
                        height=400
                    )

                    st.plotly_chart(fig_radar_p, use_container_width=True)

                    # Tabla comparativa
                    st.markdown("##### Tabla Comparativa")
                    compare_cols_p = ['player_name', 'w', 'l', 'era', 'so', 'ip', 'whip']
                    available_compare_p = [c for c in compare_cols_p if c in comparison_df_p.columns]
                    st.dataframe(
                        comparison_df_p[available_compare_p],
                        use_container_width=True,
                        hide_index=True
                    )

        st.markdown("---")

        # Análisis de equipo
        st.markdown("#### 🦁 Análisis General del Equipo")

        analysis_col1, analysis_col2 = st.columns(2)

        with analysis_col1:
            st.markdown("##### 🏏 Resumen Ofensivo")
            if not batting_df.empty:
                total_hr = batting_df['hr'].sum() if 'hr' in batting_df.columns else 0
                total_rbi = batting_df['rbi'].sum() if 'rbi' in batting_df.columns else 0
                total_h = batting_df['h'].sum() if 'h' in batting_df.columns else 0
                team_avg = batting_df['avg'].mean() if 'avg' in batting_df.columns else 0

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
                team_era = pitching_df['era'].mean() if 'era' in pitching_df.columns else 0
                total_so = pitching_df['so'].sum() if 'so' in pitching_df.columns else 0
                total_wins = pitching_df['w'].sum() if 'w' in pitching_df.columns else 0
                team_whip = pitching_df['whip'].mean() if 'whip' in pitching_df.columns else 0

                metric_col1, metric_col2 = st.columns(2)
                with metric_col1:
                    st.metric("ERA Equipo", f"{team_era:.2f}")
                    st.metric("Total Ponches", int(total_so))
                with metric_col2:
                    st.metric("Total Victorias", int(total_wins))
                    st.metric("WHIP Equipo", f"{team_whip:.2f}")

    else:
        st.info("📊 Se necesitan datos de bateo y pitcheo para realizar comparaciones.")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p>📊 Estadísticas actualizadas diariamente | 🦁 Leones del Caracas - LVBP</p>
    <p style='font-size: 0.8rem;'>Los datos se sincronizan automáticamente con la base de datos</p>
</div>
""", unsafe_allow_html=True)

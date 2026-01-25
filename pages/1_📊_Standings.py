# pages/Standings.py
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
    from utils.supabase_client import get_standings, get_recent_games, init_supabase, get_available_seasons, get_current_season
except:
    from streamlit_app.utils.supabase_client import get_standings, get_recent_games, init_supabase, get_available_seasons, get_current_season

st.set_page_config(page_title="Standings - RepubliCaraquistApp", page_icon="📊", layout="wide")

# Header
st.title("📊 Standings y Resultados")

# Selector de temporada
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    # Obtener temporadas disponibles
    current_season = get_current_season()
    available_seasons = get_available_seasons()

    if not available_seasons:
        available_seasons = [current_season]

    # Crear diccionario para el selector con formato legible
    season_options = {}
    for season in available_seasons:
        display_text = f"{season-1}-{season}"
        season_options[display_text] = season

    # Determinar índice de la temporada actual
    current_season_display = f"{current_season-1}-{current_season}"
    season_list = list(season_options.keys())
    default_index = season_list.index(current_season_display) if current_season_display in season_list else 0

    # Selector de temporada
    selected_season_display = st.selectbox(
        "⚾ Seleccionar Temporada",
        options=season_list,
        index=default_index
    )

    selected_season = season_options[selected_season_display]
    st.markdown(f"### Tabla de Posiciones - LVBP {selected_season_display}")

# IDs de los 8 equipos LVBP
LVBP_TEAMS = {
    695: "Leones del Caracas",
    698: "Tiburones de La Guaira", 
    696: "Navegantes del Magallanes",
    699: "Tigres de Aragua",
    692: "Águilas del Zulia",
    693: "Cardenales de Lara",
    694: "Caribes de Anzoátegui",
    697: "Bravos de Margarita"
}

# Obtener standings
standings_df = get_standings(selected_season)

if not standings_df.empty:
    # Filtrar solo equipos LVBP
    standings_df = standings_df[standings_df['team_id'].isin(LVBP_TEAMS.keys())]
    
    # Si no hay datos para estos equipos, intentar por nombre
    if standings_df.empty:
        standings_df = get_standings(selected_season)
        lvbp_names = list(LVBP_TEAMS.values())
        standings_df = standings_df[standings_df['team_name'].str.contains('|'.join([
            'Leones', 'Tiburones', 'Navegantes', 'Tigres', 
            'Águilas', 'Cardenales', 'Caribes', 'Bravos'
        ]), case=False, na=False)]
    
    # Limitar a 8 equipos máximo
    standings_df = standings_df.head(8)
    
    # Recalcular games back con solo estos equipos
    if not standings_df.empty:
        standings_df = standings_df.sort_values('pct', ascending=False).reset_index(drop=True)
        leader_wins = standings_df.iloc[0]['wins']
        leader_losses = standings_df.iloc[0]['losses']
        
        standings_df['games_back'] = standings_df.apply(
            lambda x: ((leader_wins - x['wins']) + (x['losses'] - leader_losses)) / 2,
            axis=1
        )
    
    # Tabs para diferentes vistas
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Tabla General", "📈 Gráficos", "🆚 Head to Head", "📅 Calendario"])
    
    with tab1:
        # Formatear tabla de posiciones
        display_df = standings_df.copy()
        
        # Agregar posición
        display_df.insert(0, 'Pos', range(1, len(display_df) + 1))
        
        # Seleccionar y renombrar columnas
        columns_to_show = {
            'Pos': '#',
            'team_name': 'Equipo',
            'wins': 'G',
            'losses': 'P',
            'pct': 'PCT',
            'games_back': 'JD',
            'home_record': 'Local',
            'away_record': 'Visitante',
            'runs_for': 'CF',
            'runs_against': 'CP',
            'run_diff': 'DIF',
            'last_10': 'Últimos 10',
            'streak': 'Racha'
        }
        
        # Filtrar columnas que existen
        available_cols = [col for col in columns_to_show.keys() if col in display_df.columns]
        display_df = display_df[available_cols]
        display_df.columns = [columns_to_show[col] for col in available_cols]
        
        # Formatear PCT
        if 'PCT' in display_df.columns:
            display_df['PCT'] = display_df['PCT'].apply(lambda x: f'.{int(x*1000):03d}' if pd.notna(x) else '.000')
        
        # Formatear JD
        if 'JD' in display_df.columns:
            display_df['JD'] = display_df['JD'].apply(lambda x: '-' if x == 0 else f'{x:.1f}')
        
        # Formatear DIF con color
        if 'DIF' in display_df.columns:
            display_df['DIF'] = display_df['DIF'].apply(lambda x: f"{x:+d}" if x != 0 else "0")
        
        # Resaltar Leones del Caracas
        def highlight_leones(row):
            if 'Leones' in str(row.get('Equipo', '')):
                return ['background-color: #FDB827; color: #CE1141; font-weight: bold'] * len(row)
            return [''] * len(row)
        
        # Aplicar estilos
        styled_df = display_df.style.apply(highlight_leones, axis=1)
        
        # Colorear diferencial
        if 'DIF' in display_df.columns:
            def color_diff(val):
                try:
                    num = int(val)
                    if num > 0:
                        return 'color: green'
                    elif num < 0:
                        return 'color: red'
                except:
                    pass
                return ''
            
            styled_df = styled_df.applymap(color_diff, subset=['DIF'])
        
        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True,
            height=350
        )
        
        # Métricas de los Leones
        st.markdown("---")
        st.markdown("### 🦁 Resumen - Leones del Caracas")
        
        leones_data = standings_df[standings_df['team_name'].str.contains('Leones', case=False, na=False)]
        
        if not leones_data.empty:
            leones = leones_data.iloc[0]
            position = standings_df.index[standings_df['team_name'] == leones['team_name']].tolist()[0] + 1
            
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric("🏆 Posición", f"{position}° / 8")
            
            with col2:
                st.metric("📊 Récord", f"{int(leones['wins'])}-{int(leones['losses'])}")
            
            with col3:
                pct = leones.get('pct', 0)
                st.metric("📈 Porcentaje", f".{int(pct*1000):03d}")
            
            with col4:
                gb = leones.get('games_back', 0)
                st.metric("📏 Juegos Detrás", f"{gb:.1f}" if gb > 0 else "Líder")
            
            with col5:
                diff = leones.get('run_diff', 0)
                st.metric("🎯 Diferencial", f"{diff:+d}")
        else:
            st.info("No hay datos de los Leones del Caracas para esta temporada")
    
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de victorias vs derrotas
            fig_wins = px.bar(
                standings_df,
                x='team_name',
                y=['wins', 'losses'],
                title=f'Victorias vs Derrotas - {selected_season_display}',
                labels={'value': 'Juegos', 'team_name': ''},
                color_discrete_map={'wins': '#196F3D', 'losses': '#922B21'},
                barmode='group'
            )
            fig_wins.update_layout(
                xaxis_tickangle=45,
                height=400,
                showlegend=True,
                legend_title_text='',
                xaxis_title="",
                yaxis_title="Juegos"
            )
            st.plotly_chart(fig_wins, use_container_width=True)
        
        with col2:
            # Gráfico de diferencial de carreras
            standings_df_sorted = standings_df.sort_values('run_diff', ascending=True)
            
            fig_diff = px.bar(
                standings_df_sorted,
                x='run_diff',
                y='team_name',
                orientation='h',
                title=f'Diferencial de Carreras - {selected_season_display}',
                labels={'run_diff': 'Diferencial', 'team_name': ''},
                color='run_diff',
                color_continuous_scale=['red', 'yellow', 'green']
            )
            fig_diff.update_layout(
                height=400,
                showlegend=False,
                xaxis_title="Diferencial",
                yaxis_title=""
            )
            st.plotly_chart(fig_diff, use_container_width=True)
        
        # Gráfico de porcentaje de victorias
        fig_pct = px.line(
            standings_df,
            x=range(1, len(standings_df) + 1),
            y='pct',
            title=f'Porcentaje de Victorias por Posición - {selected_season_display}',
            markers=True
        )
        
        # Usar update_layout para TODAS las actualizaciones
        fig_pct.update_layout(
            xaxis_title='Posición',
            yaxis_title='PCT',
            yaxis_tickformat='.3f',
            height=350
        )
        
        # Agregar nombres de equipos
        for i, row in standings_df.iterrows():
            fig_pct.add_annotation(
                x=i+1,
                y=row['pct'],
                text=row['team_name'].split()[-1],
                showarrow=False,
                yshift=10
            )
        
        st.plotly_chart(fig_pct, use_container_width=True)
    
    with tab3:
        st.markdown(f"### 🆚 Récord Head to Head - Leones del Caracas ({selected_season_display})")
        
        # Obtener juegos de los Leones
        supabase = init_supabase()
        
        # IDs CORRECTOS de los equipos LVBP
        LVBP_TEAMS = {
            695: "Leones del Caracas",
            698: "Tiburones de La Guaira", 
            696: "Navegantes del Magallanes",
            699: "Tigres de Aragua",
            692: "Águilas del Zulia",
            693: "Cardenales de Lara",
            694: "Caribes de Anzoátegui",
            697: "Bravos de Margarita"
        }
        
        LEONES_ID = 695
        
        try:
            # Obtener todos los juegos de los Leones en la temporada - INCLUIR 'Final' y 'Completed Early'
            games_response = supabase.table('games') \
                .select('*') \
                .eq('season', selected_season) \
                .in_('status', ['Final', 'Completed Early']) \
                .or_(f'home_team_id.eq.{LEONES_ID},away_team_id.eq.{LEONES_ID}') \
                .execute()
            
            if games_response.data:
                games_df = pd.DataFrame(games_response.data)
                
                # Calcular récord contra cada equipo
                h2h_data = []
                
                for team_id, team_name in LVBP_TEAMS.items():
                    if team_id == LEONES_ID:
                        continue  # Saltar Leones vs Leones
                    
                    # Filtrar juegos contra este equipo
                    vs_team = games_df[
                        ((games_df['home_team_id'] == LEONES_ID) & (games_df['away_team_id'] == team_id)) |
                        ((games_df['away_team_id'] == LEONES_ID) & (games_df['home_team_id'] == team_id))
                    ]
                    
                    if len(vs_team) == 0:
                        # Nombre corto del equipo
                        short_name = team_name.replace(' del ', ' ').replace(' de ', ' ')
                        if 'Tiburones' in short_name:
                            short_name = 'Tiburones'
                        elif 'Navegantes' in short_name:
                            short_name = 'Magallanes'
                        elif 'Tigres' in short_name:
                            short_name = 'Tigres'
                        elif 'Águilas' in short_name:
                            short_name = 'Águilas'
                        elif 'Cardenales' in short_name:
                            short_name = 'Cardenales'
                        elif 'Caribes' in short_name:
                            short_name = 'Caribes'
                        elif 'Bravos' in short_name:
                            short_name = 'Margarita'
                        
                        h2h_data.append({
                            'Rival': short_name,
                            'JJ': 0,
                            'G': 0,
                            'P': 0,
                            'PCT': '.000',
                            'Local': '0-0',
                            'Visitante': '0-0',
                            'CF': 0,
                            'CP': 0,
                            'DIF': 0,
                            'Última': '-'
                        })
                        continue
                    
                    # Calcular estadísticas
                    total_games = 0
                    total_wins = 0
                    total_losses = 0
                    home_wins = 0
                    home_losses = 0
                    away_wins = 0
                    away_losses = 0
                    runs_for = 0
                    runs_against = 0
                    
                    for _, game in vs_team.iterrows():
                        total_games += 1
                        
                        if game['home_team_id'] == LEONES_ID:
                            # Leones jugando de local
                            runs_for += game['home_score'] or 0
                            runs_against += game['away_score'] or 0
                            
                            if game['home_score'] > game['away_score']:
                                total_wins += 1
                                home_wins += 1
                            else:
                                total_losses += 1
                                home_losses += 1
                        else:
                            # Leones jugando de visitante
                            runs_for += game['away_score'] or 0
                            runs_against += game['home_score'] or 0
                            
                            if game['away_score'] > game['home_score']:
                                total_wins += 1
                                away_wins += 1
                            else:
                                total_losses += 1
                                away_losses += 1
                    
                    # Último juego
                    last_game = vs_team.sort_values('game_date').iloc[-1]
                    if last_game['home_team_id'] == LEONES_ID:
                        last_result = 'V' if last_game['home_score'] > last_game['away_score'] else 'D'
                        last_score = f"{last_game['home_score']}-{last_game['away_score']}"
                    else:
                        last_result = 'V' if last_game['away_score'] > last_game['home_score'] else 'D'
                        last_score = f"{last_game['away_score']}-{last_game['home_score']}"
                    
                    try:
                        last_date = pd.to_datetime(last_game['game_date']).strftime('%d/%m')
                    except:
                        last_date = ''
                    
                    # Calcular PCT
                    pct = total_wins / total_games if total_games > 0 else 0
                    
                    # Nombre corto del equipo
                    short_name = team_name.replace(' del ', ' ').replace(' de ', ' ')
                    if 'Tiburones' in short_name:
                        short_name = 'Tiburones'
                    elif 'Navegantes' in short_name:
                        short_name = 'Magallanes'
                    elif 'Tigres' in short_name:
                        short_name = 'Tigres'
                    elif 'Águilas' in short_name:
                        short_name = 'Águilas'
                    elif 'Cardenales' in short_name:
                        short_name = 'Cardenales'
                    elif 'Caribes' in short_name:
                        short_name = 'Caribes'
                    elif 'Bravos' in short_name:
                        short_name = 'Margarita'
                    
                    h2h_data.append({
                        'Rival': short_name,
                        'JJ': total_games,
                        'G': total_wins,
                        'P': total_losses,
                        'PCT': f'.{int(pct*1000):03d}',
                        'Local': f'{home_wins}-{home_losses}',
                        'Visitante': f'{away_wins}-{away_losses}',
                        'CF': runs_for,
                        'CP': runs_against,
                        'DIF': runs_for - runs_against,
                        'Última': f'{last_result} {last_score} ({last_date})' if last_date else f'{last_result} {last_score}'
                    })
                
                # Crear DataFrame y ordenar por PCT
                h2h_df = pd.DataFrame(h2h_data)
                h2h_df['pct_num'] = h2h_df['PCT'].apply(lambda x: float(x))
                h2h_df = h2h_df.sort_values('pct_num', ascending=False).drop('pct_num', axis=1)
                
                # Mostrar resumen
                col1, col2, col3, col4 = st.columns(4)
                
                total_h2h_wins = h2h_df['G'].sum()
                total_h2h_losses = h2h_df['P'].sum()
                total_h2h_games = h2h_df['JJ'].sum()
                total_h2h_pct = total_h2h_wins / total_h2h_games if total_h2h_games > 0 else 0
                
                with col1:
                    st.metric("Total Juegos", total_h2h_games)
                
                with col2:
                    st.metric("Récord Total", f"{total_h2h_wins}-{total_h2h_losses}")
                
                with col3:
                    st.metric("PCT General", f".{int(total_h2h_pct*1000):03d}")
                
                with col4:
                    winning_records = len(h2h_df[h2h_df['G'] > h2h_df['P']])
                    st.metric("Récord Ganador vs", f"{winning_records}/7 equipos")
                
                st.markdown("---")
                
                # Colorear la tabla
                def style_h2h(row):
                    styles = [''] * len(row)
                    
                    # Colorear PCT
                    if 'PCT' in row.index:
                        pct_val = float(row['PCT'])
                        if pct_val >= 0.500:
                            styles[row.index.get_loc('PCT')] = 'color: green; font-weight: bold'
                        else:
                            styles[row.index.get_loc('PCT')] = 'color: red'
                    
                    # Colorear DIF
                    if 'DIF' in row.index:
                        dif_val = row['DIF']
                        if dif_val > 0:
                            styles[row.index.get_loc('DIF')] = 'color: green; font-weight: bold'
                        elif dif_val < 0:
                            styles[row.index.get_loc('DIF')] = 'color: red'
                    
                    # Colorear última columna
                    if 'Última' in row.index:
                        if 'V' in str(row['Última']):
                            styles[row.index.get_loc('Última')] = 'background-color: #196F3D'
                        elif 'D' in str(row['Última']):
                            styles[row.index.get_loc('Última')] = 'background-color: #922B21'
                    
                    return styles
                
                # Mostrar tabla
                st.dataframe(
                    h2h_df.style.apply(style_h2h, axis=1),
                    use_container_width=True,
                    hide_index=True,
                    height=350
                )
                
                # Gráfico de barras H2H
                st.markdown("---")
                st.markdown("#### 📊 Visualización Head to Head")
                
                # Preparar datos para el gráfico
                h2h_chart = h2h_df.copy()
                
                fig_h2h = go.Figure()
                
                # Agregar barras de victorias
                fig_h2h.add_trace(go.Bar(
                    name='Victorias',
                    x=h2h_chart['Rival'],
                    y=h2h_chart['G'],
                    marker_color='#196F3D',
                    text=h2h_chart['G'],
                    textposition='auto',
                ))
                
                # Agregar barras de derrotas
                fig_h2h.add_trace(go.Bar(
                    name='Derrotas',
                    x=h2h_chart['Rival'],
                    y=h2h_chart['P'],
                    marker_color='#922B21',
                    text=h2h_chart['P'],
                    textposition='auto',
                ))
                
                fig_h2h.update_layout(
                    title=f'Récord de Leones del Caracas vs cada equipo - {selected_season_display}',
                    xaxis_title='Equipo',
                    yaxis_title='Juegos',
                    barmode='group',
                    height=400,
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    )
                )
                
                st.plotly_chart(fig_h2h, use_container_width=True)
                
                # Gráfico de diferencial de carreras por equipo
                col1, col2 = st.columns(2)
                
                with col1:
                    # Gráfico de pastel - Victorias vs Derrotas totales
                    fig_pie = go.Figure(data=[go.Pie(
                        labels=['Victorias', 'Derrotas'],
                        values=[total_h2h_wins, total_h2h_losses],
                        hole=.3,
                        marker_colors=['#196F3D', '#922B21']
                    )])
                    
                    fig_pie.update_layout(
                        title=f'Distribución V-D Total<br>{total_h2h_wins}-{total_h2h_losses}',
                        height=300,
                        showlegend=True
                    )
                    
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                with col2:
                    # Gráfico de diferencial por equipo
                    h2h_diff = h2h_df.sort_values('DIF', ascending=True)
                    colors = ['red' if x < 0 else 'green' for x in h2h_diff['DIF']]
                    
                    fig_diff = go.Figure(go.Bar(
                        x=h2h_diff['DIF'],
                        y=h2h_diff['Rival'],
                        orientation='h',
                        marker_color=colors,
                        text=h2h_diff['DIF'].apply(lambda x: f"{x:+d}"),
                        textposition='auto'
                    ))
                    
                    fig_diff.update_layout(
                        title='Diferencial de Carreras por Rival',
                        xaxis_title='Diferencial',
                        yaxis_title='',
                        height=300
                    )
                    
                    st.plotly_chart(fig_diff, use_container_width=True)
                
            else:
                st.warning("No hay juegos disponibles para calcular el head to head en esta temporada")
                
                # Mostrar tabla vacía
                h2h_data = []
                for team_id, team_name in LVBP_TEAMS.items():
                    if team_id != LEONES_ID:
                        short_name = team_name.split()[-1] if 'Navegantes' not in team_name else 'Magallanes'
                        h2h_data.append({
                            'Rival': short_name,
                            'JJ': 0,
                            'G': 0,
                            'P': 0,
                            'PCT': '.000',
                            'Local': '0-0',
                            'Visitante': '0-0',
                            'CF': 0,
                            'CP': 0,
                            'DIF': 0,
                            'Última': '-'
                        })
                
                h2h_df = pd.DataFrame(h2h_data)
                st.dataframe(h2h_df, use_container_width=True, hide_index=True)
                
        except Exception as e:
            st.error(f"Error al obtener datos: {str(e)}")
            
            # Mostrar tabla de respaldo con datos vacíos
            h2h_backup = []
            
            # Nombres cortos para cada equipo
            team_names_short = {
                698: "Tiburones",
                696: "Magallanes",
                699: "Tigres",
                692: "Águilas",
                693: "Cardenales",
                694: "Caribes",
                697: "Margarita"
            }
            
            for team_id, short_name in team_names_short.items():
                h2h_backup.append({
                    'Rival': short_name,
                    'JJ': 0,
                    'G': 0,
                    'P': 0,
                    'PCT': '.000',
                    'Local': '0-0',
                    'Visitante': '0-0',
                    'CF': 0,
                    'CP': 0,
                    'DIF': 0,
                    'Última': '-'
                })
            
            h2h_df = pd.DataFrame(h2h_backup)
            
            st.info("No se pudieron cargar los datos. Mostrando tabla vacía.")
            st.dataframe(h2h_df, use_container_width=True, hide_index=True)
            
            # Mostrar información de debug
            with st.expander("🔍 Información de Debug"):
                st.write(f"Error encontrado: {str(e)}")
                st.write(f"Temporada seleccionada: {selected_season}")
                st.write(f"ID de Leones: {LEONES_ID}")
                st.write("IDs de equipos LVBP:", list(LVBP_TEAMS.keys()))
    
    with tab4:
        st.markdown(f"### 📅 Calendario - {selected_season_display}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📅 Próximos 5 Juegos")
            
            try:
                supabase = init_supabase()
                from datetime import datetime, timedelta
                today = datetime.now().strftime('%Y-%m-%d')
                
                upcoming_games = supabase.table('games') \
                    .select('*') \
                    .eq('season', selected_season) \
                    .gte('game_date', today) \
                    .or_(f'home_team_id.eq.695,away_team_id.eq.695') \
                    .neq('status', 'Final') \
                    .order('game_date', desc=False) \
                    .limit(5) \
                    .execute()
                
                if upcoming_games.data and len(upcoming_games.data) > 0:
                    upcoming_display = []
                    
                    for game in upcoming_games.data:
                        try:
                            game_datetime = pd.to_datetime(game['game_datetime'])
                            fecha = game_datetime.strftime('%d/%m')
                            hora = game_datetime.strftime('%I:%M %p')
                        except:
                            fecha = game.get('game_date', 'TBD')[:10] if game.get('game_date') else 'TBD'
                            hora = 'TBD'
                        
                        if game['home_team_id'] == 695:
                            rival_id = game['away_team_id']
                            lugar = 'vs'
                            estadio_juego = "Monumental"
                        else:
                            rival_id = game['home_team_id']
                            lugar = '@'
                            estadios_equipos = {
                                698: "Universitario",
                                696: "José B. Pérez",
                                699: "J.P. Colmenares",
                                692: "Luis Aparicio",
                                693: "A.H. Gutiérrez",
                                694: "Chico Carrasquel",
                                697: "Nueva Esparta"
                            }
                            estadio_juego = estadios_equipos.get(rival_id, "Por definir")
                        
                        rival_names = {
                            698: "Tiburones",
                            696: "Magallanes",
                            699: "Tigres",
                            692: "Águilas",
                            693: "Cardenales",
                            694: "Caribes",
                            697: "Margarita"
                        }
                        rival = rival_names.get(rival_id, f"Equipo {rival_id}")
                        
                        status = game.get('status', 'Programado')
                        if status == 'Scheduled':
                            status = 'Programado'
                        elif status == 'In Progress':
                            status = 'En Juego'
                        elif status == 'Postponed':
                            status = 'Pospuesto'
                        
                        upcoming_display.append({
                            'Fecha': fecha,
                            'Hora': hora,
                            'Rival': f"{lugar} {rival}",
                            'Estadio': estadio_juego,
                            'Estado': status
                        })
                    
                    upcoming_df = pd.DataFrame(upcoming_display)
                    
                    def color_status(val):
                        if val == 'En Juego':
                            return 'background-color: #F39C12; color: white'
                        elif val == 'Pospuesto':
                            return 'background-color: #E74C3C; color: white'
                        elif val == 'Programado':
                            return 'background-color: #3498DB; color: white'
                        return ''
                    
                    def color_estadio(val):
                        if val == 'Monumental':
                            return 'color: #FEFAFA'
                        else:
                            return 'color: #FEFAFA'
                    
                    styled_df = upcoming_df.style.applymap(color_status, subset=['Estado'])
                    styled_df = styled_df.applymap(color_estadio, subset=['Estadio'])
                    
                    st.dataframe(styled_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay juegos programados próximamente")
                    if selected_season < get_current_season():
                        st.caption("📌 Esta es una temporada pasada.")
                    else:
                        st.caption("📌 La temporada puede haber finalizado.")
                        
            except Exception as e:
                st.error(f"Error: {str(e)}")
        
        with col2:
            st.markdown("#### 📜 Últimos 5 Resultados")
            
            try:
                recent_games = supabase.table('games') \
                    .select('*') \
                    .eq('season', selected_season) \
                    .eq('status', 'Final') \
                    .or_(f'home_team_id.eq.695,away_team_id.eq.695') \
                    .order('game_date', desc=True) \
                    .limit(5) \
                    .execute()
                
                if recent_games.data and len(recent_games.data) > 0:
                    games_display = []
                    
                    for game in recent_games.data:
                        is_home = game['home_team_id'] == 695
                        
                        try:
                            fecha = pd.to_datetime(game['game_date']).strftime('%d/%m')
                        except:
                            fecha = 'N/A'
                        
                        if is_home:
                            rival_id = game['away_team_id']
                            lugar = 'vs'
                            score_leones = game['home_score']
                            score_rival = game['away_score']
                        else:
                            rival_id = game['home_team_id']
                            lugar = '@'
                            score_leones = game['away_score']
                            score_rival = game['home_score']
                        
                        rival_names = {
                            698: "Tiburones",
                            696: "Magallanes",
                            699: "Tigres",
                            692: "Águilas",
                            693: "Cardenales",
                            694: "Caribes",
                            697: "Margarita"
                        }
                        rival = rival_names.get(rival_id, f"Equipo {rival_id}")
                        
                        if score_leones > score_rival:
                            resultado = 'V'
                        else:
                            resultado = 'D'
                        
                        games_display.append({
                            'Fecha': fecha,
                            'Rival': f"{lugar} {rival}",
                            'Resultado': resultado,
                            'Marcador': f"{score_leones}-{score_rival}"
                        })
                    
                    df_games = pd.DataFrame(games_display)
                    
                    def color_result(val):
                        if val == 'V':
                            return 'background-color: #196F3D; color: white; font-weight: bold'
                        elif val == 'D':
                            return 'background-color: #922B21; color: white; font-weight: bold'
                        return ''
                    
                    st.dataframe(
                        df_games.style.applymap(color_result, subset=['Resultado']),
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    total_v = len([g for g in games_display if g['Resultado'] == 'V'])
                    total_d = len([g for g in games_display if g['Resultado'] == 'D'])
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.metric("Últimos 5", f"{total_v}-{total_d}")
                    with col_b:
                        pct_recent = total_v / 5 if 5 > 0 else 0
                        st.metric("PCT", f".{int(pct_recent*1000):03d}")
                        
                else:
                    st.info("No hay juegos recientes disponibles")
                    
            except Exception as e:
                st.error(f"Error: {str(e)}")

else:
    st.warning(f"No hay datos de standings disponibles para la temporada {selected_season_display}")
    st.info("Los datos se actualizan diariamente a las 2:00 AM VET")
    
    # Mostrar información de debug
    with st.expander("🔍 Información de Debug"):
        st.write(f"Temporada seleccionada: {selected_season}")
        st.write(f"Temporadas disponibles: {available_seasons}")
        
        # Intentar mostrar qué equipos hay en la BD
        try:
            supabase = init_supabase()
            teams = supabase.table('teams').select('id, name, abbreviation').eq('league_id', 135).execute()
            if teams.data:
                st.write("Equipos en la base de datos:")
                teams_df = pd.DataFrame(teams.data)
                st.dataframe(teams_df, use_container_width=True)
            else:
                st.write("No se encontraron equipos en la base de datos")
        except Exception as e:
            st.error(f"Error al consultar equipos: {str(e)}")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>📊 Datos actualizados automáticamente | Fuente: MLB Stats API</p>
    <p>Los standings se calculan en base a los juegos finalizados</p>
</div>
""", unsafe_allow_html=True)

# Agregar leyenda
with st.expander("📖 Leyenda"):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        **Abreviaciones:**
        - **G**: Ganados
        - **P**: Perdidos
        - **PCT**: Porcentaje de victorias
        - **JD**: Juegos detrás del líder
        """)
    
    with col2:
        st.markdown("""
        **Estadísticas:**
        - **CF**: Carreras a favor
        - **CP**: Carreras permitidas
        - **DIF**: Diferencial de carreras
        - **Local/Visitante**: Récord como local/visitante
        """)
    
    with col3:
        st.markdown("""
        **Rachas:**
        - **W#**: Victorias consecutivas
        - **L#**: Derrotas consecutivas
        - **Últimos 10**: Récord en los últimos 10 juegos
        """)








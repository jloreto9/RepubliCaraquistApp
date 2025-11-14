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
    
    # Selector de temporada
    selected_season_display = st.selectbox(
        "⚾ Seleccionar Temporada",
        options=list(season_options.keys()),
        index=0
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
                color_discrete_map={'wins': '#90EE90', 'losses': '#FFB6C1'},
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
        
        # Aquí iría el código para head to head
        # Por ahora, placeholder
        st.info("Sección en desarrollo - Mostrará el récord contra cada equipo")
        
        # Tabla ejemplo
        h2h_data = []
        for team_id, team_name in LVBP_TEAMS.items():
            if team_id != 695:  # No contra sí mismo
                h2h_data.append({
                    'Rival': team_name,
                    'Victorias': 0,
                    'Derrotas': 0,
                    'PCT': '.000',
                    'Local': '0-0',
                    'Visitante': '0-0'
                })
        
        h2h_df = pd.DataFrame(h2h_data)
        st.dataframe(h2h_df, use_container_width=True, hide_index=True)
    
    with tab4:
        st.markdown(f"### 📅 Calendario - {selected_season_display}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📅 Próximos 5 Juegos")
            st.info("Sección en desarrollo")
        
        with col2:
            st.markdown("#### 📜 Últimos 5 Resultados")
            
            recent_games = get_recent_games(team_id=695, limit=5)
            
            if not recent_games.empty:
                games_display = []
                
                for _, game in recent_games.iterrows():
                    is_home = game['home_team_id'] == 695
                    
                    try:
                        fecha = pd.to_datetime(game['game_date']).strftime('%d/%m')
                    except:
                        fecha = 'N/A'
                    
                    if is_home:
                        rival = "vs " + str(game.get('away_team_id', 'TBD'))
                        if game['status'] == 'Final':
                            resultado = 'V' if game['home_score'] > game['away_score'] else 'D'
                            marcador = f"{game['home_score']}-{game['away_score']}"
                        else:
                            resultado = '-'
                            marcador = 'Por jugar'
                    else:
                        rival = "@ " + str(game.get('home_team_id', 'TBD'))
                        if game['status'] == 'Final':
                            resultado = 'V' if game['away_score'] > game['home_score'] else 'D'
                            marcador = f"{game['away_score']}-{game['home_score']}"
                        else:
                            resultado = '-'
                            marcador = 'Por jugar'
                    
                    games_display.append({
                        'Fecha': fecha,
                        'Rival': rival,
                        'Resultado': resultado,
                        'Marcador': marcador
                    })
                
                df_games = pd.DataFrame(games_display)
                
                def color_result(val):
                    if val == 'V':
                        return 'background-color: #90EE90'
                    elif val == 'D':
                        return 'background-color: #FFB6C1'
                    return ''
                
                st.dataframe(
                    df_games.style.applymap(color_result, subset=['Resultado']),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No hay juegos recientes disponibles")

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






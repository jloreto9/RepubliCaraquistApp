# streamlit_app/pages/1_📊_Standings.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.supabase_client import get_standings, get_recent_games, get_team_stats, init_supabase
from datetime import datetime

st.set_page_config(page_title="Standings - RepubliCaraquistApp", page_icon="📊", layout="wide")

# Header
st.title("📊 Standings y Resultados")
st.markdown("### Tabla de Posiciones - LVBP 2024-2025")

# Obtener datos
try:
    standings_df = get_standings(season=2025)
    
    if standings_df.empty:
        # Si no hay datos en la tabla standings, calcular desde games
        supabase = init_supabase()
        
        # Obtener todos los juegos
        games = supabase.table('games').select('*').eq('season', 2025).eq('status', 'Final').execute()
        games_df = pd.DataFrame(games.data)
        
        # Obtener equipos
        teams = supabase.table('teams').select('*').execute()
        teams_df = pd.DataFrame(teams.data)
        
        # Calcular standings manualmente
        standings_data = []
        for team in teams_df.itertuples():
            team_games = games_df[(games_df['home_team_id'] == team.id) | (games_df['away_team_id'] == team.id)]
            
            wins = 0
            losses = 0
            runs_for = 0
            runs_against = 0
            
            for _, game in team_games.iterrows():
                if game['home_team_id'] == team.id:
                    runs_for += game['home_score'] or 0
                    runs_against += game['away_score'] or 0
                    if game['home_score'] > game['away_score']:
                        wins += 1
                    else:
                        losses += 1
                else:
                    runs_for += game['away_score'] or 0
                    runs_against += game['home_score'] or 0
                    if game['away_score'] > game['home_score']:
                        wins += 1
                    else:
                        losses += 1
            
            pct = wins / (wins + losses) if (wins + losses) > 0 else 0
            
            standings_data.append({
                'team_name': team.name,
                'wins': wins,
                'losses': losses,
                'pct': pct,
                'games_back': 0,  # Se calculará después
                'runs_for': runs_for,
                'runs_against': runs_against,
                'run_diff': runs_for - runs_against
            })
        
        standings_df = pd.DataFrame(standings_data).sort_values('pct', ascending=False)
        
        # Calcular games back
        if not standings_df.empty:
            leader_wins = standings_df.iloc[0]['wins']
            leader_losses = standings_df.iloc[0]['losses']
            standings_df['games_back'] = standings_df.apply(
                lambda x: ((leader_wins - x['wins']) + (x['losses'] - leader_losses)) / 2, axis=1
            )
    
    # Tabs para diferentes vistas
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Tabla General", "📈 Gráficos", "🆚 Head to Head", "📅 Calendario"])
    
    with tab1:
        # Mostrar tabla de posiciones
        if not standings_df.empty:
            # Formatear la tabla
            display_df = standings_df[['team_name', 'wins', 'losses', 'pct', 'games_back', 'runs_for', 'runs_against', 'run_diff']].copy()
            display_df.columns = ['Equipo', 'G', 'P', 'PCT', 'JD', 'CF', 'CP', 'DIF']
            display_df['PCT'] = display_df['PCT'].apply(lambda x: f'.{int(x*1000):03d}')
            display_df['JD'] = display_df['JD'].apply(lambda x: '-' if x == 0 else f'{x:.1f}')
            
            # Resaltar Leones del Caracas
            def highlight_leones(row):
                if 'Leones' in row['Equipo']:
                    return ['background-color: #FDB827; color: #CE1141; font-weight: bold'] * len(row)
                return [''] * len(row)
            
            st.dataframe(
                display_df.style.apply(highlight_leones, axis=1),
                use_container_width=True,
                hide_index=True,
                height=400
            )
            
            # Métricas adicionales
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            
            leones_data = standings_df[standings_df['team_name'].str.contains('Leones')]
            if not leones_data.empty:
                leones = leones_data.iloc[0]
                
                with col1:
                    st.metric(
                        "🏆 Posición",
                        f"{standings_df.index[standings_df['team_name'] == leones['team_name']].tolist()[0] + 1}° lugar",
                        f"{leones['games_back']:.1f} JD" if leones['games_back'] > 0 else "Líder"
                    )
                
                with col2:
                    st.metric(
                        "📊 Efectividad",
                        f".{int(leones['pct']*1000):03d}",
                        f"{leones['wins']}-{leones['losses']}"
                    )
                
                with col3:
                    st.metric(
                        "🎯 Diferencial",
                        f"{leones['run_diff']:+d}",
                        f"CF: {leones['runs_for']} | CP: {leones['runs_against']}"
                    )
    
    with tab2:
        # Gráficos
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de victorias vs derrotas
            fig_wins = px.bar(
                standings_df.head(8),
                x='team_name',
                y=['wins', 'losses'],
                title='Victorias vs Derrotas',
                labels={'value': 'Juegos', 'team_name': 'Equipo'},
                color_discrete_map={'wins': '#90EE90', 'losses': '#FFB6C1'}
            )
            fig_wins.update_layout(height=400)
            st.plotly_chart(fig_wins, use_container_width=True)
        
        with col2:
            # Gráfico de diferencial de carreras
            fig_diff = px.bar(
                standings_df.head(8),
                x='team_name',
                y='run_diff',
                title='Diferencial de Carreras',
                color='run_diff',
                color_continuous_scale=['red', 'yellow', 'green'],
                labels={'run_diff': 'Diferencial', 'team_name': 'Equipo'}
            )
            fig_diff.update_layout(height=400)
            st.plotly_chart(fig_diff, use_container_width=True)
        
        # Gráfico de tendencia
        st.markdown("### 📈 Tendencia de Posiciones (Últimos 30 días)")
        
        # Aquí iría un gráfico de líneas con la evolución de las posiciones
        # Por ahora, mostraremos un placeholder
        fig_trend = go.Figure()
        
        # Datos de ejemplo (en producción, esto vendría de la BD)
        import numpy as np
        dates = pd.date_range(end=datetime.now(), periods=30)
        
        for i, team in enumerate(standings_df.head(5)['team_name']):
            y_values = np.random.randint(1, 9, size=30)
            if 'Leones' in team:
                fig_trend.add_trace(go.Scatter(
                    x=dates, y=y_values,
                    mode='lines+markers',
                    name=team,
                    line=dict(color='#FDB827', width=3),
                    marker=dict(size=8)
                ))
            else:
                fig_trend.add_trace(go.Scatter(
                    x=dates, y=y_values,
                    mode='lines',
                    name=team
                ))
        
        fig_trend.update_layout(
            title='Evolución de Posiciones',
            xaxis_title='Fecha',
            yaxis_title='Posición',
            yaxis=dict(autorange='reversed'),
            height=400
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    
    with tab3:
        st.markdown("### 🆚 Récord Head to Head - Leones del Caracas")
        
        # Obtener récord contra cada equipo
        supabase = init_supabase()
        
        # Query para head to head
        h2h_data = []
        teams = supabase.table('teams').select('*').execute()
        
        for team in teams.data:
            if team['id'] != 695:  # No contra sí mismo
                games = supabase.table('games') \
                    .select('*') \
                    .eq('season', 2025) \
                    .eq('status', 'Final') \
                    .or_(f"and(home_team_id.eq.695,away_team_id.eq.{team['id']}),and(home_team_id.eq.{team['id']},away_team_id.eq.695)") \
                    .execute()
                
                wins = 0
                losses = 0
                
                for game in games.data:
                    if game['home_team_id'] == 695:
                        if game['home_score'] > game['away_score']:
                            wins += 1
                        else:
                            losses += 1
                    else:
                        if game['away_score'] > game['home_score']:
                            wins += 1
                        else:
                            losses += 1
                
                if wins + losses > 0:
                    h2h_data.append({
                        'Rival': team['name'],
                        'Victorias': wins,
                        'Derrotas': losses,
                        'PCT': f".{int((wins/(wins+losses))*1000):03d}" if wins + losses > 0 else ".000"
                    })
        
        if h2h_data:
            h2h_df = pd.DataFrame(h2h_data)
            
            # Colorear según el récord
            def color_record(val):
                if isinstance(val, str) and val.startswith('.'):
                    pct = float(val)
                    if pct >= 0.500:
                        return 'color: green'
                    else:
                        return 'color: red'
                return ''
            
            st.dataframe(
                h2h_df.style.applymap(color_record, subset=['PCT']),
                use_container_width=True,
                hide_index=True
            )
    
    with tab4:
        st.markdown("### 📅 Próximos Juegos")
        
        # Obtener próximos juegos
        upcoming_games = supabase.table('games') \
            .select('*, home_team:teams!games_home_team_id_fkey(name), away_team:teams!games_away_team_id_fkey(name)') \
            .or_('home_team_id.eq.695,away_team_id.eq.695') \
            .gte('game_date', datetime.now().strftime('%Y-%m-%d')) \
            .order('game_date', asc=True) \
            .limit(10) \
            .execute()
        
        if upcoming_games.data:
            upcoming_df = pd.DataFrame(upcoming_games.data)
            
            # Formatear para mostrar
            display_upcoming = []
            for _, game in upcoming_df.iterrows():
                display_upcoming.append({
                    'Fecha': pd.to_datetime(game['game_date']).strftime('%d/%m'),
                    'Hora': pd.to_datetime(game['game_datetime']).strftime('%I:%M %p') if game['game_datetime'] else 'TBD',
                    'Local': game['home_team']['name'] if game['home_team'] else 'TBD',
                    'Visitante': game['away_team']['name'] if game['away_team'] else 'TBD',
                    'Estadio': game['venue'] if game['venue'] else 'TBD'
                })
            
            st.dataframe(pd.DataFrame(display_upcoming), use_container_width=True, hide_index=True)
        else:
            st.info("No hay juegos programados próximamente")
        
        st.markdown("---")
        st.markdown("### 📜 Últimos Resultados")
        
        recent_games = get_recent_games(team_id=695, limit=10)
        
        if not recent_games.empty:
            display_recent = []
            for _, game in recent_games.iterrows():
                is_home = game['home_team_id'] == 695
                
                if is_home:
                    result = 'V' if game['home_score'] > game['away_score'] else 'D'
                    score = f"{game['home_score']}-{game['away_score']}"
                    vs = game['away_team']['abbreviation'] if game.get('away_team') else 'OPP'
                else:
                    result = 'V' if game['away_score'] > game['home_score'] else 'D'
                    score = f"{game['away_score']}-{game['home_score']}"
                    vs = f"@ {game['home_team']['abbreviation']}" if game.get('home_team') else '@ OPP'
                
                display_recent.append({
                    'Fecha': pd.to_datetime(game['game_date']).strftime('%d/%m'),
                    'Vs': vs,
                    'Resultado': result,
                    'Marcador': score
                })
            
            recent_df = pd.DataFrame(display_recent)
            
            # Colorear resultados
            def color_result(val):
                if val == 'V':
                    return 'background-color: #90EE90'
                elif val == 'D':
                    return 'background-color: #FFB6C1'
                return ''
            
            st.dataframe(
                recent_df.style.applymap(color_result, subset=['Resultado']),
                use_container_width=True,
                hide_index=True
            )

except Exception as e:
    st.error(f"Error al cargar los datos: {str(e)}")
    st.info("Verifica la conexión con Supabase y que las tablas contengan datos.")

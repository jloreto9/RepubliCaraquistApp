# streamlit_app/app.py
import streamlit as st
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de la página
st.set_page_config(
    page_title="RepubliCaraquistApp",
    page_icon="🦁",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS personalizado
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        color: #FDB827;
        text-align: center;
        font-weight: bold;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .leones-gold {
        color: #FDB827;
    }
    .leones-red {
        color: #CE1141;
    }
    </style>
    """, unsafe_allow_html=True)

# Header principal
st.markdown('<h1 class="main-header">🦁 RepubliCaraquistApp</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Análisis Avanzado de los Leones del Caracas - LVBP</p>', unsafe_allow_html=True)

# Sidebar
# Sidebar
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/0/0d/Logo_Leones_del_Caracas.svg", width=200)
    st.markdown("---")
    
    # Contenido principal - Dashboard con datos reales
from utils.supabase_client import get_standings, get_recent_games, get_team_stats

# Obtener datos reales
current_season = 2026  # o get_current_season()
standings_df = get_standings(current_season)

# Datos de los Leones
if not standings_df.empty:
    # Buscar datos de los Leones
    leones_data = standings_df[standings_df['team_name'].str.contains('Leones', case=False, na=False)]
    
    if not leones_data.empty:
        leones = leones_data.iloc[0]
        
        # Posición
        position = standings_df.index[standings_df['team_name'] == leones['team_name']].tolist()[0] + 1
        position_text = f"{position}°"
        
        # Récord
        wins = int(leones.get('wins', 0))
        losses = int(leones.get('losses', 0))
        record_text = f"{wins}-{losses}"
        pct = leones.get('pct', 0)
        
        # Racha
        streak = leones.get('streak', 'N/A')
        
        # Diferencial
        run_diff = int(leones.get('run_diff', 0))
        runs_for = int(leones.get('runs_for', 0))
        runs_against = int(leones.get('runs_against', 0))
    else:
        # Valores por defecto si no hay datos
        position_text = "N/A"
        record_text = "0-0"
        pct = 0
        streak = "N/A"
        run_diff = 0
        runs_for = 0
        runs_against = 0
else:
    # Sin datos - valores por defecto
    position_text = "N/A"
    record_text = "0-0"
    pct = 0
    streak = "N/A"
    run_diff = 0
    runs_for = 0
    runs_against = 0

# Mostrar métricas
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric(
        label="🏆 Posición",
        value=position_text,
        delta=f"↑ {position} posición" if position <= 4 else f"↓ {position} posición"
    )
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric(
        label="📊 Récord",
        value=record_text,
        delta=f".{int(pct*1000):03d} PCT"
    )
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric(
        label="🔥 Racha",
        value=streak,
        delta="Racha actual"
    )
    st.markdown('</div>', unsafe_allow_html=True)

with col4:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric(
        label="🎯 Diferencial",
        value=f"{run_diff:+d}" if run_diff != 0 else "0",
        delta=f"RF: {runs_for} | RA: {runs_against}"
    )
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# Tabs principales
tab1, tab2, tab3 = st.tabs(["📅 Último Juego", "📈 Tendencias", "🌟 Líderes del Equipo"])

with tab1:
    # Obtener último juego real
    recent_games = get_recent_games(team_id=695, limit=1)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 🆚 Último Resultado")
        
        if not recent_games.empty:
            last_game = recent_games.iloc[0]
            
            # Determinar si Leones ganó
            is_home = last_game['home_team_id'] == 695
            if is_home:
                score_text = f"Leones del Caracas {last_game['home_score']} - {last_game['away_score']} {last_game.get('away_team', {}).get('name', 'Rival')}"
                won = last_game['home_score'] > last_game['away_score']
            else:
                score_text = f"{last_game.get('home_team', {}).get('name', 'Rival')} {last_game['home_score']} - {last_game['away_score']} Leones del Caracas"
                won = last_game['away_score'] > last_game['home_score']
            
            # Color según resultado
            bg_color = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' if won else 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'
            
            st.markdown(f"""
            <div style='background: {bg_color}; 
                        padding: 2rem; border-radius: 1rem; color: white;'>
                <h2 style='text-align: center; margin: 0;'>
                    {score_text}
                </h2>
                <p style='text-align: center; margin-top: 1rem;'>
                    📅 {pd.to_datetime(last_game['game_date']).strftime('%d de %B, %Y')} | 📍 {last_game.get('venue', 'Estadio')}
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("No hay juegos recientes disponibles")
    
    with col2:
        st.markdown("### ⭐ Jugador del Juego")
        # Aquí podrías obtener el mejor jugador del último juego
        # Por ahora, datos de ejemplo
        st.info("""
        **Por implementar**  
        Estadísticas del mejor jugador
        """)

with tab2:
    st.markdown("### 📊 Últimos 10 Juegos")
    
    # Crear datos de ejemplo
    games_data = {
        'Fecha': pd.date_range(end=datetime.now(), periods=10).strftime('%d/%m'),
        'Rival': ['MAG', 'LAG', 'ARA', 'ZUL', 'LAR', 'MAR', 'ANZ', 'MAG', 'LAG', 'ARA'],
        'Resultado': ['W', 'W', 'W', 'L', 'W', 'L', 'W', 'W', 'L', 'W'],
        'Marcador': ['7-4', '5-3', '8-6', '3-5', '6-2', '4-7', '9-5', '4-3', '2-4', '6-4']
    }
    
    df_games = pd.DataFrame(games_data)
    
    # Mostrar con colores
    def color_result(val):
        color = '#90EE90' if val == 'W' else '#FFB6C1'
        return f'background-color: {color}'
    
    st.dataframe(
        df_games.style.applymap(color_result, subset=['Resultado']),
        use_container_width=True,
        hide_index=True
    )

with tab3:
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🏏 Líderes de Bateo")
        batting_leaders = pd.DataFrame({
            'Jugador': ['Harold Castro', 'Gleyber Torres', 'José Rondón'],
            'AVG': [.342, .318, .305],
            'HR': [8, 12, 10],
            'RBI': [35, 42, 38]
        })
        st.dataframe(batting_leaders, use_container_width=True, hide_index=True)
    
    with col2:
        st.markdown("### ⚾ Líderes de Pitcheo")
        pitching_leaders = pd.DataFrame({
            'Jugador': ['Jesús Luzardo', 'Eduardo Rodríguez', 'Silvino Bracho'],
            'ERA': [2.45, 3.12, 2.89],
            'SO': [45, 38, 31],
            'WHIP': [1.05, 1.18, 1.12]
        })
        st.dataframe(pitching_leaders, use_container_width=True, hide_index=True)

st.markdown("---")

# Footer
st.markdown("""
<div style='text-align: center; color: #666; padding: 2rem;'>
    <p>Desarrollado Jorge Leonardo Loreto 📊 Científico de Datos | ⚾ Analista de Béisbol | 🦁 Fanático de los Leones del Caracas Twitter: @RepubCaraquista</p>
    <p>📊 Datos actualizados diariamente a las 2:00 AM VET</p>
    <p>Powered by MLB Stats API & Supabase</p>
</div>
""", unsafe_allow_html=True)

# Información de navegación
st.info("👈 **Navega por las diferentes secciones usando el menú lateral**")





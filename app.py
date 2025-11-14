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
    
    # Selector de temporada
    from utils.supabase_client import get_current_season, get_available_seasons
    
    current_season = get_current_season()  # Debería ser 2026
    available_seasons = get_available_seasons()
    
    # Si no hay temporadas disponibles, usar la actual
    if not available_seasons:
        available_seasons = [current_season]
    
    selected_season = st.selectbox(
        "⚾ Temporada",
        available_seasons,
        index=0
    )
    
    # Mostrar como 2025-2026
    if selected_season == 2026:
        st.markdown("### Temporada 2025-2026")
    elif selected_season == 2025:
        st.markdown("### Temporada 2024-2025")
    else:
        st.markdown(f"### Temporada {selected_season-1}-{selected_season}")
    
    st.markdown("**Liga Venezolana de Béisbol Profesional**")

# Contenido principal - Dashboard
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric(
        label="🏆 Posición",
        value="2do",
        delta="↑ 1 posición"
    )
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric(
        label="📊 Récord",
        value="25-15",
        delta=".625 PCT"
    )
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric(
        label="🔥 Racha",
        value="W3",
        delta="3 victorias seguidas"
    )
    st.markdown('</div>', unsafe_allow_html=True)

with col4:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric(
        label="🎯 Diferencial",
        value="+28",
        delta="RF: 198 | RA: 170"
    )
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# Tabs principales
tab1, tab2, tab3 = st.tabs(["📅 Último Juego", "📈 Tendencias", "🌟 Líderes del Equipo"])

with tab1:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 🆚 Último Resultado")
        st.markdown("""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 2rem; border-radius: 1rem; color: white;'>
            <h2 style='text-align: center; margin: 0;'>
                Leones del Caracas 7 - 4 Navegantes del Magallanes
            </h2>
            <p style='text-align: center; margin-top: 1rem;'>
                📅 15 de Diciembre, 2024 | 📍 Estadio Universitario
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("### ⭐ Jugador del Juego")
        st.info("""
        **Harold Castro**  
        3-4, 2 HR, 4 RBI  
        
        **AVG:** .342  
        **OPS:** .925
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
    <p>Desarrollado con ❤️ por Jorge Leonardo Loreto</p>
    <p>📊 Datos actualizados diariamente a las 2:00 AM VET</p>
    <p>Powered by MLB Stats API & Supabase</p>
</div>
""", unsafe_allow_html=True)

# Información de navegación
st.info("👈 **Navega por las diferentes secciones usando el menú lateral**")



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
    from utils.supabase_client import init_supabase, get_current_season, get_available_seasons
except:
    from streamlit_app.utils.supabase_client import init_supabase, get_current_season, get_available_seasons

st.set_page_config(page_title="Estadísticas Individuales - RepubliCaraquistApp", page_icon="⚾", layout="wide")

# Header
st.title("⚾ Estadísticas Individuales")
st.markdown("### Líderes de Bateo y Pitcheo - Leones del Caracas")

# Selector de temporada
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    current_season = get_current_season()
    available_seasons = get_available_seasons()
    
    if not available_seasons:
        available_seasons = [current_season]
    
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

# Tabs para Bateo y Pitcheo
tab1, tab2 = st.tabs(["🏏 Estadísticas de Bateo", "⚾ Estadísticas de Pitcheo"])

# Inicializar Supabase
supabase = init_supabase()
LEONES_ID = 695

with tab1:
    st.markdown(f"### 🏏 Líderes de Bateo - {selected_season_display}")
    
    try:
        # Obtener estadísticas de bateo
        batting_response = supabase.table('batting_stats') \
            .select('*, players!inner(full_name, jersey_number)') \
            .eq('team_id', LEONES_ID) \
            .execute()
        
        if batting_response.data and len(batting_response.data) > 0:
            # Crear DataFrame
            batting_df = pd.DataFrame(batting_response.data)
            
            # Extraer nombre del jugador
            batting_df['player_name'] = batting_df['players'].apply(lambda x: x['full_name'] if isinstance(x, dict) else 'Desconocido')
            batting_df['jersey'] = batting_df['players'].apply(lambda x: x.get('jersey_number', '') if isinstance(x, dict) else '')
            
            # Agrupar por jugador
            batting_grouped = batting_df.groupby(['player_id', 'player_name', 'jersey']).agg({
                'ab': 'sum',
                'r': 'sum',
                'h': 'sum',
                'doubles': 'sum',
                'triples': 'sum',
                'hr': 'sum',
                'rbi': 'sum',
                'bb': 'sum',
                'so': 'sum',
                'sb': 'sum',
                'cs': 'sum'
            }).reset_index()
            
            # Calcular estadísticas
            batting_grouped['AVG'] = (batting_grouped['h'] / batting_grouped['ab']).round(3).fillna(0)
            batting_grouped['OBP'] = ((batting_grouped['h'] + batting_grouped['bb']) / 
                                      (batting_grouped['ab'] + batting_grouped['bb'])).round(3).fillna(0)
            batting_grouped['SLG'] = ((batting_grouped['h'] + batting_grouped['doubles'] + 
                                       2*batting_grouped['triples'] + 3*batting_grouped['hr']) / 
                                      batting_grouped['ab']).round(3).fillna(0)
            batting_grouped['OPS'] = (batting_grouped['OBP'] + batting_grouped['SLG']).round(3)
            
            # Filtrar jugadores con al menos 10 turnos al bate
            batting_qualified = batting_grouped[batting_grouped['ab'] >= 10].copy()
            
            # Ordenar por promedio
            batting_qualified = batting_qualified.sort_values('AVG', ascending=False)
            
            # Métricas principales
            col1, col2, col3, col4 = st.columns(4)
            
            if not batting_qualified.empty:
                leader = batting_qualified.iloc[0]
                
                with col1:
                    st.metric(
                        "👑 Líder de Bateo",
                        leader['player_name'],
                        f"AVG: {leader['AVG']:.3f}"
                    )
                
                with col2:
                    hr_leader = batting_qualified.nlargest(1, 'hr').iloc[0]
                    st.metric(
                        "💪 Líder Jonrones",
                        hr_leader['player_name'],
                        f"HR: {int(hr_leader['hr'])}"
                    )
                
                with col3:
                    rbi_leader = batting_qualified.nlargest(1, 'rbi').iloc[0]
                    st.metric(
                        "🎯 Líder Impulsadas",
                        rbi_leader['player_name'],
                        f"RBI: {int(rbi_leader['rbi'])}"
                    )
                
                with col4:
                    ops_leader = batting_qualified.nlargest(1, 'OPS').iloc[0]
                    st.metric(
                        "📊 Líder OPS",
                        ops_leader['player_name'],
                        f"OPS: {ops_leader['OPS']:.3f}"
                    )
            
            st.markdown("---")
            
            # Tabla de líderes
            display_cols = {
                'player_name': 'Jugador',
                'jersey': '#',
                'ab': 'VB',
                'r': 'CA',
                'h': 'H',
                'doubles': '2B',
                'triples': '3B',
                'hr': 'HR',
                'rbi': 'CI',
                'bb': 'BB',
                'so': 'SO',
                'sb': 'BR',
                'AVG': 'AVG',
                'OBP': 'OBP',
                'SLG': 'SLG',
                'OPS': 'OPS'
            }
            
            batting_display = batting_qualified[list(display_cols.keys())].copy()
            batting_display.columns = list(display_cols.values())
            
            # Formatear estadísticas
            for col in ['AVG', 'OBP', 'SLG', 'OPS']:
                if col in batting_display.columns:
                    batting_display[col] = batting_display[col].apply(lambda x: f'.{int(x*1000):03d}' if x > 0 else '.000')
            
            # Convertir a enteros
            int_cols = ['VB', 'CA', 'H', '2B', '3B', 'HR', 'CI', 'BB', 'SO', 'BR']
            for col in int_cols:
                if col in batting_display.columns:
                    batting_display[col] = batting_display[col].astype(int)
            
            st.dataframe(
                batting_display,
                use_container_width=True,
                hide_index=True,
                height=400
            )
            
            # Gráficos
            st.markdown("---")
            col1, col2 = st.columns(2)
            
            with col1:
                # Top 10 promedio de bateo
                top_avg = batting_qualified.nlargest(10, 'AVG')
                fig_avg = px.bar(
                    top_avg,
                    x='AVG',
                    y='player_name',
                    orientation='h',
                    title='Top 10 - Promedio de Bateo',
                    labels={'AVG': 'Promedio', 'player_name': ''},
                    color='AVG',
                    color_continuous_scale=['#922B21', '#FDB827', '#196F3D']
                )
                fig_avg.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig_avg, use_container_width=True)
            
            with col2:
                # Jonrones vs RBI
                fig_power = px.scatter(
                    batting_qualified,
                    x='hr',
                    y='rbi',
                    size='ab',
                    hover_data=['player_name'],
                    title='Poder: Jonrones vs Carreras Impulsadas',
                    labels={'hr': 'Jonrones', 'rbi': 'Carreras Impulsadas'},
                    color='OPS',
                    color_continuous_scale=['#922B21', '#FDB827', '#196F3D']
                )
                fig_power.update_layout(height=400)
                st.plotly_chart(fig_power, use_container_width=True)
            
        else:
            st.info("No hay estadísticas de bateo disponibles para esta temporada")
            
    except Exception as e:
        st.error(f"Error al cargar estadísticas de bateo: {str(e)}")

with tab2:
    st.markdown(f"### ⚾ Líderes de Pitcheo - {selected_season_display}")
    
    try:
        # Obtener estadísticas de pitcheo
        pitching_response = supabase.table('pitching_stats') \
            .select('*, players!inner(full_name, jersey_number)') \
            .eq('team_id', LEONES_ID) \
            .execute()
        
        if pitching_response.data and len(pitching_response.data) > 0:
            # Crear DataFrame
            pitching_df = pd.DataFrame(pitching_response.data)
            
            # Extraer nombre del jugador
            pitching_df['player_name'] = pitching_df['players'].apply(lambda x: x['full_name'] if isinstance(x, dict) else 'Desconocido')
            pitching_df['jersey'] = pitching_df['players'].apply(lambda x: x.get('jersey_number', '') if isinstance(x, dict) else '')
            
            # Agrupar por jugador
            pitching_grouped = pitching_df.groupby(['player_id', 'player_name', 'jersey']).agg({
                'ip_decimal': 'sum',
                'h': 'sum',
                'r': 'sum',
                'er': 'sum',
                'bb': 'sum',
                'so': 'sum',
                'hr': 'sum'
            }).reset_index()
            
            # Calcular estadísticas
            pitching_grouped['ERA'] = (pitching_grouped['er'] * 9 / pitching_grouped['ip_decimal']).round(2).fillna(0)
            pitching_grouped['WHIP'] = ((pitching_grouped['bb'] + pitching_grouped['h']) / 
                                        pitching_grouped['ip_decimal']).round(2).fillna(0)
            pitching_grouped['K9'] = (pitching_grouped['so'] * 9 / pitching_grouped['ip_decimal']).round(1).fillna(0)
            pitching_grouped['BB9'] = (pitching_grouped['bb'] * 9 / pitching_grouped['ip_decimal']).round(1).fillna(0)
            
            # Convertir IP decimal a formato tradicional
            pitching_grouped['IP'] = pitching_grouped['ip_decimal'].apply(
                lambda x: f"{int(x)}.{int((x - int(x)) * 3)}"
            )
            
            # Filtrar pitchers con al menos 5 innings
            pitching_qualified = pitching_grouped[pitching_grouped['ip_decimal'] >= 5].copy()
            
            # Ordenar por ERA
            pitching_qualified = pitching_qualified.sort_values('ERA')
            
            # Métricas principales
            col1, col2, col3, col4 = st.columns(4)
            
            if not pitching_qualified.empty:
                era_leader = pitching_qualified.iloc[0]
                
                with col1:
                    st.metric(
                        "🏆 Líder ERA",
                        era_leader['player_name'],
                        f"ERA: {era_leader['ERA']:.2f}"
                    )
                
                with col2:
                    so_leader = pitching_qualified.nlargest(1, 'so').iloc[0]
                    st.metric(
                        "🔥 Líder Ponches",
                        so_leader['player_name'],
                        f"SO: {int(so_leader['so'])}"
                    )
                
                with col3:
                    whip_leader = pitching_qualified.nsmallest(1, 'WHIP').iloc[0]
                    st.metric(
                        "🎯 Líder WHIP",
                        whip_leader['player_name'],
                        f"WHIP: {whip_leader['WHIP']:.2f}"
                    )
                
                with col4:
                    ip_leader = pitching_qualified.nlargest(1, 'ip_decimal').iloc[0]
                    st.metric(
                        "💪 Más Innings",
                        ip_leader['player_name'],
                        f"IP: {ip_leader['IP']}"
                    )
            
            st.markdown("---")
            
            # Tabla de líderes
            display_cols = {
                'player_name': 'Jugador',
                'jersey': '#',
                'IP': 'IP',
                'h': 'H',
                'r': 'C',
                'er': 'CL',
                'bb': 'BB',
                'so': 'SO',
                'hr': 'HR',
                'ERA': 'ERA',
                'WHIP': 'WHIP',
                'K9': 'K/9',
                'BB9': 'BB/9'
            }
            
            pitching_display = pitching_qualified[list(display_cols.keys())].copy()
            pitching_display.columns = list(display_cols.values())
            
            # Convertir a enteros
            int_cols = ['H', 'C', 'CL', 'BB', 'SO', 'HR']
            for col in int_cols:
                if col in pitching_display.columns:
                    pitching_display[col] = pitching_display[col].astype(int)
            
            st.dataframe(
                pitching_display,
                use_container_width=True,
                hide_index=True,
                height=400
            )
            
            # Gráficos
            st.markdown("---")
            col1, col2 = st.columns(2)

            with col1:
                # Top 10 ERA
                top_era = pitching_qualified.nsmallest(10, 'ERA')
                fig_era = px.bar(
                    top_era,
                    x='ERA',
                    y='player_name',
                    orientation='h',
                    title='Top 10 - Mejor ERA',
                    labels={'ERA': 'ERA', 'player_name': ''},
                    color='ERA',
                    color_continuous_scale=['#196F3D', '#FDB827', '#922B21']
                )
                fig_era.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig_era, use_container_width=True)
            
            with col2:
                # Ponches vs WHIP
                fig_efficiency = px.scatter(
                    pitching_qualified,
                    x='so',
                    y='WHIP',
                    size='ip_decimal',
                    hover_data=['player_name'],
                    title='Efectividad: Ponches vs WHIP',
                    labels={'so': 'Ponches', 'WHIP': 'WHIP'},
                    color='ERA',
                    color_continuous_scale=['#196F3D', '#FDB827', '#922B21']
                )
                fig_efficiency.update_layout(height=400)
                st.plotly_chart(fig_efficiency, use_container_width=True)
            
        else:
            st.info("No hay estadísticas de pitcheo disponibles para esta temporada")
            
    except Exception as e:
        st.error(f"Error al cargar estadísticas de pitcheo: {str(e)}")

# Footer con información adicional
st.markdown("---")

# Leyenda y explicación de estadísticas
with st.expander("📖 Glosario de Estadísticas"):
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Estadísticas de Bateo:**
        - **VB**: Veces al Bate
        - **CA**: Carreras Anotadas
        - **H**: Hits
        - **2B/3B/HR**: Dobles/Triples/Jonrones
        - **CI**: Carreras Impulsadas
        - **BB**: Bases por Bolas
        - **SO**: Ponches
        - **BR**: Bases Robadas
        - **AVG**: Promedio de Bateo (H/VB)
        - **OBP**: Porcentaje de Embasado
        - **SLG**: Slugging (Bases Totales/VB)
        - **OPS**: OBP + SLG
        """)
    
    with col2:
        st.markdown("""
        **Estadísticas de Pitcheo:**
        - **IP**: Innings Lanzados
        - **H**: Hits Permitidos
        - **C/CL**: Carreras/Carreras Limpias
        - **BB**: Bases por Bolas
        - **SO**: Ponches
        - **HR**: Jonrones Permitidos
        - **ERA**: Promedio de Carreras Limpias
        - **WHIP**: (BB + H) / IP
        - **K/9**: Ponches por 9 innings
        - **BB/9**: Bases por Bolas por 9 innings
        """)

# Información de actualización
st.markdown("""
<div style='text-align: center; color: #666; padding: 2rem;'>
    <p>📊 Estadísticas actualizadas diariamente</p>
    <p>Mínimo 10 VB para calificar en bateo | Mínimo 5 IP para calificar en pitcheo</p>
</div>
""", unsafe_allow_html=True)

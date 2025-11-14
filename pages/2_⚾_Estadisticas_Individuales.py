# streamlit_app/pages/2_⚾_Estadisticas_Individuales.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.supabase_client import init_supabase, get_batting_stats, get_pitching_stats

st.set_page_config(page_title="Estadísticas Individuales", page_icon="⚾", layout="wide")

st.title("⚾ Estadísticas Individuales")
st.markdown("### Líderes y estadísticas por jugador - LVBP 2024-2025")

# Tabs principales
tab1, tab2, tab3, tab4 = st.tabs(["🏏 Líderes de Bateo", "⚾ Líderes de Pitcheo", "🔍 Buscador", "📊 Comparador"])

with tab1:
    st.markdown("### 🏏 Líderes de Bateo")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        # Filtros
        st.markdown("#### Filtros")
        
        team_filter = st.selectbox(
            "Equipo",
            ["Todos", "Leones del Caracas", "Navegantes", "Tigres", "Caribes", "Águilas", "Cardenales", "Tiburones", "Bravos"]
        )
        
        min_ab = st.slider("Mínimo de turnos al bate", 0, 200, 50)
        
        stat_type = st.selectbox(
            "Ordenar por",
            ["AVG", "OPS", "HR", "RBI", "H", "R", "SB"]
        )
    
    with col2:
        # Obtener datos
        supabase = init_supabase()
        
        # Query para estadísticas de bateo
        query = """
        SELECT 
            p.full_name,
            p.jersey_number,
            t.name as team_name,
            COUNT(DISTINCT bs.game_id) as games,
            SUM(bs.ab) as ab,
            SUM(bs.r) as r,
            SUM(bs.h) as h,
            SUM(bs.doubles) as doubles,
            SUM(bs.triples) as triples,
            SUM(bs.hr) as hr,
            SUM(bs.rbi) as rbi,
            SUM(bs.bb) as bb,
            SUM(bs.so) as so,
            SUM(bs.sb) as sb,
            CASE WHEN SUM(bs.ab) > 0 
                THEN ROUND(SUM(bs.h)::DECIMAL / SUM(bs.ab), 3) 
                ELSE 0 END as avg,
            CASE WHEN (SUM(bs.ab) + SUM(bs.bb)) > 0
                THEN ROUND((SUM(bs.h) + SUM(bs.bb))::DECIMAL / (SUM(bs.ab) + SUM(bs.bb)), 3)
                ELSE 0 END as obp,
            CASE WHEN SUM(bs.ab) > 0
                THEN ROUND((SUM(bs.h) + SUM(bs.doubles) + 2*SUM(bs.triples) + 3*SUM(bs.hr))::DECIMAL / SUM(bs.ab), 3)
                ELSE 0 END as slg
        FROM batting_stats bs
        JOIN players p ON bs.player_id = p.id
        JOIN teams t ON p.team_id = t.id
        JOIN games g ON bs.game_id = g.id
        WHERE g.season = 2025
        GROUP BY p.id, p.full_name, p.jersey_number, t.name
        HAVING SUM(bs.ab) >= %s
        """
        
        # Por ahora usar una query más simple
        response = supabase.table('batting_stats') \
            .select('*, players!inner(full_name, jersey_number), teams!inner(name)') \
            .execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            
            # Agrupar por jugador
            batting_leaders = df.groupby(['players', 'teams']).agg({
                'ab': 'sum',
                'r': 'sum',
                'h': 'sum',
                'doubles': 'sum',
                'triples': 'sum',
                'hr': 'sum',
                'rbi': 'sum',
                'bb': 'sum',
                'so': 'sum',
                'sb': 'sum'
            }).reset_index()
            
            # Extraer nombres
            batting_leaders['Jugador'] = batting_leaders['players'].apply(lambda x: x['full_name'] if isinstance(x, dict) else 'Unknown')
            batting_leaders['Equipo'] = batting_leaders['teams'].apply(lambda x: x['name'] if isinstance(x, dict) else 'Unknown')
            
            # Calcular estadísticas
            batting_leaders['AVG'] = (batting_leaders['h'] / batting_leaders['ab']).round(3).fillna(0)
            batting_leaders['OBP'] = ((batting_leaders['h'] + batting_leaders['bb']) / (batting_leaders['ab'] + batting_leaders['bb'])).round(3).fillna(0)
            batting_leaders['SLG'] = ((batting_leaders['h'] + batting_leaders['doubles'] + 2*batting_leaders['triples'] + 3*batting_leaders['hr']) / batting_leaders['ab']).round(3).fillna(0)
            batting_leaders['OPS'] = (batting_leaders['OBP'] + batting_leaders['SLG']).round(3)
            
            # Filtrar por mínimo de AB
            batting_leaders = batting_leaders[batting_leaders['ab'] >= min_ab]
            
            # Filtrar por equipo si se seleccionó
            if team_filter != "Todos":
                batting_leaders = batting_leaders[batting_leaders['Equipo'].str.contains(team_filter)]
            
            # Ordenar por estadística seleccionada
            sort_column = stat_type if stat_type in batting_leaders.columns else 'AVG'
            batting_leaders = batting_leaders.sort_values(sort_column, ascending=False)
            
            # Mostrar tabla
            display_cols = ['Jugador', 'Equipo', 'ab', 'AVG', 'OBP', 'SLG', 'OPS', 'hr', 'rbi', 'r', 'h', 'bb', 'so', 'sb']
            display_df = batting_leaders[display_cols].head(20)
            display_df.columns = ['Jugador', 'Equipo', 'VB', 'AVG', 'OBP', 'SLG', 'OPS', 'HR', 'CI', 'CA', 'H', 'BB', 'K', 'BR']
            
            # Formatear decimales
            for col in ['AVG', 'OBP', 'SLG', 'OPS']:
                display_df[col] = display_df[col].apply(lambda x: f'.{int(x*1000):03d}' if x > 0 else '.000')
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # Gráficos
            st.markdown("---")
            col1, col2 = st.columns(2)
            
            with col1:
                # Top 10 AVG
                top_avg = batting_leaders.nlargest(10, 'AVG')
                fig_avg = px.bar(
                    top_avg,
                    x='AVG',
                    y='Jugador',
                    orientation='h',
                    title='Top 10 - Promedio de Bateo',
                    color='AVG',
                    color_continuous_scale='RdYlGn'
                )
                fig_avg.update_layout(height=400)
                st.plotly_chart(fig_avg, use_container_width=True)
            
            with col2:
                # Top 10 HR
                top_hr = batting_leaders.nlargest(10, 'hr')
                fig_hr = px.bar(
                    top_hr,
                    x='hr',
                    y='Jugador',
                    orientation='h',
                    title='Top 10 - Jonrones',
                    color='hr',
                    color_continuous_scale='Reds'
                )
                fig_hr.update_layout(height=400)
                st.plotly_chart(fig_hr, use_container_width=True)

with tab2:
    st.markdown("### ⚾ Líderes de Pitcheo")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        # Filtros
        st.markdown("#### Filtros")
        
        team_filter_p = st.selectbox(
            "Equipo",
            ["Todos", "Leones del Caracas", "Navegantes", "Tigres", "Caribes", "Águilas", "Cardenales", "Tiburones", "Bravos"],
            key="team_filter_pitching"
        )
        
        min_ip = st.slider("Mínimo de innings", 0, 50, 10)
        
        stat_type_p = st.selectbox(
            "Ordenar por",
            ["ERA", "WHIP", "SO", "W", "SV", "IP"],
            key="stat_type_pitching"
        )
    
    with col2:
        # Obtener datos de pitcheo
        response = supabase.table('pitching_stats') \
            .select('*, players!inner(full_name, jersey_number), teams!inner(name)') \
            .execute()
        
        if response.data:
            df_p = pd.DataFrame(response.data)
            
            # Agrupar por jugador
            pitching_leaders = df_p.groupby(['players', 'teams']).agg({
                'ip_decimal': 'sum',
                'h': 'sum',
                'r': 'sum',
                'er': 'sum',
                'bb': 'sum',
                'so': 'sum',
                'hr': 'sum',
                'hbp': 'sum',
                'wp': 'sum'
            }).reset_index()
            
            # Extraer nombres
            pitching_leaders['Jugador'] = pitching_leaders['players'].apply(lambda x: x['full_name'] if isinstance(x, dict) else 'Unknown')
            pitching_leaders['Equipo'] = pitching_leaders['teams'].apply(lambda x: x['name'] if isinstance(x, dict) else 'Unknown')
            
            # Calcular estadísticas
            pitching_leaders['ERA'] = (9 * pitching_leaders['er'] / pitching_leaders['ip_decimal']).round(2).fillna(0)
            pitching_leaders['WHIP'] = ((pitching_leaders['bb'] + pitching_leaders['h']) / pitching_leaders['ip_decimal']).round(3).fillna(0)
            pitching_leaders['K/9'] = (9 * pitching_leaders['so'] / pitching_leaders['ip_decimal']).round(2).fillna(0)
            pitching_leaders['BB/9'] = (9 * pitching_leaders['bb'] / pitching_leaders['ip_decimal']).round(2).fillna(0)
            
            # Filtrar por mínimo de IP
            pitching_leaders = pitching_leaders[pitching_leaders['ip_decimal'] >= min_ip]
            
            # Filtrar por equipo si se seleccionó
            if team_filter_p != "Todos":
                pitching_leaders = pitching_leaders[pitching_leaders['Equipo'].str.contains(team_filter_p)]
            
            # Ordenar
            sort_map = {'ERA': 'ERA', 'WHIP': 'WHIP', 'SO': 'so', 'IP': 'ip_decimal'}
            sort_col = sort_map.get(stat_type_p, 'ERA')
            ascending = sort_col in ['ERA', 'WHIP']
            pitching_leaders = pitching_leaders.sort_values(sort_col, ascending=ascending)
            
            # Mostrar tabla
            display_cols_p = ['Jugador', 'Equipo', 'ip_decimal', 'ERA                    'Estadística': ['Turnos', 'Hits', 'Promedio', 'Jonrones', 'Impulsadas'],
                    player1: [stats1['AB'], stats1['H'], f".{int(stats1['AVG']*1000):03d}", stats1['HR'], stats1['RBI']],
                    player2: [stats2['AB'], stats2['H'], f".{int(stats2['AVG']*1000):03d}", stats2['HR'], stats2['RBI']]
                })
                
                st.dataframe(comparison_df, use_container_width=True, hide_index=True)
                
            elif type1 == 'lanzador' and type2 == 'lanzador':
                # Comparación de lanzadores
                comparison_df = pd.DataFrame({
                    'Estadística': ['Innings', 'ERA', 'Ponches', 'Bases por bolas'],
                    player1: [f"{int(stats1['IP'])}.{int((stats1['IP'] % 1) * 3)}", 
                             f"{stats1['ERA']:.2f}", stats1['SO'], stats1['BB']],
                    player2: [f"{int(stats2['IP'])}.{int((stats2['IP'] % 1) * 3)}", 
                             f"{stats2['ERA']:.2f}", stats2['SO'], stats2['BB']]
                })
                
                st.dataframe(comparison_df, use_container_width=True, hide_index=True)
            else:
                st.warning("No se pueden comparar un bateador con un lanzador")
        else:
            st.error("No se encontraron estadísticas para uno o ambos jugadores")
    elif player1 == player2:
        st.warning("Por favor selecciona dos jugadores diferentes")
# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>📊 Estadísticas actualizadas diariamente | Fuente: MLB Stats API</p>
</div>
""", unsafe_allow_html=True)

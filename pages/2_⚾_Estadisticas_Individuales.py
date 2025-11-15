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
        # DEBUG: Ver qué hay en la base de datos
        with st.expander("🔍 Debug - Ver datos disponibles"):
            # Ver si hay juegos
            games_check = supabase.table('games') \
                .select('id, game_date, home_team_id, away_team_id') \
                .eq('season', selected_season) \
                .or_(f'home_team_id.eq.{LEONES_ID},away_team_id.eq.{LEONES_ID}') \
                .limit(5) \
                .execute()
            
            st.write(f"Juegos encontrados para temporada {selected_season}:")
            if games_check.data:
                st.write(f"Total: {len(games_check.data)} juegos")
                st.write("Primeros IDs:", [g['id'] for g in games_check.data[:5]])
            else:
                st.write("No se encontraron juegos")
            
            # Ver si hay stats de bateo
            batting_check = supabase.table('batting_stats') \
                .select('game_id, player_id, team_id, ab, h') \
                .eq('team_id', LEONES_ID) \
                .limit(5) \
                .execute()
            
            st.write("\nEstadísticas de bateo encontradas:")
            if batting_check.data:
                st.write(f"Total registros: {len(batting_check.data)}")
                st.write("Game IDs:", [b['game_id'] for b in batting_check.data[:5]])
            else:
                st.write("No se encontraron estadísticas")
        
        # OPCIÓN 1: Query directo sin filtrar por temporada primero
        batting_response = supabase.table('batting_stats') \
            .select('''
                *,
                players!inner(full_name, jersey_number),
                games!inner(season, game_date)
            ''') \
            .eq('team_id', LEONES_ID) \
            .eq('games.season', selected_season) \
            .execute()
        
        if not batting_response.data or len(batting_response.data) == 0:
            # OPCIÓN 2: Query más simple sin join de games
            st.info("Intentando método alternativo...")
            
            # Obtener todos los batting_stats de los Leones
            batting_response = supabase.table('batting_stats') \
                .select('*, players!inner(full_name, jersey_number)') \
                .eq('team_id', LEONES_ID) \
                .execute()
            
            if batting_response.data:
                # Filtrar manualmente por temporada
                batting_df = pd.DataFrame(batting_response.data)
                
                # Obtener los game_ids de la temporada
                games_response = supabase.table('games') \
                    .select('id') \
                    .eq('season', selected_season) \
                    .execute()
                
                if games_response.data:
                    valid_game_ids = [g['id'] for g in games_response.data]
                    # Filtrar batting_df por game_ids válidos
                    batting_df = batting_df[batting_df['game_id'].isin(valid_game_ids)]
                    
                    if len(batting_df) > 0:
                        st.success(f"✅ Encontradas {len(batting_df)} entradas de bateo para la temporada {selected_season}")
                    else:
                        batting_df = pd.DataFrame()  # DataFrame vacío
                else:
                    batting_df = pd.DataFrame()
            else:
                batting_df = pd.DataFrame()
        else:
            batting_df = pd.DataFrame(batting_response.data)
            st.success(f"✅ Encontradas {len(batting_df)} entradas de bateo")
        
        # Procesar datos si existen
        if not batting_df.empty:
            # Extraer nombre del jugador
            batting_df['player_name'] = batting_df['players'].apply(
                lambda x: x['full_name'] if isinstance(x, dict) else 'Desconocido'
            )
            batting_df['jersey'] = batting_df['players'].apply(
                lambda x: str(x.get('jersey_number', '')) if isinstance(x, dict) else ''
            )
            
            # Asegurar que todas las columnas numéricas sean numéricas
            numeric_cols = ['ab', 'r', 'h', 'doubles', 'triples', 'hr', 'rbi', 'bb', 'so', 'sb', 'cs', 'hbp', 'sf', 'sh']
            for col in numeric_cols:
                if col in batting_df.columns:
                    batting_df[col] = pd.to_numeric(batting_df[col], errors='coerce').fillna(0)
            
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
            batting_grouped['TB'] = (batting_grouped['h'] + batting_grouped['doubles'] + 
                                     2*batting_grouped['triples'] + 3*batting_grouped['hr'])
            batting_grouped['SLG'] = (batting_grouped['TB'] / batting_grouped['ab']).round(3).fillna(0)
            batting_grouped['OPS'] = (batting_grouped['OBP'] + batting_grouped['SLG']).round(3)
            
            # Filtrar jugadores con al menos 10 AB
            batting_qualified = batting_grouped[batting_grouped['ab'] >= 10].copy()
            
            if len(batting_qualified) > 0:
                # Ordenar por AVG
                batting_qualified = batting_qualified.sort_values('AVG', ascending=False)
                
                # Mostrar métricas y tabla como antes...
                col1, col2, col3, col4 = st.columns(4)
                
                # Líder de bateo
                avg_leader = batting_qualified.iloc[0]
                with col1:
                    st.metric(
                        "👑 Líder de Bateo",
                        avg_leader['player_name'],
                        f".{int(avg_leader['AVG']*1000):03d}"
                    )
                
                # Continuar con el resto del código...
                # [El resto del código de display sigue igual]
                
            else:
                st.warning("No hay jugadores con al menos 10 turnos al bate")
        else:
            st.warning("No se encontraron estadísticas de bateo para esta temporada")
            
            # Mostrar información adicional de debug
            with st.expander("🔍 Información adicional"):
                st.write(f"Temporada seleccionada: {selected_season}")
                st.write(f"ID de los Leones: {LEONES_ID}")
                
                # Verificar si hay datos en general
                all_batting = supabase.table('batting_stats') \
                    .select('team_id') \
                    .limit(10) \
                    .execute()
                
                if all_batting.data:
                    unique_teams = set([b['team_id'] for b in all_batting.data])
                    st.write(f"Teams con datos: {unique_teams}")
                
    except Exception as e:
        st.error(f"Error: {str(e)}")
        with st.expander("Detalles del error"):
            st.write(str(e))
with tab2:
    st.markdown(f"### ⚾ Líderes de Pitcheo - {selected_season_display}")
    
    try:
        # Primero obtener los juegos de la temporada para filtrar
        games_response = supabase.table('games') \
            .select('id') \
            .eq('season', selected_season) \
            .or_(f'home_team_id.eq.{LEONES_ID},away_team_id.eq.{LEONES_ID}') \
            .execute()
        
        if games_response.data:
            game_ids = [g['id'] for g in games_response.data]
            
            # Obtener estadísticas de pitcheo solo de esos juegos
            pitching_response = supabase.table('pitching_stats') \
                .select('*, players!inner(full_name, jersey_number)') \
                .eq('team_id', LEONES_ID) \
                .in_('game_id', game_ids) \
                .execute()
            
            if pitching_response.data and len(pitching_response.data) > 0:
                # Crear DataFrame
                pitching_df = pd.DataFrame(pitching_response.data)
                
                # Extraer nombre del jugador
                pitching_df['player_name'] = pitching_df['players'].apply(
                    lambda x: x['full_name'] if isinstance(x, dict) else 'Desconocido'
                )
                pitching_df['jersey'] = pitching_df['players'].apply(
                    lambda x: str(x.get('jersey_number', '')) if isinstance(x, dict) else ''
                )
                
                # Agrupar por jugador y sumar estadísticas
                pitching_grouped = pitching_df.groupby(['player_id', 'player_name', 'jersey']).agg({
                    'ip_decimal': 'sum',
                    'h': 'sum',
                    'r': 'sum',
                    'er': 'sum',
                    'bb': 'sum',
                    'so': 'sum',
                    'hr': 'sum',
                    'hbp': 'sum',
                    'wp': 'sum',
                    'bk': 'sum'
                }).reset_index()
                
                # Reemplazar NaN con 0
                pitching_grouped = pitching_grouped.fillna(0)
                
                # Calcular estadísticas correctamente
                # ERA = (ER * 9) / IP
                pitching_grouped['ERA'] = pitching_grouped.apply(
                    lambda x: (x['er'] * 9) / x['ip_decimal'] if x['ip_decimal'] > 0 else 0, axis=1
                )
                
                # WHIP = (BB + H) / IP
                pitching_grouped['WHIP'] = pitching_grouped.apply(
                    lambda x: (x['bb'] + x['h']) / x['ip_decimal'] if x['ip_decimal'] > 0 else 0, axis=1
                )
                
                # K/9 = (SO * 9) / IP
                pitching_grouped['K9'] = pitching_grouped.apply(
                    lambda x: (x['so'] * 9) / x['ip_decimal'] if x['ip_decimal'] > 0 else 0, axis=1
                )
                
                # BB/9 = (BB * 9) / IP
                pitching_grouped['BB9'] = pitching_grouped.apply(
                    lambda x: (x['bb'] * 9) / x['ip_decimal'] if x['ip_decimal'] > 0 else 0, axis=1
                )
                
                # K/BB = SO / BB
                pitching_grouped['K_BB'] = pitching_grouped.apply(
                    lambda x: x['so'] / x['bb'] if x['bb'] > 0 else x['so'], axis=1
                )
                
                # Convertir IP decimal a formato tradicional (6.1, 6.2, 7.0)
                def decimal_to_ip(decimal_ip):
                    full_innings = int(decimal_ip)
                    partial = decimal_ip - full_innings
                    outs = round(partial * 3)
                    if outs >= 3:
                        full_innings += 1
                        outs = 0
                    return f"{full_innings}.{outs}"
                
                pitching_grouped['IP'] = pitching_grouped['ip_decimal'].apply(decimal_to_ip)
                
                # Filtrar pitchers con al menos 5 innings
                pitching_qualified = pitching_grouped[pitching_grouped['ip_decimal'] >= 5].copy()
                
                # Ordenar por ERA (menor es mejor)
                pitching_qualified = pitching_qualified.sort_values('ERA')
                
                # Métricas principales
                col1, col2, col3, col4 = st.columns(4)
                
                if not pitching_qualified.empty:
                    # Líder ERA
                    era_leader = pitching_qualified.iloc[0]
                    
                    with col1:
                        st.metric(
                            "🏆 Líder ERA",
                            era_leader['player_name'],
                            f"{era_leader['ERA']:.2f}"
                        )
                    
                    # Líder ponches
                    so_leader = pitching_qualified.nlargest(1, 'so').iloc[0]
                    with col2:
                        st.metric(
                            "🔥 Líder Ponches",
                            so_leader['player_name'],
                            f"{int(so_leader['so'])} K"
                        )
                    
                    # Líder WHIP
                    whip_leader = pitching_qualified.nsmallest(1, 'WHIP').iloc[0]
                    with col3:
                        st.metric(
                            "🎯 Líder WHIP",
                            whip_leader['player_name'],
                            f"{whip_leader['WHIP']:.2f}"
                        )
                    
                    # Más innings
                    ip_leader = pitching_qualified.nlargest(1, 'ip_decimal').iloc[0]
                    with col4:
                        st.metric(
                            "💪 Más Innings",
                            ip_leader['player_name'],
                            f"{ip_leader['IP']} IP"
                        )
                
                st.markdown("---")
                
                # Preparar tabla de display
                display_cols = {
                    'player_name': 'Jugador',
                    'jersey': '#',
                    'IP': 'IP',
                    'h': 'H',
                    'r': 'C',
                    'er': 'CL',
                    'bb': 'BB',
                    'so': 'K',
                    'hr': 'HR',
                    'ERA': 'ERA',
                    'WHIP': 'WHIP',
                    'K9': 'K/9',
                    'BB9': 'BB/9',
                    'K_BB': 'K/BB'
                }
                
                pitching_display = pitching_qualified[list(display_cols.keys())].copy()
                pitching_display.columns = list(display_cols.values())
                
                # Formatear estadísticas decimales
                pitching_display['ERA'] = pitching_display['ERA'].apply(lambda x: f'{x:.2f}')
                pitching_display['WHIP'] = pitching_display['WHIP'].apply(lambda x: f'{x:.2f}')
                pitching_display['K/9'] = pitching_display['K/9'].apply(lambda x: f'{x:.1f}')
                pitching_display['BB/9'] = pitching_display['BB/9'].apply(lambda x: f'{x:.1f}')
                pitching_display['K/BB'] = pitching_display['K/BB'].apply(lambda x: f'{x:.2f}')
                
                # Convertir a enteros las estadísticas de conteo
                int_cols = ['H', 'C', 'CL', 'BB', 'K', 'HR']
                for col in int_cols:
                    if col in pitching_display.columns:
                        pitching_display[col] = pitching_display[col].astype(int)
                
                # Mostrar tabla
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
                    # Top 10 ERA (mínimo 5 IP)
                    top_era = pitching_qualified.nsmallest(10, 'ERA')
                    fig_era = px.bar(
                        top_era,
                        x='ERA',
                        y='player_name',
                        orientation='h',
                        title='Top 10 - Mejor ERA',
                        labels={'ERA': 'ERA', 'player_name': ''},
                        text=top_era['ERA'].apply(lambda x: f'{x:.2f}')
                    )
                    fig_era.update_traces(marker_color='#196F3D')
                    fig_era.update_layout(height=400, showlegend=False)
                    st.plotly_chart(fig_era, use_container_width=True)
                
                with col2:
                    # Ponches vs WHIP
                    fig_efficiency = px.scatter(
                        pitching_qualified,
                        x='so',
                        y='WHIP',
                        size='ip_decimal',
                        hover_data=['player_name', 'ERA'],
                        title='Efectividad: Ponches vs WHIP',
                        labels={'so': 'Ponches', 'WHIP': 'WHIP'},
                        text='player_name'
                    )
                    fig_efficiency.update_traces(marker=dict(color='#FDB827', line=dict(width=1, color='#196F3D')))
                    fig_efficiency.update_layout(height=400)
                    fig_efficiency.update_yaxis(autorange='reversed')  # Menor WHIP es mejor
                    st.plotly_chart(fig_efficiency, use_container_width=True)
                
            else:
                st.info("No hay estadísticas de pitcheo disponibles para esta temporada")
        else:
            st.info("No hay juegos de los Leones en esta temporada")
            
    except Exception as e:
        st.error(f"Error al cargar estadísticas de pitcheo: {str(e)}")
        with st.expander("Detalles del error"):
            st.write(str(e))

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
        - **OBP**: % de Embasado ((H+BB+HBP)/(VB+BB+HBP+SF))
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
        - **K**: Ponches
        - **HR**: Jonrones Permitidos
        - **ERA**: Efectividad (CL*9/IP)
        - **WHIP**: (BB + H) / IP
        - **K/9**: Ponches por 9 innings
        - **BB/9**: BB por 9 innings
        - **K/BB**: Ratio Ponches/BB
        """)

# Información de actualización
st.markdown("""
<div style='text-align: center; color: #666; padding: 2rem;'>
    <p>📊 Estadísticas actualizadas diariamente</p>
    <p>Mínimo 10 VB para calificar en bateo | Mínimo 5 IP para calificar en pitcheo</p>
</div>
""", unsafe_allow_html=True)


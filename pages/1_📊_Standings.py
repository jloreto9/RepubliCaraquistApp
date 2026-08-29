# pages/Standings.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys
import os

# Agregar el directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar funciones
from utils.supabase_client import (
    get_standings,
    get_recent_games,
    init_supabase,
    get_available_seasons,
    get_current_season,
    get_leones_advanced_stats,
    get_weekly_records
)
from utils.teams import (
    LVBP_TEAMS,
    LVBP_ABBR,
    LVBP_COLORS,
    get_team_logo,
    get_team_name,
    get_team_abbr,
    get_team_color,
    resolve_team_id,
    get_brand_logo
)
from utils.elo import (
    calculate_matchup_win_prob,
    simulate_monte_carlo_projections,
    BASE_ELO,
    HOME_ADVANTAGE
)

ELO_PHASE_OPTIONS = {
    "regular": "1. Temporada Regular",
    "wildcard_playin": "2. Serie del Comodín (Wild Card)",
    "round_robin": "3. Round Robin (Todos contra Todos)",
    "final": "4. Serie Final",
}


def load_elo_ratings_for_phase(season, phase):
    """Lee ratings ELO persistidos sin recalcular."""
    supabase = init_supabase()
    try:
        response = supabase.table("elo_ratings") \
            .select("team_id, elo, games_played, updated_at, teams(name, abbreviation)") \
            .eq("season", season) \
            .eq("phase", phase) \
            .order("elo", desc=True) \
            .execute()
    except Exception as e:
        st.error(f"Error cargando ELO: {str(e)}")
        return pd.DataFrame()

    if not response.data:
        return pd.DataFrame()

    df = pd.DataFrame(response.data)
    if "teams" in df.columns:
        df["team_name"] = df["teams"].apply(
            lambda x: x.get("name", "N/A") if isinstance(x, dict) else "N/A"
        )
    else:
        df["team_name"] = "N/A"

    df = df.sort_values("elo", ascending=False).reset_index(drop=True)
    df.insert(0, "rank", range(1, len(df) + 1))
    return df


@st.cache_data(ttl=600, show_spinner=False)
def run_elo_simulations_cached(season: int, simulate_from_scratch: bool = False) -> dict:
    """Ejecuta y cachea simulaciones Monte Carlo basadas en ELO y standings."""
    standings_df = get_standings(season, phase="regular")
    elo_df = load_elo_ratings_for_phase(season, "regular")

    elo_dict = {}
    if not elo_df.empty:
        for _, r in elo_df.iterrows():
            try:
                tid = int(r["team_id"])
                elo_dict[tid] = float(r["elo"])
            except:
                pass

    # Fallback si falta algún equipo
    for tid in LVBP_TEAMS.keys():
        if tid not in elo_dict:
            elo_dict[tid] = float(BASE_ELO)

    return simulate_monte_carlo_projections(
        standings_df=standings_df,
        elo_dict=elo_dict,
        n_simulations=5000,
        simulate_from_scratch=simulate_from_scratch
    )


@st.cache_data(ttl=300, show_spinner=False)
def get_calendar_games_with_elo_projections(season: int) -> pd.DataFrame:
    """Obtiene partidos del calendario oficial y calcula probabilidades ELO reales."""
    supabase = init_supabase()
    elo_regular_df = load_elo_ratings_for_phase(season, "regular")
    current_elos = {}
    if not elo_regular_df.empty:
        for _, r in elo_regular_df.iterrows():
            try:
                current_elos[int(r["team_id"])] = float(r["elo"])
            except:
                pass
    for tid in LVBP_TEAMS.keys():
        if tid not in current_elos:
            current_elos[tid] = float(BASE_ELO)

    try:
        cal_games_res = supabase.table('games') \
            .select('*') \
            .eq('season', season) \
            .order('game_date', desc=True) \
            .limit(100) \
            .execute()
        cal_games = cal_games_res.data or []
    except Exception:
        cal_games = []

    if not cal_games:
        return pd.DataFrame()

    cal_rows = []
    for g in cal_games:
        h_id = g.get('home_team_id')
        a_id = g.get('away_team_id')
        if h_id in LVBP_TEAMS and a_id in LVBP_TEAMS:
            h_elo = current_elos.get(h_id, BASE_ELO)
            a_elo = current_elos.get(a_id, BASE_ELO)
            p_h, p_a = calculate_matchup_win_prob(h_elo, a_elo, HOME_ADVANTAGE)
            
            h_name = LVBP_TEAMS[h_id]
            a_name = LVBP_TEAMS[a_id]
            fav_name = h_name if p_h >= 0.5 else a_name
            fav_pct = max(p_h, p_a)
            
            st_val = g.get('status', 'Final')
            is_fin = st_val in ['Final', 'Completed Early', 'Game Over']
            h_sc = g.get('home_score', 0)
            a_sc = g.get('away_score', 0)
            real_res = f"{h_sc} - {a_sc}" if is_fin else st_val
            
            cal_rows.append({
                'id': g.get('id'),
                'game_date': str(g.get('game_date', ''))[:10],
                'home_id': h_id,
                'away_id': a_id,
                'Local_Logo': get_team_logo(h_id, size=72),
                'Local': h_name,
                'Visitante_Logo': get_team_logo(a_id, size=72),
                'Visitante': a_name,
                'ELO Local': f"{h_elo:.1f}",
                'ELO Visitante': f"{a_elo:.1f}",
                'Prob. Local': f"{p_h:.1%}",
                'Prob. Visitante': f"{p_a:.1%}",
                'Favorito ELO': f"{fav_name} ({fav_pct:.1%})",
                'Marcador / Estado': real_res
            })
    return pd.DataFrame(cal_rows)


st.set_page_config(page_title="Standings - RepubliCaraquistApp", page_icon="📊", layout="wide")

try:
    from utils.styles import inject_custom_css
    inject_custom_css()
except:
    pass

# Sidebar con Logo Oficial República Caraquista
with st.sidebar:
    st.image(get_brand_logo(), width=200)
    st.markdown("---")

# Header
col_h_logo, col_h_txt = st.columns([1, 8])
with col_h_logo:
    st.image(get_brand_logo(), width=75)
with col_h_txt:
    st.title("📊 Standings y Resultados")
    st.markdown("### Tabla de Posiciones, Sabermetría Pitagórica y Ratings ELO — LVBP")

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
        display_text = f"{season}-{season+1}"
        season_options[display_text] = season    # Determinar índice de la temporada (por defecto 2025-2026 si existe)
    current_season_display = f"{current_season}-{current_season+1}"
    season_list = list(season_options.keys())
    default_index = 0
    for idx, s in enumerate(available_seasons):
        if s == 2025:
            default_index = idx
            break

    # Selector de temporada
    selected_season_display = st.selectbox(
        "⚾ Seleccionar Temporada",
        options=season_list,
        index=default_index
    )

    selected_season = season_options[selected_season_display]

with col2:
    STANDINGS_PHASE_OPTIONS = {
        "regular": "Temporada Regular (56 JJ)",
        "round_robin": "Round Robin (Todos contra Todos)",
        "wildcard_playin": "Serie del Comodín (Wild Card)",
        "final": "Serie Final",
        "all": "Acumulado Total (Todas las Fases)"
    }
    selected_phase = st.selectbox(
        "🏆 Fase del Torneo",
        options=list(STANDINGS_PHASE_OPTIONS.keys()),
        format_func=lambda x: STANDINGS_PHASE_OPTIONS[x],
        index=0
    )

st.markdown(f"### Tabla de Posiciones - LVBP {selected_season_display} ({STANDINGS_PHASE_OPTIONS[selected_phase]})")

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

# Obtener standings de la base de datos por fase
standings_df = get_standings(selected_season, phase=selected_phase)

if not standings_df.empty:
    
    # Filtrar solo equipos de LVBP si hay otros
    if 'team_id' in standings_df.columns:
        standings_df = standings_df[standings_df['team_id'].isin(LVBP_TEAMS.keys())]
    elif 'team_name' in standings_df.columns:
        standings_df = standings_df[standings_df['team_name'].str.contains('|'.join([
            'Leones', 'Tiburones', 'Navegantes', 'Tigres', 
            'Águilas', 'Aguilas', 'Cardenales', 'Caribes', 'Bravos'
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
    tab1, tab_pyth, tab_elo, tab2, tab3, tab4 = st.tabs(["📊 Tabla General", "🧮 Sabermetría Pitagórica", "⚡ ELO & Proyecciones", "📈 Gráficos", "🆚 Head to Head", "📅 Calendario"])
    
    with tab1:
        # Formatear tabla de posiciones
        display_df = standings_df.copy()
        
        # Agregar logo y posición
        display_df.insert(0, 'Logo', display_df['team_name'].apply(lambda x: get_team_logo(x, size=72)))
        display_df.insert(1, 'Pos', range(1, len(display_df) + 1))
        
        # Seleccionar y renombrar columnas
        columns_to_show = {
            'Logo': ' ',
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
            
            styled_df = styled_df.map(color_diff, subset=['DIF'])
        
        st.dataframe(
            styled_df,
            column_config={
                ' ': st.column_config.ImageColumn(" ", width="small"),
                '#': st.column_config.NumberColumn("#", width="small")
            },
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
                st.metric("🏆 Posición", f"#{position}")
            
            with col2:
                wins = leones.get('wins', 0)
                losses = leones.get('losses', 0)
                st.metric("⚾ Récord", f"{wins}-{losses}")
            
            with col3:
                pct = leones.get('pct', 0)
                st.metric("📈 Porcentaje", f".{int(pct*1000):03d}")
            
            with col4:
                gb = leones.get('games_back', 0)
                st.metric("📏 Juegos Detrás", f"{gb:.1f}" if gb > 0 else "Líder")
            
            with col5:
                diff = leones.get('run_diff', 0)
                st.metric("🎯 Diferencial", f"{diff:+d}")

            # Desglose situacional avanzado
            adv = get_leones_advanced_stats(selected_season)
            if adv:
                sc1, sc2, sc3, sc4, sc5 = st.columns(5)
                with sc1:
                    st.metric("🏠 Home Club", adv.get('home_record', '-'))
                with sc2:
                    st.metric("✈️ Visitante", adv.get('away_record', '-'))
                with sc3:
                    st.metric("🌙 De Noche", adv.get('night_record', '-'))
                with sc4:
                    st.metric("☀️ De Día", adv.get('day_record', '-'))
                with sc5:
                    st.metric("⚡ 1 Carrera", adv.get('one_run', '-'))

            # Récord por semana de campeonato
            st.markdown("##### 📅 Récord por Semana de Campeonato")
            weekly_df = get_weekly_records(selected_season, team_id=695, phase=selected_phase)
            if not weekly_df.empty:
                st.dataframe(
                    weekly_df[["Semana", "Juegos", "G", "P", "PCT", "CF", "CP", "DIF", "Récord"]],
                    use_container_width=True,
                    hide_index=True
                )
        else:
            st.info("No hay datos de los Leones del Caracas para esta temporada")

        # Glosario y Leyenda Didáctica de la Tabla de Posiciones
        with st.expander("📖 Guía y Glosario: ¿Cómo entender la Tabla de Posiciones y Métricas?", expanded=False):
            st.markdown(r"""
            ### 📌 Glosario de la Tabla de Clasificación

            | Abreviatura / Métrica | Nombre Completo | ¿Qué significa y cómo se calcula? | ¿Cómo interpretarlo? (Valores de referencia) |
            |---|---|---|---|
            | **#** | Posición en la Tabla | Lugar numérico que ocupa el equipo en la clasificación oficial. | Los primeros 4 clasifican directo al Round Robin; 5° y 6° van a la Serie Comodín (Wild Card). |
            | **Equipo** | Franquicia | Nombre y escudo oficial del equipo en la LVBP. | Resaltado en dorado para los Leones del Caracas. |
            | **JJ** | Juegos Jugados | Cantidad total de partidos disputados en la temporada regular ($JJ = G + P$). | Temporada regular completa consta de 56 juegos por equipo. |
            | **G** | Ganados (Victorias) | Partidos en los que el equipo anotó más carreras que el rival. | Más es mejor. Un equipo con 30+ victorias casi siempre clasifica. |
            | **P** | Perdidos (Derrotas) | Partidos en los que el rival anotó más carreras. | Menos es mejor. |
            | **PCT** | Porcentaje de Victorias | Proporción de juegos ganados: $\text{PCT} = \frac{G}{JJ}$. Se expresa con tres decimales (ej. `.554`). | **>.600:** Nivel Élite / Puntero.<br>**>.500:** Récord positivo (más ganados que perdidos).<br>**<.450:** Temporada complicada en riesgo de eliminación. |
            | **JD / GB** | Juegos de Diferencia (Games Back) | Distancia matemática respecto al equipo en el 1er lugar: $\text{JD} = \frac{(G_{\text{líder}} - G) + (P - P_{\text{líder}})}{2}$. | **- / Líder:** El equipo está en la cima.<br>**1.0 a 3.0:** A tiro de alcanzar el liderato.<br>**6.0+:** Distancia considerable. |
            | **CF** | Carreras a Favor (RF) | Total de carreras anotadas por la ofensiva del equipo a lo largo del torneo. | Mide la potencia del bateo y corrido de bases del equipo. |
            | **CP** | Carreras en Contra (RA) | Total de carreras permitidas por el pitcheo y la defensa del equipo. | Menos es mejor. Mide la solidez defensiva y monticular. |
            | **DIF** | Diferencial de Carreras | Resta directa entre ataque y defensa: $\text{DIF} = CF - CP$. | **Positivo (+):** El equipo anota más de lo que recibe (equipo dominante).<br>**Negativo (-):** El equipo recibe más de lo que anota (vulnerabilidad). |
            | **Últimos 10 (L10)** | Récord Reciente | Victorias y derrotas en los últimos 10 juegos disputados. | Mide el momento actual de forma del equipo (ej. `7-3` indica gran momento). |
            | **Racha (Streak)** | Racha Activa | Juegos ganados o perdidos consecutivamente hasta la fecha. | `3 W` = 3 triunfos seguidos; `2 L` = 2 caídas al hilo. |

            ---

            ### 🏟️ Glosario de Desgloses Situacionales

            | Métrica Situacional | ¿Qué mide? | Interpretación Sabermétrica |
            |---|---|---|
            | **Home Club** | Récord jugando en el estadio sede como equipo local. | Ventaja de localía, bateo en último turno de cada inning y apoyo del público. |
            | **Visitante** | Récord en la carretera en estadios rivales. | Capacidad del equipo para ganar bajo hostilidad foránea. |
            | **De Noche** | Juegos iniciados a partir de las 7:00 PM. | Horario habitual estándar en el circuito LVBP. |
            | **De Día** | Juegos disputados en horario diurno (1:00 PM a 5:00 PM). | Frecuente en fines de semana; condiciones de sol y visibilidad distintas. |
            | **1 Carrera** | Partidos que terminan con margen de 1 carrera (ej. 4-3, 2-1). | Mide la solvencia del cerrador/bullpen en la 9na entrada y el oportunismo bajo máxima presión (clutch). |
            """)

    with tab_pyth:
        st.subheader("🧮 Expectativa Pitagórica de Victorias (Pythagorean Record)")
        st.markdown(
            "La fórmula pitagórica (Bill James / Davenport) calcula cuántas victorias **debió** ganar un equipo según sus carreras anotadas (CF) y permitidas (CP): "
            r"$W\% = \frac{CF^{1.83}}{CF^{1.83} + CP^{1.83}}$"
        )
        
        if not standings_df.empty and 'runs_for' in standings_df.columns and 'runs_against' in standings_df.columns:
            pyth_df = standings_df.copy()
            cf = pyth_df['runs_for'].astype(float)
            cp = pyth_df['runs_against'].astype(float)
            tot_games = pyth_df['wins'].astype(float) + pyth_df['losses'].astype(float)
            
            # Exponente estándar 1.83
            denom_pyth = (cf**1.83) + (cp**1.83)
            pyth_pct = np.where(denom_pyth > 0, (cf**1.83) / denom_pyth, 0.500)
            pyth_df['xW'] = (pyth_pct * tot_games).round(1)
            pyth_df['xL'] = (tot_games - pyth_df['xW']).round(1)
            pyth_df['W_diff'] = (pyth_df['wins'] - pyth_df['xW']).round(1)
            pyth_df['pyth_pct'] = pyth_pct
            
            # Métricas para Leones
            leones_p = pyth_df[pyth_df['team_name'].str.contains('Leones', case=False, na=False)]
            if not leones_p.empty:
                l_row = leones_p.iloc[0]
                pk1, pk2, pk3, pk4, pk5 = st.columns(5)
                with pk1:
                    st.metric("Victorias Reales", f"{int(l_row['wins'])}")
                with pk2:
                    st.metric("Victorias Esperadas (xW)", f"{l_row['xW']:.1f}")
                with pk3:
                    diff_val = l_row['W_diff']
                    st.metric(
                        "Diferencial (W - xW)",
                        f"{diff_val:+.1f}",
                        help="Positivo: Superó expectativa (clutch / suerte). Negativo: Récord inferior al rendimiento de carreras."
                    )
                with pk4:
                    rf_per_g = l_row['runs_for'] / (l_row['wins'] + l_row['losses']) if (l_row['wins'] + l_row['losses']) > 0 else 0
                    st.metric("Carreras Anotadas / J", f"{rf_per_g:.2f}")
                with pk5:
                    ra_per_g = l_row['runs_against'] / (l_row['wins'] + l_row['losses']) if (l_row['wins'] + l_row['losses']) > 0 else 0
                    st.metric("Carreras Permitidas / J", f"{ra_per_g:.2f}")
            
            st.markdown("---")
            
            # Tabla formateada
            pyth_display = pyth_df[['team_name', 'wins', 'losses', 'runs_for', 'runs_against', 'run_diff', 'pct', 'pyth_pct', 'xW', 'W_diff']].copy()
            pyth_display['Logo'] = pyth_display['team_name'].apply(lambda x: get_team_logo(x, size=72))
            pyth_display['pct_fmt'] = pyth_display['pct'].apply(lambda x: ".000" if pd.isna(x) else ("1.000" if x >= 1.0 else f".{int(x*1000):03d}"))
            pyth_display['pyth_fmt'] = pyth_display['pyth_pct'].apply(lambda x: ".500" if pd.isna(x) else ("1.000" if x >= 1.0 else f".{int(x*1000):03d}"))
            pyth_display['diff_fmt'] = pyth_display['W_diff'].apply(lambda x: f"{x:+.1f}")
            pyth_display['diagnostico'] = pyth_display['W_diff'].apply(
                lambda x: "🔥 Sobre-rendimiento (Clutch)" if x >= 1.5 else ("❄️ Sub-rendimiento (Mala Suerte)" if x <= -1.5 else "⚖️ En línea con lo esperado")
            )
            
            pyth_table_out = pyth_display[['Logo', 'team_name', 'wins', 'losses', 'runs_for', 'runs_against', 'run_diff', 'pct_fmt', 'pyth_fmt', 'xW', 'diff_fmt', 'diagnostico']].rename(columns={
                'Logo': ' ', 'team_name': 'Equipo', 'wins': 'G Reales', 'losses': 'P Reales', 'runs_for': 'CF', 'runs_against': 'CP',
                'run_diff': 'DIF', 'pct_fmt': 'PCT Real', 'pyth_fmt': 'PCT Pitagórico', 'xW': 'xW (Esperadas)',
                'diff_fmt': 'Dif (G - xW)', 'diagnostico': 'Diagnóstico Sabermétrico'
            })
            
            st.dataframe(
                pyth_table_out,
                column_config={' ': st.column_config.ImageColumn(" ", width="small")},
                use_container_width=True,
                hide_index=True
            )
            
            # Gráfico de dispersión: Real vs Esperado
            fig_pyth_scatter = px.scatter(
                pyth_df,
                x='xW',
                y='wins',
                text='team_name',
                title=f'Victorias Reales vs. Victorias Pitagóricas Esperadas - {selected_season_display}',
                labels={'xW': 'Victorias Esperadas (Pitagórico xW)', 'wins': 'Victorias Reales (W)'},
                color='W_diff',
                color_continuous_scale='RdYlGn',
                size=[15]*len(pyth_df)
            )
            fig_pyth_scatter.add_shape(
                type="line",
                x0=pyth_df['xW'].min()-1, x1=pyth_df['xW'].max()+1,
                y0=pyth_df['xW'].min()-1, y1=pyth_df['xW'].max()+1,
                line=dict(color="#ffffff", dash="dash", width=1.5)
            )
            fig_pyth_scatter.update_traces(textposition='top center')
            fig_pyth_scatter.update_layout(
                template='plotly_dark',
                height=450,
                coloraxis_colorbar_title="Dif (W-xW)"
            )
            st.plotly_chart(fig_pyth_scatter, use_container_width=True)

            with st.expander("📖 Guía y Glosario: ¿Cómo entender la Expectativa Pitagórica y la Suerte?", expanded=False):
                st.markdown(r"""
                ### 🧮 ¿Qué es el Récord Pitagórico?
                Inventado por el padre de la sabermetría **Bill James**, el modelo pitagórico demuestra que **el diferencial de carreras es un predictor mucho más fiel del nivel real de un equipo que su récord de victorias y derrotas**.

                | Métrica Pitagórica | Nombre / Fórmula | ¿Qué indica? |
                |---|---|---|
                | **xW (Victorias Esperadas)** | $JJ \times \frac{CF^{1.83}}{CF^{1.83} + CP^{1.83}}$ | La cantidad justa de partidos que el equipo debió haber ganado según las carreras que anotó y permitió. |
                | **xL (Derrotas Esperadas)** | $JJ - xW$ | Los juegos que el equipo debió perder según su balance de carreras. |
                | **PCT Pitagórico** | $\frac{CF^{1.83}}{CF^{1.83} + CP^{1.83}}$ | El porcentaje de victorias esperado matemáticamente. |
                | **Diferencial (G - xW)** | $G_{\text{Reales}} - xW$ | **Factor Suerte / Clutch:**<br>• **Positivo ($\ge +1.5$):** *Sobre-rendimiento.* El equipo ganó más juegos de lo esperado gracias a bateo oportuno o efectividad en juegos de 1 carrera.<br>• **Negativo ($\le -1.5$):** *Sub-rendimiento.* El equipo jugó mejor de lo que refleja su récord, pero sufrió derrotas dolorosas por mal bullpen o mala suerte en juegos cerrados.<br>• **Cercano a 0:** El récord refleja con exactitud la calidad del equipo. |
                """)
        else:
            st.info("Datos de carreras no disponibles para el cálculo pitagórico.")
            
    with tab_elo:
        st.subheader("⚡ Suite ELO & Simulaciones Probabilísticas Monte Carlo")
        st.markdown(
            "El sistema ELO evalúa la fuerza relativa de cada equipo de forma dinámica tras cada partido (+35 pts por localía). "
            "Mediante 5,000 iteraciones Monte Carlo, modelamos las probabilidades de clasificación regular, Wild Card, Round Robin y Campeonato LVBP."
        )

        with st.expander("📖 Guía y Glosario: ¿Cómo funciona el Rating ELO y Monte Carlo?", expanded=False):
            st.markdown(r"""
            ### ⚡ Rating ELO
            * **Base 1500:** Todos los equipos inician en 1500 puntos (promedio de la liga).
            * **Dinámica:** Si le ganas a un rival con mayor ELO, ganas muchos puntos. Si pierdes contra un equipo débil, pierdes más puntos.
            * **Ventaja de Localía (+35 pts):** Refleja la probabilidad histórica superior del equipo home club.

            ### 🎲 Simulaciones Monte Carlo (5,000 Iteraciones)
            * Cada iteración simula el calendario restante juego por juego utilizando las probabilidades exactas de victoria de cada enfrentamiento.
            * Permite calcular con rigor científico el **% de clasificar a Round Robin**, **% de alcanzar la Serie Final** y **% de coronarse Campeón**.
            """)

        elo_subtab1, elo_subtab2, elo_subtab3 = st.tabs([
            "🎲 Simulaciones Monte Carlo (Playoff & Campeón)",
            "🔮 Predictor de Partidos (Matchup Win %)",
            "⚡ Ratings ELO Oficiales"
        ])

        with elo_subtab1:
            st.markdown("#### 🎲 Proyecciones Monte Carlo de Temporada y Postemporada (5,000 Iteraciones)")
            st.caption(
                "Estructura reglamentaria LVBP: Puestos 1°-4° clasifican directo al Round Robin (16 JJ) | "
                "Puestos 5°-6° disputan la Serie del Comodín (el 5to necesita 1 victoria, el 6to necesita 2) | "
                "Los 2 mejores del Round Robin avanzan a la Gran Final (Serie de 7 JJ)."
            )

            col_opt1, col_opt2 = st.columns([3, 1])
            with col_opt1:
                sim_mode = st.radio(
                    "Modo de Simulación:",
                    [
                        "🏁 Proyección a partir del Standing Actual (Récord + ELO)",
                        "⚡ Baseline ELO de Temporada Completa (True-Talent 56 JJ)"
                    ],
                    horizontal=True,
                    key="elo_sim_mode_radio"
                )
            with col_opt2:
                recalc_btn = st.button("🔄 Re-ejecutar 5,000 Simulaciones", key="recalc_sim_btn")

            sim_scratch = "True-Talent" in sim_mode
            if recalc_btn:
                run_elo_simulations_cached.clear()

            with st.spinner("Ejecutando 5,000 simulaciones Monte Carlo..."):
                sim_results = run_elo_simulations_cached(selected_season, simulate_from_scratch=sim_scratch)

            df_proj = sim_results["projections"].copy()
            df_mat = sim_results["position_matrix"].copy()

            # Métricas destacadas de Leones del Caracas
            leones_sim = df_proj[df_proj["team_id"] == 695]
            if not leones_sim.empty:
                l_row = leones_sim.iloc[0]
                st.markdown("##### 🦁 Probabilidades de los Leones del Caracas")
                lm1, lm2, lm3, lm4, lm5 = st.columns(5)
                with lm1:
                    st.metric("Top 4 Directo (RR)", f"{l_row['top4_prob']:.1%}")
                with lm2:
                    st.metric("Serie Comodín (5°-6°)", f"{l_row['wc_prob']:.1%}")
                with lm3:
                    st.metric("Pase Total a Round Robin", f"{l_row['rr_prob']:.1%}")
                with lm4:
                    st.metric("Llegar a la Gran Final", f"{l_row['final_prob']:.1%}")
                with lm5:
                    st.metric("🏆 Ser Campeón LVBP", f"{l_row['champ_prob']:.1%}")

            st.markdown("---")

            # 1. Matriz de Probabilidades de Posición Final (1° al 8°)
            st.markdown("#### 🎯 Matriz de Probabilidad de Posición Final (Ronda Regular 1° al 8°)")
            
            # Formato visual
            disp_mat = df_mat.copy()
            disp_mat["Logo"] = disp_mat["team_name"].apply(lambda x: get_team_logo(x, size=72))
            for pos in range(1, 9):
                col_name = f"{pos}°"
                if col_name in disp_mat.columns:
                    disp_mat[col_name] = disp_mat[col_name].apply(lambda x: f"{x:.1%}")
            
            disp_mat_tbl = disp_mat[["Logo", "team_name", "elo", "1°", "2°", "3°", "4°", "5°", "6°", "7°", "8°"]].rename(columns={
                "Logo": " ", "team_name": "Equipo", "elo": "Rating ELO"
            })
            disp_mat_tbl["Rating ELO"] = disp_mat_tbl["Rating ELO"].apply(lambda x: f"{x:.1f}")
            st.dataframe(
                disp_mat_tbl,
                column_config={" ": st.column_config.ImageColumn(" ", width="small")},
                use_container_width=True,
                hide_index=True
            )

            # 2. Tabla de Probabilidades de Postemporada
            st.markdown("#### 🏆 Probabilidades de Avance por Ronda de Postemporada")
            disp_proj = df_proj.copy()
            disp_proj["Logo"] = disp_proj["team_name"].apply(lambda x: get_team_logo(x, size=72))
            disp_proj["elo_fmt"] = disp_proj["elo"].apply(lambda x: f"{x:.1f}")
            disp_proj["top4_fmt"] = disp_proj["top4_prob"].apply(lambda x: f"{x:.1%}")
            disp_proj["wc_fmt"] = disp_proj["wc_prob"].apply(lambda x: f"{x:.1%}")
            disp_proj["rr_fmt"] = disp_proj["rr_prob"].apply(lambda x: f"{x:.1%}")
            disp_proj["final_fmt"] = disp_proj["final_prob"].apply(lambda x: f"{x:.1%}")
            disp_proj["champ_fmt"] = disp_proj["champ_prob"].apply(lambda x: f"{x:.1%}")

            disp_proj_tbl = disp_proj[["Logo", "team_name", "elo_fmt", "top4_fmt", "wc_fmt", "rr_fmt", "final_fmt", "champ_fmt"]].rename(columns={
                "Logo": " ",
                "team_name": "Equipo",
                "elo_fmt": "Rating ELO",
                "top4_fmt": "Top 4 Directo (RR)",
                "wc_fmt": "Wild Card (5°-6°)",
                "rr_fmt": "Pase Total Round Robin",
                "final_fmt": "Gran Finalista",
                "champ_fmt": "🏆 Campeón LVBP"
            })
            st.dataframe(
                disp_proj_tbl,
                column_config={" ": st.column_config.ImageColumn(" ", width="small")},
                use_container_width=True,
                hide_index=True
            )

            # Gráfico de Campeonato
            fig_champ = px.bar(
                df_proj,
                x="team_name",
                y="champ_prob",
                title=f"<b>Probabilidad de Coronarse Campeón de la LVBP ({selected_season_display})</b>",
                labels={"team_name": "Equipo", "champ_prob": "Probabilidad de Campeón"},
                color="champ_prob",
                color_continuous_scale="Viridis",
                text=df_proj["champ_prob"].apply(lambda x: f"{x:.1%}")
            )
            fig_champ.update_layout(
                template="plotly_dark",
                height=380,
                xaxis_title="",
                yaxis_title="Probabilidad",
                yaxis=dict(tickformat=".0%"),
                showlegend=False
            )
            st.plotly_chart(fig_champ, use_container_width=True)

        with elo_subtab2:
            st.markdown("#### 🔮 Predictor de Partidos & Probabilidades del Calendario Real (Basado en ELO)")
            st.markdown(
                "Calcula la probabilidad real de victoria para cualquier enfrentamiento consultando los ratings ELO oficiales "
                "almacenados en la base de datos, incorporando la ventaja reglamentaria de localía (+35 pts ELO)."
            )

            # Cargar ELOs reales actuales
            current_elos = {}
            elo_regular_df = load_elo_ratings_for_phase(selected_season, "regular")
            if not elo_regular_df.empty:
                for _, r in elo_regular_df.iterrows():
                    try:
                        current_elos[int(r["team_id"])] = float(r["elo"])
                    except:
                        pass
            for tid in LVBP_TEAMS.keys():
                if tid not in current_elos:
                    current_elos[tid] = float(BASE_ELO)

            # 1. Pronósticos sobre el Calendario Real de la Temporada
            st.markdown("##### 📅 Pronóstico de Partidos del Calendario Oficial")
            
            df_cal_pred = get_calendar_games_with_elo_projections(selected_season)

            if not df_cal_pred.empty:
                # Filtro rápido
                filtro_cal = st.radio(
                    "Filtrar partidos del calendario:",
                    ["🦁 Solo Juegos de Leones del Caracas", "⚾ Todos los Juegos de la Liga"],
                    horizontal=True,
                    key="cal_pred_filter"
                )
                
                if "Leones" in filtro_cal:
                    df_cal_disp = df_cal_pred[(df_cal_pred['home_id'] == 695) | (df_cal_pred['away_id'] == 695)]
                else:
                    df_cal_disp = df_cal_pred
                    
                st.dataframe(
                    df_cal_disp[['game_date', 'Local_Logo', 'Local', 'Visitante_Logo', 'Visitante', 'ELO Local', 'ELO Visitante', 'Prob. Local', 'Prob. Visitante', 'Favorito ELO', 'Marcador / Estado']].rename(columns={
                        'game_date': 'Fecha',
                        'Local_Logo': ' ',
                        'Visitante_Logo': '  '
                    }),
                    column_config={
                        ' ': st.column_config.ImageColumn(" ", width="small"),
                        '  ': st.column_config.ImageColumn(" ", width="small")
                    },
                    use_container_width=True,
                    hide_index=True,
                    height=300
                )
            else:
                st.info("No se encontraron partidos registrados en el calendario para esta temporada.")

            st.markdown("---")

            # 2. Simulador de Enfrentamiento Directo Personalizado (100% ELO Real)
            st.markdown("##### 🆚 Simulador de Enfrentamiento Directo (Datos 100% Reales)")
            st.caption("Selecciona cualquier combinación de local y visitante para evaluar las probabilidades exactas con los ratings ELO reales.")

            col_h, col_vs, col_a = st.columns([5, 1, 5])
            
            team_ids = list(LVBP_TEAMS.keys())
            team_names_list = [LVBP_TEAMS[t] for t in team_ids]

            with col_h:
                st.markdown("##### 🏠 Equipo Local (Home)")
                home_team_name = st.selectbox(
                    "Seleccionar Local:",
                    options=team_names_list,
                    index=team_names_list.index("Leones del Caracas") if "Leones del Caracas" in team_names_list else 0,
                    key="pred_home_team"
                )
                home_tid = next(t for t, name in LVBP_TEAMS.items() if name == home_team_name)
                home_elo = current_elos.get(home_tid, BASE_ELO)
                
                ch_logo, ch_info = st.columns([1, 4])
                with ch_logo:
                    st.image(get_team_logo(home_tid, size=144), width=65)
                with ch_info:
                    st.info(f"⚡ **Rating ELO Real:** `{home_elo:.2f}`\n*(+35.0 pts localía = `{home_elo + HOME_ADVANTAGE:.2f}`)*")

            with col_vs:
                st.markdown("<div style='text-align: center; padding-top: 50px; font-size: 1.8rem; font-weight: bold;'>VS</div>", unsafe_allow_html=True)

            with col_a:
                st.markdown("##### ✈️ Equipo Visitante (Away)")
                away_options = [n for n in team_names_list if n != home_team_name]
                away_team_name = st.selectbox(
                    "Seleccionar Visitante:",
                    options=away_options,
                    index=away_options.index("Navegantes del Magallanes") if "Navegantes del Magallanes" in away_options else 0,
                    key="pred_away_team"
                )
                away_tid = next(t for t, name in LVBP_TEAMS.items() if name == away_team_name)
                away_elo = current_elos.get(away_tid, BASE_ELO)
                
                ca_logo, ca_info = st.columns([1, 4])
                with ca_logo:
                    st.image(get_team_logo(away_tid, size=144), width=65)
                with ca_info:
                    st.info(f"⚡ **Rating ELO Real:** `{away_elo:.2f}`")

            # Cálculo de probabilidades reales
            p_home, p_away = calculate_matchup_win_prob(home_elo, away_elo, HOME_ADVANTAGE)
            diff_eff = (home_elo + HOME_ADVANTAGE) - away_elo

            st.markdown(f"###### 📊 Pronóstico Sabermétrico: **{home_team_name} (Local) vs. {away_team_name} (Visitante)**")

            cp1, cp2, cp3 = st.columns(3)
            with cp1:
                st.metric(f"🏠 Victoria {home_team_name}", f"{p_home:.1%}", f"{home_elo:.1f} ELO (+35 Local)")
            with cp2:
                st.metric(f"✈️ Victoria {away_team_name}", f"{p_away:.1%}", f"{away_elo:.1f} ELO")
            with cp3:
                fav = home_team_name if p_home >= 0.5 else away_team_name
                fav_prob = max(p_home, p_away)
                st.metric("🏆 Favorito del Enfrentamiento", f"{fav}", f"{fav_prob:.1%} prob.")

            # Barra visual comparativa
            fig_match = go.Figure()
            fig_match.add_trace(go.Bar(
                y=["Enfrentamiento"],
                x=[p_home],
                name=f"🏠 {home_team_name} ({p_home:.1%})",
                orientation='h',
                marker=dict(color="#FDB827" if "Leones" in home_team_name else "#196F3D"),
                text=f"<b>{home_team_name} (Local): {p_home:.1%}</b>",
                textposition='inside',
                insidetextanchor='middle',
                textfont=dict(size=14, color="white")
            ))
            fig_match.add_trace(go.Bar(
                y=["Enfrentamiento"],
                x=[p_away],
                name=f"✈️ {away_team_name} ({p_away:.1%})",
                orientation='h',
                marker=dict(color="#003B57" if "Navegantes" in away_team_name else "#CE1141"),
                text=f"<b>{away_team_name} (Visitante): {p_away:.1%}</b>",
                textposition='inside',
                insidetextanchor='middle',
                textfont=dict(size=14, color="white")
            ))
            fig_match.update_layout(
                barmode='stack',
                template='plotly_dark',
                height=180,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis=dict(tickformat='.0%', range=[0, 1], showgrid=False),
                yaxis=dict(visible=False),
                legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_match, use_container_width=True)

            st.caption(
                f"ℹ️ El modelo aplica la ventaja reglamentaria de localía (+35 pts ELO). "
                f"Diferencial efectivo: **{diff_eff:+.1f} puntos** a favor de {'Local' if diff_eff > 0 else 'Visitante'}."
            )

        with elo_subtab3:
            st.markdown("#### ⚡ Clasificación Oficial y Ratings ELO por Fase")
            st.markdown(
                "El sistema ELO evalúa la fuerza relativa de cada equipo de forma dinámica tras cada partido, "
                "ponderando según el nivel del rival y la ventaja de localía (+35 pts). Base inicial: 1500."
            )
            
            elo_phase = st.selectbox(
                "🏆 Seleccionar Fase del Torneo",
                options=list(ELO_PHASE_OPTIONS.keys()),
                format_func=lambda x: ELO_PHASE_OPTIONS.get(x, x),
                key="elo_phase_selector_main"
            )
            elo_df = load_elo_ratings_for_phase(selected_season, elo_phase)
            
            if elo_df.empty:
                st.info(f"No hay registros de ELO calculados para la fase '{ELO_PHASE_OPTIONS.get(elo_phase, elo_phase)}' en {selected_season_display}.")
            else:
                leones_elo = elo_df[elo_df['team_name'].str.contains('Leones', case=False, na=False)]
                leader_elo = elo_df.iloc[0]
                
                e1, e2, e3, e4 = st.columns(4)
                with e1:
                    st.metric("🥇 Líder ELO Fase", f"{leader_elo['team_name']}")
                with e2:
                    st.metric("⚡ Rating del Líder", f"{float(leader_elo['elo']):.2f}")
                with e3:
                    if not leones_elo.empty:
                        l_elo_row = leones_elo.iloc[0]
                        st.metric("🦁 Rating Leones", f"{float(l_elo_row['elo']):.2f}", f"#{int(l_elo_row['rank'])} / {len(elo_df)}")
                    else:
                        st.metric("🦁 Leones del Caracas", "No participó", "Fase posterior")
                with e4:
                    st.metric("Juegos Evaluados", f"{int(leader_elo['games_played'])} JJ")
                st.markdown("---")
                    
                col_elo_chart, col_elo_tbl = st.columns([5, 7])
                
                with col_elo_chart:
                    st.markdown("##### 📊 Comparativa de ELO por Equipo")
                    elo_chart_df = elo_df.sort_values('elo', ascending=True).copy()
                    fig_elo = px.bar(
                        elo_chart_df,
                        x='elo',
                        y='team_name',
                        orientation='h',
                        color='elo',
                        color_continuous_scale='RdYlGn',
                        text_auto='.1f'
                    )
                    fig_elo.add_vline(x=1500, line_dash="dash", line_color="#ffffff", annotation_text="Base 1500", annotation_position="top")
                    fig_elo.update_layout(
                        template='plotly_dark',
                        height=360,
                        margin=dict(l=10, r=10, t=10, b=10),
                        coloraxis_showscale=False,
                        xaxis_title="Rating ELO",
                        yaxis_title=""
                    )
                    st.plotly_chart(fig_elo, use_container_width=True)
                    
                with col_elo_tbl:
                    st.markdown("##### 📋 Tabla Oficial de Ratings ELO")
                    display_df = elo_df[["rank", "team_name", "elo", "games_played", "updated_at"]].copy()
                    display_df["Logo"] = display_df["team_name"].apply(lambda x: get_team_logo(x, size=72))
                    display_df["delta"] = (display_df["elo"].astype(float) - 1500.0).round(2)
                    display_df["delta_str"] = display_df["delta"].apply(lambda x: f"{x:+.2f}")
                    display_df["elo_str"] = display_df["elo"].apply(lambda x: f"{float(x):.2f}")
                    display_df["updated_str"] = pd.to_datetime(display_df["updated_at"], errors="coerce").dt.strftime('%d/%m/%Y %H:%M')
                    
                    table_out = display_df[["Logo", "rank", "team_name", "elo_str", "delta_str", "games_played", "updated_str"]].rename(columns={
                        "Logo": " ", "rank": "#", "team_name": "Equipo", "elo_str": "Rating ELO", "delta_str": "Dif vs 1500",
                        "games_played": "JJ", "updated_str": "Última Actualización"
                    })
                    
                    st.dataframe(
                        table_out,
                        column_config={" ": st.column_config.ImageColumn(" ", width="small")},
                        use_container_width=True,
                        hide_index=True
                    )
    
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
                            'Logo': get_team_logo(team_id, size=72),
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
                    last_game = vs_team.sort_values('game_date', ascending=False).iloc[0]
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
                        'Logo': get_team_logo(team_id, size=72),
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
                    column_config={'Logo': st.column_config.ImageColumn(" ", width="small")},
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
                            'Logo': get_team_logo(rival_id, size=72),
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
                    
                    styled_df = upcoming_df.style.map(color_status, subset=['Estado'])
                    styled_df = styled_df.map(color_estadio, subset=['Estadio'])
                    
                    st.dataframe(
                        styled_df,
                        column_config={'Logo': st.column_config.ImageColumn(" ", width="small")},
                        use_container_width=True,
                        hide_index=True
                    )
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
                        df_games.style.map(color_result, subset=['Resultado']),
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








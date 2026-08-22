# pages/7_🛡️_Bullpen_y_Lineups.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from utils.supabase_client import get_available_seasons
from utils.bullpen_lineups import (
    fetch_season_bullpen_and_lineups,
    compute_bullpen_inherited_stats,
    LEONES_TEAM_ID
)

st.set_page_config(
    page_title="Bullpen y Tracker de Lineups - Leones del Caracas",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ Analítica de Bullpen y Tracker de Alineaciones")
st.markdown("Control de efectividad en herencia de corredores (IR/IRS) y análisis de combinaciones de lineups y su récord W-L.")

# Sidebar
st.sidebar.header("⚙️ Configuración")

available_seasons = get_available_seasons()
season_options = [f"{s}-{s+1}" for s in available_seasons]
default_idx = 0
for idx, s in enumerate(available_seasons):
    if s == 2025:
        default_idx = idx
        break

selected_season_str = st.sidebar.selectbox("⚾ Temporada", season_options, index=default_idx)
selected_season = int(selected_season_str.split("-")[0])

with st.spinner("Cargando datos de bullpen y lineups de la temporada..."):
    df_bullpen, lineups_data = fetch_season_bullpen_and_lineups(selected_season, team_id=LEONES_TEAM_ID)

tab_bp, tab_lu = st.tabs(["🛡️ Efectividad de Relevistas (IR / IRS)", "📋 Tracker de Alineaciones (Lineups)"])

# ================= TAB 1: BULLPEN =================
with tab_bp:
    st.subheader("🛡️ Corredores Heredados del Bullpen (Inherited Runners)")
    st.markdown("Evalúa la capacidad de los lanzadores relevistas para 'apagar el fuego' al entrar con hombres en las almohadillas.")
    
    if not df_bullpen.empty:
        df_irs_summary = compute_bullpen_inherited_stats(df_bullpen)
        
        # KPIs
        tot_ir = int(df_bullpen["inherited_runners"].sum())
        tot_irs = int(df_bullpen["inherited_scored"].sum())
        global_irs_pct = round(tot_irs / tot_ir * 100, 1) if tot_ir > 0 else 0.0
        
        # Mejor relevista con al menos 5 IR
        rel_qualified = df_irs_summary[df_irs_summary["Corredores Heredados (IR)"] >= 5]
        best_reliever = rel_qualified.iloc[0]["Lanzador Relevista"] if not rel_qualified.empty else "N/A"
        best_rel_pct = rel_qualified.iloc[0]["% Anotados (IRS%)"] if not rel_qualified.empty else 0.0
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Total Corredores Heredados (IR)", f"{tot_ir}")
        with c2:
            st.metric("Heredados que Anotaron (IRS)", f"{tot_irs}")
        with c3:
            st.metric("Tasa IRS% Colectiva", f"{global_irs_pct}%", help="Menor porcentaje representa mayor efectividad conteniendo carreras.")
        with c4:
            st.metric("Líder 'Apaga-Fuegos' (Min 5 IR)", f"{best_reliever}", f"{best_rel_pct}% IRS")
            
        st.markdown("---")
        
        # Gráficos y Tablas
        col_g, col_t = st.columns([6, 6])
        
        with col_g:
            st.markdown("#### 📊 Comparativa: Heredados (IR) vs. Anotados (IRS)")
            fig_bar = px.bar(
                df_irs_summary.head(10),
                x="Lanzador Relevista",
                y=["Corredores Heredados (IR)", "Heredados Anotados (IRS)"],
                barmode="group",
                color_discrete_sequence=["#3498db", "#e74c3c"]
            )
            fig_bar.update_layout(
                template="plotly_dark",
                height=380,
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with col_t:
            st.markdown("#### 📋 Tabla de Rendimiento por Relevista")
            st.dataframe(df_irs_summary, use_container_width=True, hide_index=True)
            
            csv_bp = df_irs_summary.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Descargar Tabla Bullpen en CSV", data=csv_bp, file_name=f"bullpen_irs_{selected_season}.csv", mime="text/csv")
            
        with st.expander("🔍 Ver Registro Detallado de Entradas con Corredores en Base", expanded=False):
            disp_bp = df_bullpen.rename(columns={
                "game_date": "Fecha", "opposing_team": "Rival", "inning": "Inning Entrada",
                "pitcher_name": "Lanzador", "inherited_runners": "Corredores Heredados", "inherited_scored": "Anotaron"
            })
            st.dataframe(disp_bp[["Fecha", "Rival", "Inning Entrada", "Lanzador", "Corredores Heredados", "Anotaron"]], use_container_width=True, hide_index=True)
    else:
        st.info("No se encontraron registros de relevos con corredores heredados.")

# ================= TAB 2: LINEUPS =================
with tab_lu:
    st.subheader("📋 Tracker de Alineaciones Titulares y Récord W-L")
    st.markdown("Rastrea las alineaciones empleadas durante la temporada y su récord de victorias y derrotas.")
    
    if lineups_data:
        # Agrupar por alineación
        lineup_records = []
        for item in lineups_data:
            lineup_records.append({
                "game_date": item["game_date"],
                "opposing_team": item["opposing_team"],
                "won": 1 if item["leones_won"] else 0,
                "lost": 0 if item["leones_won"] else 1,
                "lineup_summary": item["lineup_summary"]
            })
            
        df_lu = pd.DataFrame(lineup_records)
        
        # Resumen por alineación única
        lu_agg = df_lu.groupby("lineup_summary").agg(
            Juegos=("won", "count"),
            Victorias=("won", "sum"),
            Derrotas=("lost", "sum")
        ).reset_index()
        
        lu_agg["Pct_Victorias"] = (lu_agg["Victorias"] / lu_agg["Juegos"]).apply(lambda x: f"{x:.3f}".replace("0.", "."))
        lu_agg = lu_agg.sort_values(by=["Juegos", "Victorias"], ascending=[False, False])
        
        col_k1, col_k2, col_k3 = st.columns(3)
        with col_k1:
            st.metric("Total Juegos Analizados", f"{len(df_lu)}")
        with col_k2:
            st.metric("Alineaciones Únicas Usadas", f"{len(lu_agg)}")
        with col_k3:
            most_used_games = lu_agg.iloc[0]["Juegos"] if not lu_agg.empty else 0
            st.metric("Alineación Más Utilizada", f"{most_used_games} juegos", f"{lu_agg.iloc[0]['Victorias']}-{lu_agg.iloc[0]['Derrotas']} W-L" if not lu_agg.empty else None)
            
        st.markdown("---")
        st.markdown("#### 🌟 Alineaciones Más Utilizadas")
        st.dataframe(lu_agg, use_container_width=True, hide_index=True)
        
        # Desglose por posición en el orden al bate (1ro al 9no)
        st.markdown("#### 🔢 Jugadores Más Frecuentes por Turno al Bate (1ro al 9no)")
        order_rows = []
        for item in lineups_data:
            for st_player in item["starters"]:
                order_rows.append({
                    "Turno": f"Turno {st_player['order']}",
                    "Jugador": st_player["player_name"],
                    "Posicion": st_player["position"]
                })
                
        if order_rows:
            df_order = pd.DataFrame(order_rows)
            order_summary = df_order.groupby(["Turno", "Jugador"]).size().reset_index(name="Juegos Titular")
            order_summary = order_summary.sort_values(by=["Turno", "Juegos Titular"], ascending=[True, False])
            
            st.dataframe(order_summary, use_container_width=True, hide_index=True)
    else:
        st.info("No se encontraron datos de alineaciones para la temporada.")

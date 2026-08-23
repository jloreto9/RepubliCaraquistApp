# pages/6_⚡_Situacional_y_BvP.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from utils.supabase_client import get_available_seasons
from utils.teams import get_team_logo, get_team_name, get_team_abbr, LVBP_TEAMS, get_brand_logo
from utils.situational import (
    fetch_season_situational_data,
    compute_all_situational_splits,
    compute_bvp_summary,
    summarize_slash_line,
    LEONES_TEAM_ID
)

st.set_page_config(
    page_title="Desempeño Situacional y BvP - Leones del Caracas",
    page_icon="⚡",
    layout="wide"
)

# Header
col_h_logo, col_h_txt = st.columns([1, 8])
with col_h_logo:
    st.image(get_brand_logo(), width=75)
with col_h_txt:
    st.title("⚡ Desempeño Situacional y Enfrentamientos BvP")
    st.markdown("Analiza la efectividad en situaciones de alta presión (RISP, 2 Outs, Bases Llenas) y el historial cara a cara bateador vs. lanzador.")

# Sidebar
with st.sidebar:
    st.image(get_brand_logo(), width=200)
    st.markdown("---")
    st.header("⚙️ Configuración")

available_seasons = get_available_seasons()
season_options = [f"{s}-{s+1}" for s in available_seasons]
default_idx = 0
for idx, s in enumerate(available_seasons):
    if s == 2025:
        default_idx = idx
        break

selected_season_str = st.sidebar.selectbox("⚾ Temporada", season_options, index=default_idx)
selected_season = int(selected_season_str.split("-")[0])

with st.spinner("Cargando datos situacionales y matchups de la temporada..."):
    df_pa = fetch_season_situational_data(selected_season, team_id=LEONES_TEAM_ID)

if df_pa.empty:
    st.warning(f"⚠️ No se encontraron datos para la temporada {selected_season_str}.")
    st.stop()

tab_sit, tab_bvp = st.tabs(["⚡ Rendimiento Situacional (RISP & Clutch)", "⚔️ Cara a Cara BvP (Bateador vs Lanzador)"])

# ================= TAB 1: SITUACIONAL =================
with tab_sit:
    st.subheader("⚡ Desglose de Rendimiento Situacional")
    
    # Filtro de ámbito: Ofensiva de Leones
    leones_pa = df_pa[df_pa["is_batter_leones"] == True].copy()
    batter_counts = leones_pa["batter_name"].value_counts()
    batter_opts = [f"{name} ({c} apariciones)" for name, c in batter_counts.items()]
    batter_map = {f"{name} ({c} apariciones)": name for name, c in batter_counts.items()}
    
    sel_b_display = st.selectbox("👤 Seleccionar Bateador de Leones", ["🌟 Toda la Ofensiva de Leones"] + batter_opts)
    
    if sel_b_display == "🌟 Toda la Ofensiva de Leones":
        df_target = leones_pa
        target_name = "Leones del Caracas (Ofensiva Completa)"
    else:
        chosen_b = batter_map[sel_b_display]
        df_target = leones_pa[leones_pa["batter_name"] == chosen_b]
        target_name = chosen_b
        
    # Calcular splits
    splits_df = compute_all_situational_splits(df_target)
    
    # KPI Cards Clave
    risp_df = df_target[df_target["is_risp"] == True]
    empty_df = df_target[df_target["is_bases_empty"] == True]
    outs2_risp = df_target[df_target["is_2_outs_risp"] == True]
    
    m_all = summarize_slash_line(df_target)
    m_risp = summarize_slash_line(risp_df)
    m_empty = summarize_slash_line(empty_df)
    m_clutch = summarize_slash_line(outs2_risp)
    
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    with k1:
        st.metric("Total PA", f"{m_all['PA']}")
    with k2:
        st.metric("AVG General", f"{m_all['AVG']}")
    with k3:
        st.metric("AVG en RISP", f"{m_risp['AVG']}", delta=f"{m_risp['AVG_num'] - m_all['AVG_num']:+.3f}" if m_all['AB']>0 else None)
    with k4:
        st.metric("OPS en RISP", f"{m_risp['OPS']}", delta=f"{m_risp['OPS_num'] - m_all['OPS_num']:+.3f}" if m_all['AB']>0 else None)
    with k5:
        st.metric("2-Outs RISP (Clutch)", f"{m_clutch['AVG']}", help="Bateo con 2 outs y hombres en posición anotadora.")
    with k6:
        st.metric("Total RBI", f"{m_all['RBI']}")
        
    st.markdown("---")
    
    # Gráfico comparativo de OPS y AVG
    c_chart, c_table = st.columns([5, 7])
    
    with c_chart:
        st.markdown("#### 📊 Comparativa de OPS por Situación")
        if not splits_df.empty:
            splits_chart_df = splits_df.copy()
            splits_chart_df["OPS_val"] = splits_chart_df["OPS"].astype(float)
            fig_ops = px.bar(
                splits_chart_df,
                x="OPS_val",
                y="Situación",
                orientation="h",
                color="OPS_val",
                color_continuous_scale="Viridis",
                text_auto=".3f"
            )
            fig_ops.update_layout(
                template="plotly_dark",
                yaxis=dict(autorange="reversed"),
                height=380,
                margin=dict(l=10, r=10, t=10, b=10),
                coloraxis_showscale=False,
                xaxis_title="OPS"
            )
            st.plotly_chart(fig_ops, use_container_width=True)
            
    with c_table:
        st.markdown("#### 📋 Tabla Completa de Splits Situacionales")
        st.dataframe(splits_df, use_container_width=True, hide_index=True)
        
        csv_sit = splits_df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Descargar Splits en CSV", data=csv_sit, file_name=f"splits_{selected_season}_{target_name.replace(' ', '_')}.csv", mime="text/csv")

# ================= TAB 2: BvP =================
with tab_bvp:
    st.subheader("⚔️ Enfrentamientos Cara a Cara (BvP)")
    st.markdown("Revisa el historial acumulado entre cualquier bateador de Leones y lanzadores rivales de la liga.")
    
    bvp_leones_batters = df_pa[df_pa["is_batter_leones"] == True]
    batters_u = bvp_leones_batters.drop_duplicates(subset=["batter_id"]).sort_values("batter_name")
    
    b_options = {row["batter_name"]: row["batter_id"] for _, row in batters_u.iterrows()}
    
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        sel_bvp_batter_name = st.selectbox("👤 Bateador de Leones", list(b_options.keys()))
        sel_bvp_batter_id = b_options[sel_bvp_batter_name]
        
    bvp_df = compute_bvp_summary(df_pa, batter_id=sel_bvp_batter_id)
    
    with col_sel2:
        equipos_rivales = ["Todos los Rivales"] + sorted(list(bvp_df["Equipo Rival"].unique())) if not bvp_df.empty else ["Todos"]
        col_sel_r, col_logo_r = st.columns([4, 1])
        with col_sel_r:
            sel_rival_team = st.selectbox("🏟️ Filtrar por Equipo Rival", equipos_rivales)
        with col_logo_r:
            if sel_rival_team != "Todos los Rivales":
                st.image(get_team_logo(sel_rival_team, size=144), width=50)
        
    if not bvp_df.empty:
        if sel_rival_team != "Todos los Rivales":
            bvp_filtered = bvp_df[bvp_df["Equipo Rival"] == sel_rival_team].copy()
        else:
            bvp_filtered = bvp_df.copy()
            
        bvp_filtered["Logo"] = bvp_filtered["Equipo Rival"].apply(lambda r: get_team_logo(r, size=72))
        
        # Reordenar columnas para colocar el Logo antes de Equipo Rival
        cols = ["Logo"] + [c for c in bvp_filtered.columns if c != "Logo"]
        bvp_display = bvp_filtered[cols]
            
        st.markdown(f"#### 📊 Historial de {sel_bvp_batter_name} vs. Lanzadores Rivales ({len(bvp_filtered)} lanzadores enfrentados)")
        st.dataframe(
            bvp_display,
            column_config={
                "Logo": st.column_config.ImageColumn(" ", width="small")
            },
            use_container_width=True,
            hide_index=True
        )
        
        csv_bvp = bvp_filtered.drop(columns=["Logo"], errors="ignore").to_csv(index=False).encode("utf-8")
        st.download_button("📥 Descargar Matriz BvP en CSV", data=csv_bvp, file_name=f"bvp_{selected_season}_{sel_bvp_batter_name.replace(' ', '_')}.csv", mime="text/csv")
    else:
        st.info("No se encontraron enfrentamientos para el bateador seleccionado.")

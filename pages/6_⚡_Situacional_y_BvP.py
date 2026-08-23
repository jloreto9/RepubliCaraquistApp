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

try:
    from utils.styles import inject_custom_css
    inject_custom_css()
except:
    pass

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
    st.markdown("Examina cómo varía la producción ofensiva de acuerdo al contexto del juego: corredores en base, número de outs y entradas.")
    
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
    
    # KPI Cards Clave con Tooltips
    risp_df = df_target[df_target["is_risp"] == True]
    empty_df = df_target[df_target["is_bases_empty"] == True]
    outs2_risp = df_target[df_target["is_2_outs_risp"] == True]
    
    m_all = summarize_slash_line(df_target)
    m_risp = summarize_slash_line(risp_df)
    m_empty = summarize_slash_line(empty_df)
    m_clutch = summarize_slash_line(outs2_risp)
    
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    with k1:
        st.metric("Total PA", f"{m_all['PA']}", help="Apariciones al plato totales (Plate Appearances) registradas.")
    with k2:
        st.metric("AVG General", f"{m_all['AVG']}", help="Promedio de bateo general (H / AB).")
    with k3:
        st.metric("AVG en RISP", f"{m_risp['AVG']}", delta=f"{m_risp['AVG_num'] - m_all['AVG_num']:+.3f}" if m_all['AB']>0 else None, help="Promedio de bateo con corredores en posición anotadora (2da o 3ra base).")
    with k4:
        st.metric("OPS en RISP", f"{m_risp['OPS']}", delta=f"{m_risp['OPS_num'] - m_all['OPS_num']:+.3f}" if m_all['AB']>0 else None, help="OPS (OBP + SLG) con corredores en posición anotadora. Mide la productividad integral en situaciones de remolque.")
    with k5:
        st.metric("2-Outs RISP (Clutch)", f"{m_clutch['AVG']}", delta=f"{m_clutch['AVG_num'] - m_all['AVG_num']:+.3f}" if m_all['AB']>0 else None, help="Bateo bajo máxima presión: con 2 outs y hombres en 2da o 3ra base.")
    with k6:
        st.metric("Total RBI", f"{m_all['RBI']}", help="Carreras impulsadas totales acumuladas.")
        
    st.markdown("---")
    
    # Glosario y Leyenda de Métricas Situacionales
    with st.expander("📖 Leyenda & Guía Sabermétrica de Métricas Situacionales", expanded=False):
        st.markdown(r"""
        | Métrica / Situación | Definición | Interpretación Sabermétrica |
        |---|---|---|
        | **PA (Plate Appearances)** | Total de viajes al plato | Incluye turnos oficiales (AB), boletos (BB), pelotazos (HBP), elevados de sacrificio (SF) y toques (SH). |
        | **AB (At Bats)** | Turnos oficiales al bate | $AB = PA - BB - HBP - SF - SH - \text{Interferencias}$. Base de cálculo para AVG y SLG. |
        | **AVG (Batting Average)** | Promedio de bateo: $H / AB$ | Frecuencia de conectar imparables por turno oficial consumido. |
        | **OBP (On-Base Pct)** | Porcentaje de embasado | $\frac{H + BB + HBP}{AB + BB + HBP + SF}$. Mide la capacidad de evitar outs y llegar a base. |
        | **SLG (Slugging Pct)** | Promedio de bases alcanzadas | $\frac{1B + 2(2B) + 3(3B) + 4(HR)}{AB}$. Mide el poder de extrabases del bateador. |
        | **OPS (On-Base + Slugging)** | Producción ofensiva total: $OBP + SLG$ | Excelente: $> .900$ | Muy Bueno: $.800 - .899$ | Promedio: $.700 - .799$ | Bajo: $< .650$. |
        | **RISP (Runners In Scoring Position)** | Hombres en posición anotadora | Al menos un corredor en 2da o 3ra base al momento de consumir el turno. |
        | **RISP con 2 Outs (Clutch)** | Oportunismo de alta presión | Situación crítica donde el bateador debe producir un imparable antes de que culmine la entrada. |
        | **Bases Limpias / Llenas** | Contexto de corredores | Compara la efectividad sin tráfico en las almohadillas frente al escenario con las 3 bases ocupadas. |
        """)
    
    # Gráfico comparativo de OPS y Tabla
    c_chart, c_table = st.columns([5, 7])
    
    with c_chart:
        st.markdown("#### 📊 Comparativa de OPS por Situación")
        st.caption("📈 Barras más largas y cálidas representan mayor producción ofensiva combinada (OBP + SLG).")
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
            fig_ops.add_vline(x=0.700, line_dash="dash", line_color="gray", annotation_text="Promedio (.700)")
            fig_ops.update_layout(
                template="plotly_dark",
                yaxis=dict(autorange="reversed"),
                height=420,
                margin=dict(l=10, r=10, t=10, b=10),
                coloraxis_showscale=False,
                xaxis_title="OPS (On-Base Plus Slugging)"
            )
            st.plotly_chart(fig_ops, use_container_width=True)
            
    with c_table:
        st.markdown("#### 📋 Tabla Completa de Splits Situacionales")
        st.caption("Detalle de la línea ofensiva slash (AVG / OBP / SLG / OPS) y acumulados por situación.")
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
        st.caption("ℹ️ **Leyenda de columnas:** **PA:** Apariciones | **AB:** Turnos | **H:** Hits | **2B/3B/HR:** Extrabases | **BB:** Boletos | **SO:** Ponches | **AVG / OBP / SLG / OPS:** Línea de bateo.")
        
        st.dataframe(
            bvp_display,
            column_config={
                "Logo": st.column_config.ImageColumn(" ", width="small"),
                "PA": st.column_config.NumberColumn("PA", help="Apariciones al plato frente a este lanzador"),
                "AB": st.column_config.NumberColumn("AB", help="Turnos oficiales al bate"),
                "H": st.column_config.NumberColumn("H", help="Hits conectados"),
                "HR": st.column_config.NumberColumn("HR", help="Cuadrangulares"),
                "RBI": st.column_config.NumberColumn("RBI", help="Carreras remolcadas"),
                "BB": st.column_config.NumberColumn("BB", help="Boletos recibidos"),
                "SO": st.column_config.NumberColumn("SO", help="Ponches recibidos"),
                "AVG": st.column_config.TextColumn("AVG", help="Promedio de bateo (H/AB)"),
                "OBP": st.column_config.TextColumn("OBP", help="Porcentaje de embasado"),
                "SLG": st.column_config.TextColumn("SLG", help="Slugging (Bases totales/AB)"),
                "OPS": st.column_config.TextColumn("OPS", help="Producción ofensiva combinada (OBP + SLG)")
            },
            use_container_width=True,
            hide_index=True
        )
        
        csv_bvp = bvp_filtered.drop(columns=["Logo"], errors="ignore").to_csv(index=False).encode("utf-8")
        st.download_button("📥 Descargar Matriz BvP en CSV", data=csv_bvp, file_name=f"bvp_{selected_season}_{sel_bvp_batter_name.replace(' ', '_')}.csv", mime="text/csv")
        
        with st.expander("ℹ️ Nota Metodológica de Muestra BvP (Batter vs. Pitcher)"):
            st.markdown(r"""
            * **Muestras Pequeñas ($< 5\text{ PA}$):** En el béisbol de invierno (LVBP), muchos enfrentamientos BvP tienen menos de 5 turnos. Deben evaluarse como referencia preliminar y no como certeza estadística.
            * **Muestras Robustas ($\ge 10\text{ PA}$):** Revelan tendencias claras de dominio del lanzador o ventaja del bateador ante ciertos tipos de repertorio.
            """)
    else:
        st.info("No se encontraron enfrentamientos para el bateador seleccionado.")

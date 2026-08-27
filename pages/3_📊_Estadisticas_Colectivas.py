# pages/3_📊_Estadisticas_Colectivas.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import sys

# Agregar el directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from utils.supabase_client import (
        get_collective_team_stats,
        get_available_seasons,
        get_current_season
    )
    from utils.teams import (
        get_team_logo,
        get_team_name,
        get_team_abbr,
        get_team_color,
        LVBP_TEAMS,
        get_brand_logo
    )
except:
    from streamlit_app.utils.supabase_client import (
        get_collective_team_stats,
        get_available_seasons,
        get_current_season
    )
    from streamlit_app.utils.teams import (
        get_team_logo,
        get_team_name,
        get_team_abbr,
        get_team_color,
        LVBP_TEAMS,
        get_brand_logo
    )

st.set_page_config(
    page_title="Estadísticas Colectivas - RepubliCaraquistApp",
    page_icon="📊",
    layout="wide"
)

try:
    from utils.styles import inject_custom_css
    inject_custom_css()
except:
    pass

# Sidebar
with st.sidebar:
    st.image(get_brand_logo(), width=200)
    st.markdown("---")
    st.header("⚙️ Configuración")

available_seasons = get_available_seasons()
current_season = get_current_season()
if not available_seasons:
    available_seasons = [current_season]

season_options = {f"{s}-{s+1}": s for s in available_seasons}
default_idx = 0
for idx, s in enumerate(available_seasons):
    if s == 2025:
        default_idx = idx
        break

selected_season_str = st.sidebar.selectbox("⚾ Temporada", list(season_options.keys()), index=default_idx)
selected_season = season_options[selected_season_str]

fase_options = {
    "Temporada Regular": "R",
    "Todos Contra Todos (Round Robin)": "L",
    "Serie Final": "F",
    "Serie Comodín (Wild Card)": "D"
}
selected_fase_name = st.sidebar.selectbox("🏆 Fase del Torneo", list(fase_options.keys()), index=0)
selected_phase = fase_options[selected_fase_name]

# Header
col_h_logo, col_h_txt = st.columns([1, 8])
with col_h_logo:
    st.image(get_brand_logo(), width=75)
with col_h_txt:
    st.title("📊 Estadísticas Colectivas — LVBP")
    st.markdown(f"Comparativa completa y métricas sabermétricas de los 8 equipos ({selected_season_str} — {selected_fase_name}).")

# Helper function to enrich with logos
def enrich_team_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    enriched = df.copy()
    enriched["Logo"] = enriched["team_id"].apply(lambda tid: get_team_logo(tid, size=72))
    return enriched

# Main Tabs
tab_bat, tab_pit, tab_fld = st.tabs([
    "🏏 Bateo Colectivo",
    "⚡ Pitcheo Colectivo",
    "🧤 Fildeo Colectivo"
])

# ==================== TAB 1: BATEO COLECTIVO ====================
with tab_bat:
    st.subheader(f"🏏 Estadísticas Ofensivas Colectivas ({selected_season_str})")
    st.caption("Rendimiento con el madero de todos los equipos de la liga.")

    with st.spinner("Cargando bateo colectivo..."):
        df_bat = get_collective_team_stats(selected_season, phase=selected_phase, group="hitting")

    if not df_bat.empty:
        df_bat_enriched = enrich_team_df(df_bat)

        # Resumen de líderes en tarjetas KPI
        k1, k2, k3, k4 = st.columns(4)
        
        # Líder AVG
        if "avg" in df_bat.columns:
            l_avg = df_bat.sort_values("avg", ascending=False).iloc[0]
            with k1:
                st.metric("👑 Líder AVG", f"{l_avg['avg']}", f"{l_avg['team_name']}")

        # Líder OPS
        if "ops" in df_bat.columns:
            l_ops = df_bat.sort_values("ops", ascending=False).iloc[0]
            with k2:
                st.metric("💥 Líder OPS", f"{l_ops['ops']}", f"{l_ops['team_name']}")

        # Líder HR
        if "homeRuns" in df_bat.columns:
            l_hr = df_bat.sort_values("homeRuns", ascending=False).iloc[0]
            with k3:
                st.metric("💣 Líder Jonrones", f"{l_hr['homeRuns']} HR", f"{l_hr['team_name']}")

        # Líder Carreras
        if "runs" in df_bat.columns:
            l_r = df_bat.sort_values("runs", ascending=False).iloc[0]
            with k4:
                st.metric("🏃 Líder Anotadas", f"{l_r['runs']} CA", f"{l_r['team_name']}")

        st.markdown("---")

        # Columnas a desplegar
        cols_bat_map = {
            "Logo": " ",
            "team_name": "Equipo",
            "gamesPlayed": "JJ",
            "plateAppearances": "PA",
            "atBats": "AB",
            "runs": "R",
            "hits": "H",
            "doubles": "2B",
            "triples": "3B",
            "homeRuns": "HR",
            "rbi": "RBI",
            "baseOnBalls": "BB",
            "strikeOuts": "SO",
            "stolenBases": "BR",
            "caughtStealing": "CR",
            "avg": "AVG",
            "obp": "OBP",
            "slg": "SLG",
            "ops": "OPS",
            "leftOnBase": "LOB",
            "babip": "BABIP"
        }

        cols_avail = [c for c in cols_bat_map.keys() if c in df_bat_enriched.columns]
        display_bat = df_bat_enriched[cols_avail].rename(columns=cols_bat_map).sort_values("OPS" if "OPS" in cols_bat_map.values() else "AVG", ascending=False)

        st.dataframe(
            display_bat,
            column_config={
                " ": st.column_config.ImageColumn(" ", width="small"),
                "Equipo": st.column_config.TextColumn("Equipo", width="medium"),
                "AVG": st.column_config.TextColumn("AVG"),
                "OBP": st.column_config.TextColumn("OBP"),
                "SLG": st.column_config.TextColumn("SLG"),
                "OPS": st.column_config.TextColumn("OPS")
            },
            use_container_width=True,
            hide_index=True
        )

        st.markdown("#### 📊 Comparador Gráfico de Métricas Ofensivas")
        c_sel_m, _ = st.columns([3, 5])
        with c_sel_m:
            metric_options = {
                "OPS (Producción Total)": "ops",
                "AVG (Promedio al Bate)": "avg",
                "OBP (Porcentaje de Embasado)": "obp",
                "SLG (Slugging)": "slg",
                "Jonrones (HR)": "homeRuns",
                "Carreras Anotadas (R)": "runs",
                "Hits Conectados (H)": "hits",
                "Boletos Recibidos (BB)": "baseOnBalls",
                "Bases Robadas (SB)": "stolenBases",
                "Dejados en Base (LOB)": "leftOnBase"
            }
            sel_bat_m = st.selectbox("Seleccionar Métrica Ofensiva", list(metric_options.keys()))
            m_col = metric_options[sel_bat_m]

        if m_col in df_bat.columns:
            plot_df = df_bat.copy()
            plot_df[m_col] = pd.to_numeric(plot_df[m_col], errors="coerce")
            plot_df = plot_df.sort_values(m_col, ascending=True)

            colors = ["#FDB827" if "Caracas" in str(t) or "Leones" in str(t) else "#38BDF8" for t in plot_df["team_name"]]

            fig_bat = px.bar(
                plot_df,
                x=m_col,
                y="team_name",
                orientation="h",
                title=f"Comparativa de {sel_bat_m} por Equipo",
                labels={m_col: sel_bat_m, "team_name": "Equipo"},
                text_auto=True
            )
            fig_bat.update_traces(marker_color=colors)
            fig_bat.update_layout(template="plotly_dark", height=380, yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig_bat, use_container_width=True)

        with st.expander("📖 Guía y Glosario: ¿Cómo entender el Bateo Colectivo?", expanded=False):
            st.markdown(r"""
            ### 🏏 Métricas Colectivas de Ofensiva

            | Métrica | Nombre | ¿Qué evalúa a nivel de equipo? |
            |---|---|---|
            | **PA / AB** | Apariciones / Turnos | Volumen global de oportunidades ofensivas de la franquicia. |
            | **R (Carreras)** | Carreras Totales | La métrica definitiva de producción ofensiva (quien anota más carreras gana los juegos). |
            | **H (Hits)** | Imparables | Capacidad colectiva para poner la bola en juego y conectar de hit. |
            | **HR (Jonrones)** | Poder de Cuadrangulares | Poder absoluto del lineup completo. |
            | **AVG** | Promedio de Bateo del Equipo | Frecuencia global de hits del equipo ($H / AB$). |
            | **OBP** | Porcentaje de Embasado Colectivo | Qué porcentaje de veces los bateadores del equipo alcanzan base viva (vía hit, boleto o pelotazo). |
            | **SLG** | Slugging Colectivo | Promedio de bases alcanzadas por turno en toda la alineación. |
            | **OPS** | On-Base Plus Slugging Colectivo | **La radiografía ofensiva global:** mide la capacidad de una franquicia para embasarse y batear con fuerza. |
            | **LOB** | Dejados en Base (Left on Base) | Corredores en circulación que no lograron cruzar el plato antes de que terminaran los innings. |
            | **BABIP** | Promedio de Bateo en Bolas Puestas en Juego | $\frac{H - HR}{AB - K - HR + SF}$. Mide la suerte y la contundencia de los batazos dentro del campo (promedio de liga suele rondar $.300$). |
            """)

    else:
        st.info("No hay datos de bateo colectivo disponibles para la selección actual.")

# ==================== TAB 2: PITCHEO COLECTIVO ====================
with tab_pit:
    st.subheader(f"⚡ Estadísticas de Pitcheo Colectivo ({selected_season_str})")
    st.caption("Efectividad, control y dominio del cuerpo monticular por franquicia.")

    with st.spinner("Cargando pitcheo colectivo..."):
        df_pit = get_collective_team_stats(selected_season, phase=selected_phase, group="pitching")

    if not df_pit.empty:
        df_pit_enriched = enrich_team_df(df_pit)

        # Tarjetas de líderes
        p1, p2, p3, p4 = st.columns(4)

        if "era" in df_pit.columns:
            l_era = df_pit.sort_values("era", ascending=True).iloc[0]
            with p1:
                st.metric("👑 Mejor ERA (Efectividad)", f"{l_era['era']}", f"{l_era['team_name']}")

        if "whip" in df_pit.columns:
            l_whip = df_pit.sort_values("whip", ascending=True).iloc[0]
            with p2:
                st.metric("🎯 Mejor WHIP", f"{l_whip['whip']}", f"{l_whip['team_name']}")

        if "strikeOuts" in df_pit.columns:
            l_so = df_pit.sort_values("strikeOuts", ascending=False).iloc[0]
            with p3:
                st.metric("⚡ Más Ponches (K)", f"{l_so['strikeOuts']} K", f"{l_so['team_name']}")

        if "saves" in df_pit.columns:
            l_sv = df_pit.sort_values("saves", ascending=False).iloc[0]
            with p4:
                st.metric("🛡️ Más Salvados (SV)", f"{l_sv['saves']} SV", f"{l_sv['team_name']}")

        st.markdown("---")

        cols_pit_map = {
            "Logo": " ",
            "team_name": "Equipo",
            "gamesPlayed": "JJ",
            "wins": "G",
            "losses": "P",
            "era": "ERA",
            "whip": "WHIP",
            "saves": "SV",
            "holds": "HLD",
            "blownSaves": "BS",
            "inningsPitched": "IP",
            "hits": "H",
            "runs": "R",
            "earnedRuns": "CL",
            "baseOnBalls": "BB",
            "strikeOuts": "SO",
            "homeRuns": "HR",
            "strikeoutsPer9Inn": "K/9",
            "walksPer9Inn": "BB/9",
            "strikeoutWalkRatio": "K/BB",
            "avg": "BAA"
        }

        cols_avail_p = [c for c in cols_pit_map.keys() if c in df_pit_enriched.columns]
        display_pit = df_pit_enriched[cols_avail_p].rename(columns=cols_pit_map).sort_values("ERA" if "ERA" in cols_pit_map.values() else "G", ascending=True)

        st.dataframe(
            display_pit,
            column_config={
                " ": st.column_config.ImageColumn(" ", width="small"),
                "Equipo": st.column_config.TextColumn("Equipo", width="medium"),
                "ERA": st.column_config.TextColumn("ERA"),
                "WHIP": st.column_config.TextColumn("WHIP")
            },
            use_container_width=True,
            hide_index=True
        )

        st.markdown("#### 📊 Comparador Gráfico de Métricas de Pitcheo")
        c_sel_mp, _ = st.columns([3, 5])
        with c_sel_mp:
            metric_options_p = {
                "ERA (Efectividad Colectiva)": "era",
                "WHIP (Embasados por Inning)": "whip",
                "Ponches Totales (SO)": "strikeOuts",
                "Ponches por 9 Entradas (K/9)": "strikeoutsPer9Inn",
                "Boletos Permitidos (BB)": "baseOnBalls",
                "Relación K/BB": "strikeoutWalkRatio",
                "Juegos Salvados (SV)": "saves",
                "Promedio de Bateo en Contra (BAA)": "avg"
            }
            sel_pit_m = st.selectbox("Seleccionar Métrica de Pitcheo", list(metric_options_p.keys()))
            mp_col = metric_options_p[sel_pit_m]

        if mp_col in df_pit.columns:
            plot_df_p = df_pit.copy()
            plot_df_p[mp_col] = pd.to_numeric(plot_df_p[mp_col], errors="coerce")
            ascending_sort = mp_col in ["era", "whip", "avg", "baseOnBalls"]
            plot_df_p = plot_df_p.sort_values(mp_col, ascending=not ascending_sort)

            colors_p = ["#FDB827" if "Caracas" in str(t) or "Leones" in str(t) else "#CE1141" for t in plot_df_p["team_name"]]

            fig_pit = px.bar(
                plot_df_p,
                x=mp_col,
                y="team_name",
                orientation="h",
                title=f"Comparativa de {sel_pit_m} por Equipo",
                labels={mp_col: sel_pit_m, "team_name": "Equipo"},
                text_auto=True
            )
            fig_pit.update_traces(marker_color=colors_p)
            fig_pit.update_layout(template="plotly_dark", height=380, yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig_pit, use_container_width=True)

        with st.expander("📖 Guía y Glosario: ¿Cómo entender el Pitcheo Colectivo?", expanded=False):
            st.markdown(r"""
            ### ⚡ Métricas Colectivas del Montículo

            | Métrica | Nombre | ¿Qué evalúa a nivel de equipo? |
            |---|---|---|
            | **ERA** | Efectividad Colectiva | Carreras limpias promedio permitidas por todo el cuerpo de lanzadores (abridores + bullpen) cada 9 innings. |
            | **WHIP** | Embasados Colectivos por Inning | Cantidad promedio de hits y boletos permitidos por entrada de labor. |
            | **SV / HLD** | Salvados y Holds Totales | Solvencia del cuerpo de relevistas para aguantar y cerrar victorias. |
            | **BS** | Oportunidades Desperdiciadas | Juegos en los que el bullpen perdió la ventaja en los innings finales. |
            | **SO (Ponches)** | Ponches Totales | Dominio absoluto del staff de lanzadores para retirar bateadores sin que pongan la bola en juego. |
            | **K/9 & BB/9** | Frecuencia de K y BB | Tasa de ponches y boletos otorgados cada 9 entradas lanzadas. |
            | **BAA** | Promedio de Bateo Rival | El porcentaje de bateo que le conectan colectivamente al equipo. |
            """)

    else:
        st.info("No hay datos de pitcheo colectivo disponibles para la selección actual.")

# ==================== TAB 3: FILDEO COLECTIVO ====================
with tab_fld:
    st.subheader(f"🧤 Estadísticas de Fildeo Colectivo ({selected_season_str})")
    st.caption("Solvencia defensiva, asistencias, errores y doble matanzas colectivas.")

    with st.spinner("Cargando fildeo colectivo..."):
        df_fld = get_collective_team_stats(selected_season, phase=selected_phase, group="fielding")

    if not df_fld.empty:
        df_fld_enriched = enrich_team_df(df_fld)

        # Tarjetas de líderes
        f1, f2, f3, f4 = st.columns(4)

        if "fielding" in df_fld.columns:
            l_fpct = df_fld.sort_values("fielding", ascending=False).iloc[0]
            with f1:
                st.metric("🎯 Mejor % Fildeo (FPCT)", f"{l_fpct['fielding']}", f"{l_fpct['team_name']}")

        if "errors" in df_fld.columns:
            l_err = df_fld.sort_values("errors", ascending=True).iloc[0]
            with f2:
                st.metric("🛡️ Menos Errores (E)", f"{l_err['errors']} E", f"{l_err['team_name']}")

        if "doublePlays" in df_fld.columns:
            l_dp = df_fld.sort_values("doublePlays", ascending=False).iloc[0]
            with f3:
                st.metric("⚡ Más Doble Matanzas (DP)", f"{l_dp['doublePlays']} DP", f"{l_dp['team_name']}")

        if "caughtStealingPercentage" in df_fld.columns:
            l_cs = df_fld.sort_values("caughtStealingPercentage", ascending=False).iloc[0]
            with f4:
                st.metric("🧤 Mejor % Captura (CS%)", f"{l_cs['caughtStealingPercentage']}", f"{l_cs['team_name']}")

        st.markdown("---")

        cols_fld_map = {
            "Logo": " ",
            "team_name": "Equipo",
            "gamesPlayed": "JJ",
            "innings": "Inn",
            "putOuts": "PO",
            "assists": "A",
            "errors": "E",
            "chances": "TC",
            "fielding": "FPCT",
            "doublePlays": "DP",
            "triplePlays": "TP",
            "passedBall": "PB",
            "caughtStealing": "CS",
            "stolenBases": "SB",
            "caughtStealingPercentage": "CS%",
            "rangeFactorPer9Inn": "RF/9"
        }

        cols_avail_f = [c for c in cols_fld_map.keys() if c in df_fld_enriched.columns]
        display_fld = df_fld_enriched[cols_avail_f].rename(columns=cols_fld_map).sort_values("FPCT" if "FPCT" in cols_fld_map.values() else "PO", ascending=False)

        st.dataframe(
            display_fld,
            column_config={
                " ": st.column_config.ImageColumn(" ", width="small"),
                "Equipo": st.column_config.TextColumn("Equipo", width="medium"),
                "FPCT": st.column_config.TextColumn("FPCT"),
                "CS%": st.column_config.TextColumn("CS%")
            },
            use_container_width=True,
            hide_index=True
        )

        st.markdown("#### 📊 Comparador Gráfico de Rendimiento Defensivo")
        c_sel_mf, _ = st.columns([3, 5])
        with c_sel_mf:
            metric_options_f = {
                "Porcentaje de Fildeo (FPCT)": "fielding",
                "Errores Cometidos (E)": "errors",
                "Doble Matanzas (DP)": "doublePlays",
                "Asistencias (A)": "assists",
                "Outs Realizados (PO)": "putOuts",
                "Total de Lances (TC)": "chances",
                "Porcentaje de Captura de Receptores (CS%)": "caughtStealingPercentage"
            }
            sel_fld_m = st.selectbox("Seleccionar Métrica de Fildeo", list(metric_options_f.keys()))
            mf_col = metric_options_f[sel_fld_m]

        if mf_col in df_fld.columns:
            plot_df_f = df_fld.copy()
            plot_df_f[mf_col] = pd.to_numeric(plot_df_f[mf_col], errors="coerce")
            ascending_sort_f = mf_col == "errors"
            plot_df_f = plot_df_f.sort_values(mf_col, ascending=not ascending_sort_f)

            colors_f = ["#FDB827" if "Caracas" in str(t) or "Leones" in str(t) else "#10B981" for t in plot_df_f["team_name"]]

            fig_fld = px.bar(
                plot_df_f,
                x=mf_col,
                y="team_name",
                orientation="h",
                title=f"Comparativa de {sel_fld_m} por Equipo",
                labels={mf_col: sel_fld_m, "team_name": "Equipo"},
                text_auto=True
            )
            fig_fld.update_traces(marker_color=colors_f)
            fig_fld.update_layout(template="plotly_dark", height=380, yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig_fld, use_container_width=True)

        with st.expander("📖 Guía y Glosario: ¿Cómo entender el Fildeo Colectivo?", expanded=False):
            st.markdown(r"""
            ### 🧤 Métricas Defensivas Colectivas

            | Métrica | Nombre | ¿Qué evalúa a nivel de equipo? |
            |---|---|---|
            | **FPCT** | Porcentaje de Fildeo | Proporción de jugadas defensivas ejecutadas sin error por todo el equipo. |
            | **E** | Errores Totales | Cantidad de pifias cometidas a lo largo de la temporada (menos es mejor). |
            | **DP** | Doble Plays Realizados | Capacidad para matar rallies ofensivos rivales con jugadas de dos outs simultáneos. |
            | **PO / A** | Outs y Asistencias | Volumen de jugadas completadas por el cuadro interior y los jardineros. |
            | **CS%** | Eficiencia de la Receptoría | Porcentaje de robos de base neutralizados por los receptores del equipo. |
            """)

    else:
        st.info("No hay datos de fildeo colectivo disponibles para la selección actual.")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p>📊 Estadísticas oficiales de los 8 equipos de la Liga Venezolana de Béisbol Profesional (LVBP)</p>
    <p style='font-size: 0.8rem;'>Powered by MLB Stats API & RepubliCaraquistApp</p>
</div>
""", unsafe_allow_html=True)

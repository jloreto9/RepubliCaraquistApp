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
    st.markdown("Analiza la estructura del orden al bate empleada por los Leones del Caracas a lo largo de la temporada.")
    
    if lineups_data:
        # Preparar data agregada
        lineup_records = []
        starters_flat = []
        
        for item in lineups_data:
            g_date = item["game_date"]
            opp = item["opposing_team"]
            won = item["leones_won"]
            score_leo = item.get("leones_score", 0)
            score_opp = item.get("opposing_score", 0)
            starters = item.get("starters", [])
            
            game_entry = {
                "game_pk": item["game_pk"],
                "game_date": g_date,
                "opposing_team": opp,
                "won": 1 if won else 0,
                "lost": 0 if won else 1,
                "score_str": f"{score_leo}-{score_opp}",
                "result_str": "VICTORIA" if won else "DERROTA",
                "starters": starters
            }
            lineup_records.append(game_entry)
            
            for s in starters:
                starters_flat.append({
                    "Jugador": s["player_name"],
                    "Turno_Num": s["order"],
                    "Turno": f"{s['order']}º Bate",
                    "Posicion": s["position"],
                    "game_date": g_date,
                    "opposing_team": opp,
                    "won": 1 if won else 0,
                    "lost": 0 if won else 1
                })
                
        df_starters = pd.DataFrame(starters_flat)
        df_games_lu = pd.DataFrame(lineup_records)
        
        # Métricas Globales
        tot_juegos = len(df_games_lu)
        tot_jugadores = df_starters["Jugador"].nunique()
        top_titular = df_starters["Jugador"].value_counts().index[0]
        top_titular_jj = df_starters["Jugador"].value_counts().iloc[0]
        
        # Jugador 4to bate más frecuente
        cleanups = df_starters[df_starters["Turno_Num"] == 4]["Jugador"].value_counts()
        top_cleanup = cleanups.index[0] if not cleanups.empty else "N/A"
        top_cleanup_jj = cleanups.iloc[0] if not cleanups.empty else 0
        
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.metric("Juegos Analizados", f"{tot_juegos} JJ")
        with k2:
            st.metric("Jugadores Titulares Usados", f"{tot_jugadores}")
        with k3:
            st.metric("Más Titularidades", f"{top_titular}", f"{top_titular_jj} JJ")
        with k4:
            st.metric("4to Bate (Cleanup)", f"{top_cleanup}", f"{top_cleanup_jj} veces titular")
            
        st.markdown("---")
        
        # Vistas de Alineación
        subtab_card, subtab_top_lu, subtab_matrix, subtab_player = st.tabs([
            "🎴 Tarjeta de Alineación por Juego (Lineup Card)",
            "🌟 Alineaciones Más Utilizadas",
            "📊 Matriz de Calor (Turnos 1 al 9)",
            "👤 Impacto por Jugador Titular"
        ])
        
        # ---- VISTA 1: TARJETA DE ALINEACIÓN POR JUEGO ----
        with subtab_card:
            st.markdown("#### 🏟️ Explorador de Tarjeta de Juego (Dugout Scorecard)")
            st.markdown("Selecciona un partido para visualizar el orden al bate completo del 1ro al 9no bate.")
            
            # Selector de partido
            game_options = {}
            for g in lineup_records:
                symbol = "✅ Victoria" if g["won"] == 1 else "❌ Derrota"
                label = f"📅 {g['game_date']} | vs {g['opposing_team']} ({symbol} {g['score_str']})"
                game_options[label] = g
                
            selected_game_label = st.selectbox("Seleccionar Partido", list(game_options.keys()), key="lineup_game_sel")
            selected_game = game_options[selected_game_label]
            
            # Renderizar tarjeta estilo Dugout
            st.markdown(f"""
            <div style='background-color: #1e293b; padding: 16px; border-radius: 10px; border-left: 6px solid {'#10b981' if selected_game['won'] == 1 else '#ef4444'}; margin-bottom: 20px;'>
                <h3 style='margin: 0; color: #ffffff;'>🦁 Alineación Titular — Leones del Caracas</h3>
                <p style='margin: 4px 0 0 0; color: #94a3b8;'>📅 Fecha: <b>{selected_game['game_date']}</b> | Rival: <b>{selected_game['opposing_team']}</b> | Marcador: <b>{selected_game['score_str']}</b> ({selected_game['result_str']})</p>
            </div>
            """, unsafe_allow_html=True)
            
            starters_sorted = sorted(selected_game["starters"], key=lambda x: x["order"])
            
            col_order_left, col_order_right = st.columns(2)
            
            pos_names = {
                "1B": "Primera Base", "2B": "Segunda Base", "3B": "Tercera Base",
                "SS": "Campocorto", "LF": "Jardín Izquierdo", "CF": "Jardín Central",
                "RF": "Jardín Derecho", "C": "Receptor", "DH": "Bateador Designado"
            }
            
            # 1ro al 5to
            with col_order_left:
                for s in starters_sorted[:5]:
                    pos_full = pos_names.get(s['position'], s['position'])
                    badge_color = "#3b82f6" if s['order'] <= 3 else ("#f59e0b" if s['order'] == 4 else "#8b5cf6")
                    st.markdown(f"""
                    <div style='background: #0f172a; padding: 12px 16px; border-radius: 8px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #334155;'>
                        <div>
                            <span style='background: {badge_color}; color: white; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 14px; margin-right: 12px;'>#{s['order']}</span>
                            <span style='font-size: 16px; font-weight: 600; color: #f8fafc;'>{s['player_name']}</span>
                        </div>
                        <div>
                            <span style='background: #334155; color: #e2e8f0; padding: 4px 8px; border-radius: 4px; font-size: 13px;'>{s['position']} • {pos_full}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
            # 6to al 9no
            with col_order_right:
                for s in starters_sorted[5:]:
                    pos_full = pos_names.get(s['position'], s['position'])
                    st.markdown(f"""
                    <div style='background: #0f172a; padding: 12px 16px; border-radius: 8px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #334155;'>
                        <div>
                            <span style='background: #64748b; color: white; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 14px; margin-right: 12px;'>#{s['order']}</span>
                            <span style='font-size: 16px; font-weight: 600; color: #f8fafc;'>{s['player_name']}</span>
                        </div>
                        <div>
                            <span style='background: #334155; color: #e2e8f0; padding: 4px 8px; border-radius: 4px; font-size: 13px;'>{s['position']} • {pos_full}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        # ---- VISTA 2: ALINEACIONES MÁS UTILIZADAS ----
        with subtab_top_lu:
            st.markdown("#### 🌟 Combinaciones de Alineación Más Frecuentes y su Rendimiento")
            st.markdown("Identifica los órdenes al bate de 9 jugadores más empleados y su récord colectivo de victorias y derrotas.")
            
            # Agrupar alineaciones exactas
            lineup_groups = {}
            for g in lineup_records:
                starters = g["starters"]
                key = tuple((s["order"], s["player_name"], s["position"]) for s in sorted(starters, key=lambda x: x["order"]))
                if key not in lineup_groups:
                    lineup_groups[key] = {
                        "games_count": 0,
                        "wins": 0,
                        "losses": 0,
                        "games": [],
                        "starters": sorted(starters, key=lambda x: x["order"])
                    }
                won = (g["won"] == 1)
                lineup_groups[key]["games_count"] += 1
                if won:
                    lineup_groups[key]["wins"] += 1
                else:
                    lineup_groups[key]["losses"] += 1
                lineup_groups[key]["games"].append({
                    "game_date": g["game_date"],
                    "opposing_team": g["opposing_team"],
                    "score": g["score_str"],
                    "won": won
                })
                
            sorted_unique_lineups = sorted(
                lineup_groups.values(),
                key=lambda x: (x["games_count"], x["wins"]),
                reverse=True
            )
            
            u_col1, u_col2, u_col3 = st.columns(3)
            with u_col1:
                st.metric("Total Alineaciones Únicas Usadas", f"{len(sorted_unique_lineups)}")
            with u_col2:
                top_rep = sorted_unique_lineups[0]["games_count"] if sorted_unique_lineups else 0
                st.metric("Alineación Más Repetida", f"{top_rep} juegos")
            with u_col3:
                w_top = sorted_unique_lineups[0]["wins"] if sorted_unique_lineups else 0
                l_top = sorted_unique_lineups[0]["losses"] if sorted_unique_lineups else 0
                pct_top = (w_top / top_rep) if top_rep > 0 else 0
                st.metric("Récord de la Alineación #1", f"{w_top} - {l_top}", f".{int(pct_top*1000):03d} PCT")
                
            st.markdown("---")
            
            # Tarjetas expandibles con detalle de cada alineación
            for idx, u_lu in enumerate(sorted_unique_lineups[:15], 1):
                pct_val = (u_lu["wins"] / u_lu["games_count"]) if u_lu["games_count"] > 0 else 0
                s1 = u_lu['starters'][0]['player_name'] if len(u_lu['starters']) > 0 else ""
                s2 = u_lu['starters'][1]['player_name'] if len(u_lu['starters']) > 1 else ""
                s3 = u_lu['starters'][2]['player_name'] if len(u_lu['starters']) > 2 else ""
                s4 = u_lu['starters'][3]['player_name'] if len(u_lu['starters']) > 3 else ""
                
                expander_title = f"🏆 Alineación #{idx} — {u_lu['games_count']} JJ ({u_lu['wins']} V - {u_lu['losses']} D | .{int(pct_val*1000):03d} PCT) — 1. {s1}, 2. {s2}, 3. {s3}, 4. {s4}..."
                
                with st.expander(expander_title, expanded=(idx == 1)):
                    c_l_left, c_l_right = st.columns(2)
                    with c_l_left:
                        for s in u_lu["starters"][:5]:
                            b_col = "#3b82f6" if s['order'] <= 3 else ("#f59e0b" if s['order'] == 4 else "#8b5cf6")
                            st.markdown(f"""
                            <div style='background: #0f172a; padding: 10px 14px; border-radius: 6px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #334155;'>
                                <div><span style='background: {b_col}; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; margin-right: 8px;'>#{s['order']}</span><b>{s['player_name']}</b></div>
                                <div><span style='background: #334155; color: #cbd5e1; padding: 2px 6px; border-radius: 4px; font-size: 12px;'>{s['position']}</span></div>
                            </div>
                            """, unsafe_allow_html=True)
                    with c_l_right:
                        for s in u_lu["starters"][5:]:
                            st.markdown(f"""
                            <div style='background: #0f172a; padding: 10px 14px; border-radius: 6px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #334155;'>
                                <div><span style='background: #64748b; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; margin-right: 8px;'>#{s['order']}</span><b>{s['player_name']}</b></div>
                                <div><span style='background: #334155; color: #cbd5e1; padding: 2px 6px; border-radius: 4px; font-size: 12px;'>{s['position']}</span></div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                    st.markdown("##### 📅 Partidos Jugados con esta Alineación Exacta")
                    g_tbl = pd.DataFrame([{
                        "Fecha": gm["game_date"],
                        "Rival": gm["opposing_team"],
                        "Marcador": gm["score"],
                        "Resultado": "Victoria" if gm["won"] else "Derrota"
                    } for gm in u_lu["games"]])
                    st.dataframe(g_tbl, use_container_width=True, hide_index=True)
                    
        # ---- VISTA 3: MATRIZ DE CALOR (HEATMAP 1-9) ----
        with subtab_matrix:
            st.markdown("#### 📊 Distribución de Titularidades en el Orden al Bate (1ro al 9no)")
            st.markdown("Muestra cuántas veces inició cada jugador en cada posición del orden ofensivo.")
            
            # Pivot table
            pivot_matrix = df_starters.pivot_table(index="Jugador", columns="Turno_Num", aggfunc="size", fill_value=0)
            
            # Renombrar columnas
            col_map = {i: f"{i}º Bate" for i in range(1, 10)}
            pivot_matrix = pivot_matrix.rename(columns=col_map)
            
            # Ordenar columnas del 1ro al 9no
            ordered_cols = [f"{i}º Bate" for i in range(1, 10) if f"{i}º Bate" in pivot_matrix.columns]
            pivot_matrix = pivot_matrix[ordered_cols]
            
            pivot_matrix["Total Titular"] = pivot_matrix.sum(axis=1)
            pivot_matrix = pivot_matrix.sort_values(by="Total Titular", ascending=False)
            
            # Plotly Heatmap
            top_players = pivot_matrix.head(15).iloc[::-1] # Invertir para visualización
            
            fig_heat = px.imshow(
                top_players[ordered_cols].values,
                x=ordered_cols,
                y=top_players.index.tolist(),
                color_continuous_scale="Blues",
                text_auto=True,
                labels=dict(x="Turno al Bate", y="Jugador", color="Juegos Titular")
            )
            fig_heat.update_layout(
                template="plotly_dark",
                height=520,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_title="Turno en el Orden al Bate",
                yaxis_title=""
            )
            st.plotly_chart(fig_heat, use_container_width=True)
            
            st.markdown("#### 📋 Tabla Completa de Titularidades por Turno")
            st.dataframe(pivot_matrix, use_container_width=True)
            
        # ---- VISTA 3: IMPACTO POR JUGADOR ----
        with subtab_player:
            st.markdown("#### 👤 Análisis de Titularidad y Récord por Jugador")
            st.markdown("Selecciona un jugador para ver en qué turnos alineó y el récord de victorias/derrotas del equipo.")
            
            all_starters_list = sorted(df_starters["Jugador"].unique().tolist())
            sel_player = st.selectbox("Seleccionar Jugador Titular", all_starters_list, key="player_lu_sel")
            
            df_p_lu = df_starters[df_starters["Jugador"] == sel_player]
            
            # Resumen por turno para este jugador
            p_turnos = df_p_lu.groupby("Turno").agg(
                Titularidades=("won", "count"),
                Victorias=("won", "sum"),
                Derrotas=("lost", "sum")
            ).reset_index()
            p_turnos["% Victorias"] = (p_turnos["Victorias"] / p_turnos["Titularidades"]).apply(lambda x: f"{x:.3f}".replace("0.", "."))
            p_turnos = p_turnos.sort_values(by="Titularidades", ascending=False)
            
            pk1, pk2, pk3 = st.columns(3)
            tot_p_games = len(df_p_lu)
            tot_p_w = int(df_p_lu["won"].sum())
            tot_p_l = int(df_p_lu["lost"].sum())
            pct_p = tot_p_w / tot_p_games if tot_p_games > 0 else 0
            
            with pk1:
                st.metric(f"Titularidades con {sel_player}", f"{tot_p_games} JJ")
            with pk2:
                st.metric("Récord del Equipo", f"{tot_p_w} - {tot_p_l}")
            with pk3:
                st.metric("% Efectividad", f".{int(pct_p*1000):03d}")
                
            st.markdown("##### 🔢 Desglose por Turno al Bate")
            st.dataframe(p_turnos, use_container_width=True, hide_index=True)
            
            st.markdown("##### 📅 Historial de Partidos como Titular")
            disp_p_games = df_p_lu[["game_date", "opposing_team", "Turno", "Posicion", "won"]].copy()
            disp_p_games["Resultado"] = disp_p_games["won"].apply(lambda x: "V" if x == 1 else "D")
            disp_p_games = disp_p_games.rename(columns={
                "game_date": "Fecha", "opposing_team": "Rival", "Turno": "Turno al Bate", "Posicion": "Posición Defensiva"
            })[["Fecha", "Rival", "Turno al Bate", "Posición Defensiva", "Resultado"]]
            
            st.dataframe(disp_p_games, use_container_width=True, hide_index=True)
            
    else:
        st.info("No se encontraron datos de alineaciones para la temporada.")

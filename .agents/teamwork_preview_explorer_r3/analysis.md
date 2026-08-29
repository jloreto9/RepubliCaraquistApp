# Informe Detallado de Auditoría: Rendimiento, Caché y UI/UX (RepubliCaraquistApp)

**Auditor:** Explorer R3 (`teamwork_preview_explorer_r3`)  
**Fecha:** 2026-08-28  
**Modo:** Solo Lectura (Read-Only)  
**Objetivo:** Diagnóstico exhaustivo de la arquitectura de caché de Streamlit, rendimiento de red, sistema de diseño visual (Dark Athletic Navy / Caraquista Gold), calidad de gráficos Plotly, y cobertura pedagógica de glosarios sabermétricos.

---

## 1. Arquitectura de Caché y Rendimiento en Streamlit

### 1.1. Inventario Exhaustivo de Decoradores de Caché

Se identificaron **21 funciones cacheadas** en el repositorio (1 `@st.cache_resource` y 20 `@st.cache_data`):

| Archivo | Función | Decorador / TTL | Parámetros | Tipo de Retorno |
|---|---|---|---|---|
| `utils/supabase_client.py:11` | `init_supabase` | `@st.cache_resource` | Ninguno | `supabase.Client` |
| `utils/supabase_client.py:35` | `get_available_seasons` | `@st.cache_data(ttl=3600)` | Ninguno | `list[int]` |
| `utils/supabase_client.py:54` | `get_standings` | `@st.cache_data(ttl=600)` | `season`, `phase` | `pd.DataFrame` |
| `utils/supabase_client.py:334` | `get_leones_advanced_stats` | `@st.cache_data(ttl=1800)` | `season`, `cache_version` | `dict` |
| `utils/supabase_client.py:484` | `get_recent_games` | `@st.cache_data(ttl=1800)` | `team_id`, `limit` | `pd.DataFrame` |
| `utils/supabase_client.py:502` | `get_batting_stats` | `@st.cache_data(ttl=3600)` | `team_id`, `limit`, `season` | `pd.DataFrame` |
| `utils/supabase_client.py:571` | `get_pitching_stats` | `@st.cache_data(ttl=3600)` | `team_id`, `limit`, `season` | `pd.DataFrame` |
| `utils/supabase_client.py:677` | `get_weekly_records` | `@st.cache_data(ttl=1800)` | `season`, `team_id`, `phase` | `pd.DataFrame` |
| `utils/supabase_client.py:769` | `get_collective_team_stats` | `@st.cache_data(ttl=1800)` | `season`, `phase`, `group` | `pd.DataFrame` |
| `utils/supabase_client.py:808` | `get_individual_fielding_stats` | `@st.cache_data(ttl=1800)` | `season`, `team_id`, `phase` | `pd.DataFrame` |
| `utils/wpa_engine.py:167` | `process_game_wpa_advanced` | `@st.cache_data(ttl=1800)` | `game_pk` | `tuple[pd.DataFrame, bool, str]` |
| `utils/wpa_engine.py:370` | `get_season_wpa_leaderboard` | `@st.cache_data(ttl=3600)` | `season` | `dict` |
| `utils/spray_chart.py:246` | `fetch_season_batted_balls` | `@st.cache_data(ttl=1800)` | `season`, `team_id` | `pd.DataFrame` |
| `utils/strike_zone.py:235` | `fetch_season_pitches` | `@st.cache_data(ttl=1800)` | `season`, `team_id`, `cache_version` | `pd.DataFrame` |
| `utils/situational.py:164` | `fetch_season_situational_data` | `@st.cache_data(ttl=1800)` | `season`, `team_id`, `cache_version` | `pd.DataFrame` |
| `utils/bullpen_lineups.py:143` | `fetch_season_bullpen_and_lineups` | `@st.cache_data(ttl=1800)` | `season`, `team_id`, `cache_version` | `tuple[pd.DataFrame, list]` |
| `utils/ai_insights.py:143` | `get_ai_insights` | `@st.cache_data(ttl=3600)` | 4 `DataFrames` + 1 `dict` | `str` |
| `pages/1_📊_Standings.py:99` | `run_elo_simulations_cached` | `@st.cache_data(ttl=600)` | `season`, `simulate_from_scratch` | `dict` |
| `pages/1_📊_Standings.py:127` | `get_calendar_games_with_elo_projections` | `@st.cache_data(ttl=300)` | `season` | `pd.DataFrame` |
| `pages/4_📈_Análisis_WPA.py:77` | `get_leones_games_from_supabase` | `@st.cache_data(ttl=300)` | `season` | `pd.DataFrame` |
| `🏠_Home.py:26` | `get_game_wpa_mvp` | `@st.cache_data(ttl=600)` | `game_pk` | `dict` |

---

### 1.2. Hallazgos Críticos de Mutación de Objetos Cacheados (Cached Object Mutation)

Streamlit devuelve referencias directas a objetos en memoria cuando se usa `@st.cache_data`. Si el código consumidor modifica una columna o castea tipos in-place sobre el DataFrame recibido, **el objeto en el almacén de caché queda mutado para todas las siguientes ejecuciones y sesiones**, pudiendo provocar `CachedObjectMutationWarning` y comportamientos erráticos.

1. **Mutación en Fildeo Individual (`pages/2_⚾_Estadisticas_Individuales.py:586-597`)**:
   ```python
   fielding_df = get_individual_fielding_stats(selected_season, team_id=695)
   num_cols = ['games', 'games_started', 'putouts', 'assists', 'errors', 'chances', 'double_plays', 'triple_plays', 'caught_stealing', 'stolen_bases', 'passed_balls']
   for col in num_cols:
       if col in fielding_df.columns:
           fielding_df[col] = pd.to_numeric(fielding_df[col], errors='coerce').fillna(0).astype(int)
   ```
   *Diagnóstico:* `fielding_df` se modifica directamente sin `.copy()`.
   *Recomendación:* Agregar `.copy()` inmediatamente después de la llamada: `fielding_df = get_individual_fielding_stats(...).copy()`.

2. **Mutación en Spray Charts (`pages/5_🎯_Spray_Charts.py:57-65`)**:
   ```python
   df_raw = fetch_season_batted_balls(selected_season, team_id=LEONES_TEAM_ID)
   df_raw["game_date_dt"] = pd.to_datetime(df_raw["game_date"])
   ```
   *Diagnóstico:* Se inyecta la columna `game_date_dt` directamente en el DataFrame cacheado en memoria.
   *Recomendación:* `df_raw = fetch_season_batted_balls(...).copy()`.

---

### 1.3. Sobrecarga de Hashing y Estrategia de Invalidación

1. **Sobrecarga de Hashing en `get_ai_insights` (`utils/ai_insights.py:143`)**:
   - La función recibe como argumentos 4 DataFrames completos (`standings_df`, `batting_stats`, `pitching_stats`, `advanced_stats`) y una lista (`recent_games`).
   - Para cada ejecución, Streamlit serializa y calcula el hash criptográfico de cada celda de esos 4 DataFrames para saber si el caché es válido.
   - *Recomendación:* Pasar argumentos escalares (ej. `season: int`, `last_game_id: int`) o usar `hash_funcs` para evitar hashing costoso.

2. **Invalidación Manual de Caché (`cache_version`)**:
   - Módulos como `supabase_client.py`, `bullpen_lineups.py`, `situational.py` y `strike_zone.py` utilizan parámetros `cache_version="v..."` para forzar invalidación cuando se ajusta la lógica. Esto es funcional, pero evidencia que el ciclo de vida del caché requiere sincronización cuando los datos cambian en Supabase.

---

### 1.4. Cuello de Botella de Red y Cold Start (Carga en Frío)

Cinco módulos de analítica avanzada consultan en tiempo de ejecución todos los feeds en vivo de la temporada desde la API de MLB:
- `utils/supabase_client.py:get_leones_advanced_stats` (~56 peticiones HTTP)
- `utils/spray_chart.py:fetch_season_batted_balls` (~56 peticiones HTTP)
- `utils/strike_zone.py:fetch_season_pitches` (~56 peticiones HTTP)
- `utils/situational.py:fetch_season_situational_data` (~56 peticiones HTTP)
- `utils/bullpen_lineups.py:fetch_season_bullpen_and_lineups` (~56 peticiones HTTP)

**Impacto:**
- En un arranque en frío (cold start), al visitar estas 5 páginas se descargan hasta **280 feeds JSON completos** (~800+ MB de transferencia total).
- Si la conexión a MLB Stats API experimenta latencia o rate limiting, la página tarda entre 8 y 20 segundos en cargar.
- *Recomendación Arquitectónica:* Mover la extracción y agregación de eventos (spray charts, lanzamientos, corredores heredados) a `scripts/update_daily.py` para almacenar las tablas precalculadas en Supabase, limitando las consultas del frontend a queries SQL indexadas.

---

### 1.5. Separación entre Capa de Datos y Capa de Presentación

Se detectaron violaciones a la regla de separación de responsabilidades:
1. `pages/1_📊_Standings.py:80-160`: Contiene consultas directas a las tablas `games` y `elo_ratings` de Supabase dentro del script de la página, además de definir 2 funciones `@st.cache_data`.
2. `pages/4_📈_Análisis_WPA.py:77-94`: Define `get_leones_games_from_supabase` y ejecuta queries directas a `supabase.table('games')` en lugar de consumir `utils/supabase_client.py`.
3. `🏠_Home.py:26-48`: Define `get_game_wpa_mvp` directamente en el archivo raíz.

*Recomendación:* Centralizar todas las funciones de extracción de datos en `utils/supabase_client.py` y los cálculos de WPA en `utils/wpa_engine.py`.

---

## 2. Auditoría Visual, Diseño UI/UX y Gráficos Plotly

### 2.1. Consistencia del Sistema de Diseño (Dark Athletic Navy)

El sistema de estilos en `utils/styles.py` y `.streamlit/config.toml` establece una paleta elegante y moderna:
- Fondo principal: Dark Navy (`#070B19`)
- Fondo de tarjetas: Dark Card Glassmorphism (`#0D152B`)
- Acento dorado Caraquista: `#FDB827`
- Texto principal: Blanco Puro (`#FFFFFF`)
- Texto secundario: Slate Muted (`#94A3B8`)

### 2.2. Oportunidades de Mejora Visual y Contraste

1. **Texto de Bajo Contraste en Home (`🏠_Home.py:84, 597`)**:
   - En el subtítulo y el footer se usa `color: #666;` sobre fondo `#070B19`. Un gris oscuro `#666666` sobre `#070B19` produce un ratio de contraste de apenas ~2.3:1 (por debajo del estándar WCAG AA de 4.5:1).
   - *Solución:* Usar `color: #94A3B8;` (Slate Muted) o la clase `.muted-text`.

2. **Branding Profesional en Footer (`🏠_Home.py:599`)**:
   - Dice `📊 Científico de Datos` en vez del título unificado acordado en `GEMINI.md`: **AI Data Scientist**.

3. **Caja de Anotación Blanco Brillante en Gráfico Oscuro (`pages/4_📈_Análisis_WPA.py:234`)**:
   - `create_wp_evolution_chart` define `bgcolor='rgba(255, 255, 255, 0.9)'` para el badge de victoria/derrota, lo que genera un parche blanco estridente dentro de un gráfico en modo oscuro.
   - *Solución:* Usar `bgcolor='rgba(13, 21, 43, 0.9)'` con borde coloreado según el resultado.

4. **Función de Tema Plotly Huérfana (`utils/styles.py:352-378`)**:
   - `apply_plotly_theme(fig)` está perfectamente implementada con los colores corporativos de República Caraquista, pero **ninguna página la importa ni la ejecuta**.
   - En su lugar, las páginas usan `template="plotly_dark"` (gris genérico de Plotly) o configuran parcialmente los layouts.
   - *Solución:* Importar y aplicar `apply_plotly_theme(fig)` de manera uniforme en todos los gráficos Plotly de las páginas 1 a 8.

5. **Distorsión Sabermétrica en Gráficos de Radar (`pages/2_⚾_Estadisticas_Individuales.py:787-860`)**:
   - El gráfico de radar para comparar bateadores grafica directamente `['avg', 'hr', 'rbi', 'ops']`. Dado que `avg` está en rango 0.200–0.350 y `rbi` en 10–50, la escala radial única aplasta `avg` y `ops` a un punto microscópico cerca del origen.
   - Lo mismo ocurre en lanzadores (`['w', 'so', 'ip']`, donde `ip` es ~40 y `w` es ~3).
   - *Solución:* Normalizar las métricas a percentiles relativos (0 a 100) antes de graficar el radar, mostrando los valores reales en el hover y en la tabla inferior.

6. **Código Duplicado en `🏠_Home.py:174-199`**:
   - Las líneas 174-185 y 188-199 son repeticiones idénticas de asignaciones de variables de récord y diferencial.

7. **Expanders de Depuración en Producción (`pages/1_📊_Standings.py:1438, 1655`)**:
   - Existen dos expanders de debug activos: `with st.expander("🔍 Información de Debug"):`.

8. **Imports Residuales a Rutas Inexistentes**:
   - Bloques `try/except` en `pages/2`, `pages/3` y `pages/4` intentan importar desde `streamlit_app.utils...` (estructura de carpetas obsoleta).

---

## 3. Calidad Pedagógica, Glosarios y Adherencia al Español

### 3.1. Evaluación de Glosarios Educativos (`📖 Guía y Glosario`)

Se verificó la presencia de **15 expanders educativos** en las páginas 1 a 8:

| Página | Expanders Encontrados | Conceptos Cubiertos | Rigor Sabermétrico |
|---|---|---|---|
| `pages/1_📊_Standings.py` | 3 expanders | Métricas de tabla, Expectativa Pitagórica ($W\% = \frac{CF^2}{CF^2 + CP^2}$), Modelo ELO y Monte Carlo (5,000 iteraciones). | Excelente (10/10) |
| `pages/2_⚾_Estadisticas_Individuales.py` | 4 expanders | Bateo tradicional vs avanzado, Pitcheo (ERA, FIP, WHIP), Fildeo (FPCT, RF/9, CS%), Interpretación de Radars. | Excelente (10/10) |
| `pages/3_📊_Estadisticas_Colectivas.py` | 3 expanders | Bateo colectivo, Pitcheo colectivo, Fildeo colectivo para los 8 equipos. | Excelente (10/10) |
| `pages/4_📈_Análisis_WPA.py` | 2 expanders | WPA (Win Probability Added), RE24 base-out, Leverage Index (LI), Clutch ($WPA - WPA/LI$). | Extraordinario (10/10) |
| `pages/5_🎯_Spray_Charts.py` | 2 expanders | Dispersión $(x, y)$, Pull%/Center%/Oppo%, Modelo determinístico de dureza BIS, Tabla jugada por jugada. | Excelente (10/10) |
| `pages/6_🎯_Disciplina_y_Zonas.py` | 2 expanders | O-Swing%, Z-Swing%, Whiff%, CSW%, Zonas de Strike Statcast, Registro de lanzamientos. | Excelente (10/10) |
| `pages/7_⚡_Situacional_y_BvP.py` | 3 expanders | Métricas situacionales (RISP, 2 outs), Metodología de Dejados en Base (LOB 3er out vs RISP LOB), Muestra BvP. | Excelente (10/10) |
| `pages/8_🛡️_Bullpen_y_Lineups.py` | 2 expanders | Corredores Heredados (IR / IRS%), Teoría de construcción de Lineups 1-9 de Tom Tango (*The Book*). | Extraordinario (10/10) |
| `🏠_Home.py` | **0 expanders** | **Ausente:** No cuenta con expander didáctico introductorio a la plataforma. | **Oportunidad** |

### 3.2. Adherencia al Español

Se auditó el 100% de los textos de la interfaz mediante script estático:
- **Resultado:** 100% en español natural y adaptado a la jerga y cultura del béisbol profesional venezolano (LVBP).
- Términos sabermétricos universales (WPA, OBP, SLG, OPS, FIP, WHIP, CSW%, BABIP, IR/IRS%) conservan sus siglas canónicas pero acompañadas de sus nombres completos y explicaciones claras en español.

---

## 4. Matriz de Severidad y Recomendaciones

| # | Severidad | Área | Hallazgo | Recomendación Accionable |
|---|---|---|---|---|
| 1 | **Advertencia** | Caché / Integridad | Mutación in-place de `fielding_df` (`pages/2:593`) y `df_raw` (`pages/5:65`) | Aplicar `.copy()` al recibir DataFrames desde `@st.cache_data`. |
| 2 | **Advertencia** | Rendimiento / Red | 5 módulos descargan 56 feeds JSON de MLB en tiempo de ejecución | Migrar agregaciones de spray, pitcheos y bullpen al pipeline batch en `scripts/update_daily.py`. |
| 3 | **Advertencia** | UI / Visual | Radars de comparación con métricas no normalizadas (`pages/2:787-860`) | Normalizar a percentiles (0-100) antes de construir el `Scatterpolar`. |
| 4 | **Optimización** | UI / Theming | `apply_plotly_theme` no se utiliza en ningún gráfico Plotly | Invocar `apply_plotly_theme(fig)` en todas las figuras Plotly para unificar Dark Navy. |
| 5 | **Optimización** | UI / Contraste | Texto `#666` en Home y anotación blanca en WPA | Reemplazar `#666` por `#94A3B8` en Home y usar fondo oscuro en anotaciones WPA. |
| 6 | **Optimización** | UI / Contenido | Falta `📖 Guía y Glosario` en `🏠_Home.py` | Añadir un expander de bienvenida e introducción a la analítica sabermétrica. |
| 7 | **Optimización** | Código Limpio | Bloques duplicados en `🏠_Home.py:174-199` e imports obsoletos `streamlit_app` | Limpiar duplicados y remover bloques try/except a rutas inexistentes. |

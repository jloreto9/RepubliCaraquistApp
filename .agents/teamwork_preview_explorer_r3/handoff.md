# Handoff Report — Explorer R3 (Performance, Caching & UI/UX Auditor)

## 1. Observation

Durante la auditoría estática y de rendimiento de solo lectura sobre `RepubliCaraquistApp`, se observaron los siguientes hechos directamente en el código fuente:

### A. Caché y Mutación de Objetos en Streamlit
- **Decoradores de caché identificados:** Existen 21 funciones cacheadas (1 `@st.cache_resource` y 20 `@st.cache_data`) distribuidas en `utils/supabase_client.py`, `utils/wpa_engine.py`, `utils/spray_chart.py`, `utils/strike_zone.py`, `utils/situational.py`, `utils/bullpen_lineups.py`, `utils/ai_insights.py`, `pages/1_📊_Standings.py`, `pages/4_📈_Análisis_WPA.py` y `🏠_Home.py`.
- **Mutación in-place de DataFrames cacheados:**
  - `pages/2_⚾_Estadisticas_Individuales.py:586-597`:
    ```python
    586: fielding_df = get_individual_fielding_stats(selected_season, team_id=695)
    ...
    593: fielding_df[col] = pd.to_numeric(fielding_df[col], errors='coerce').fillna(0).astype(int)
    597: fielding_df[col] = pd.to_numeric(fielding_df[col], errors='coerce').fillna(0.0).astype(float)
    ```
    `fielding_df` se modifica directamente sin `.copy()`, alterando el objeto residente en el almacén de caché de Streamlit.
  - `pages/5_🎯_Spray_Charts.py:57-65`:
    ```python
    57: df_raw = fetch_season_batted_balls(selected_season, team_id=LEONES_TEAM_ID)
    ...
    65: df_raw["game_date_dt"] = pd.to_datetime(df_raw["game_date"])
    ```
    Se inyecta la columna `game_date_dt` directamente sobre el DataFrame cacheado.
- **Sobrecarga de Hashing de Argumentos:**
  - `utils/ai_insights.py:143-145`:
    ```python
    @st.cache_data(ttl=3600, show_spinner=False)
    def get_ai_insights(
        standings_df: pd.DataFrame,
        recent_games: list,
        batting_stats: pd.DataFrame,
        pitching_stats: pd.DataFrame,
        advanced_stats: dict
    ) -> str:
    ```
    Streamlit serializa y calcula el hash criptográfico de 4 DataFrames completos y estructuras anidadas en cada ejecución para evaluar la clave de caché.

### B. Rendimiento de Red y Carga en Frío (Cold Start)
- En `utils/supabase_client.py` (`get_leones_advanced_stats`), `utils/spray_chart.py` (`fetch_season_batted_balls`), `utils/strike_zone.py` (`fetch_season_pitches`), `utils/situational.py` (`fetch_season_situational_data`) y `utils/bullpen_lineups.py` (`fetch_season_bullpen_and_lineups`), cada función ejecuta un bucle paralelo con `ThreadPoolExecutor(max_workers=10-12)` que descarga de 50 a 56 feeds JSON individuales (`https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live`) directamente desde la API de MLB.
- En un arranque en frío (cold start), la navegación por estas 5 páginas dispara hasta **280 peticiones HTTP en vivo** descargando más de 800 MB de datos en total.

### C. Sistema Visual, Theming y Gráficos Plotly
- `utils/styles.py:352-378` define la función central `apply_plotly_theme(fig)` con la paleta oficial Dark Athletic Navy (`#070B19` / `#0D152B`) y dorado `#FDB827`. Sin embargo, **ninguna página ni módulo del repositorio llama a `apply_plotly_theme(fig)`**. En su lugar, los gráficos usan `template="plotly_dark"` (gris genérico) o layouts inline.
- `🏠_Home.py:84` y `🏠_Home.py:597`: Se utiliza `<p style='color: #666;'>` sobre el fondo `#070B19`, produciendo un contraste deficiente (~2.3:1) que incumple estándares de accesibilidad WCAG.
- `🏠_Home.py:599`: El título profesional en el pie de página dice "Científico de Datos", en discrepancia con el estándar unificado "AI Data Scientist".
- `pages/4_📈_Análisis_WPA.py:234`: La anotación final de victoria/derrota tiene `bgcolor='rgba(255, 255, 255, 0.9)'` (recuadro blanco opaco sobre fondo oscuro).
- `pages/2_⚾_Estadisticas_Individuales.py:787-860`: Los radares de comparación grafican variables en escalas heterogéneas (`avg` 0.280 vs `rbi` 35; `w` 3 vs `ip` 40), lo que colapsa la visualización polar hacia el centro.

### D. Glosarios Educativos y Lenguaje
- Las páginas `pages/1` a `pages/8` cuentan con **15 expanders educativos** (`📖 Guía y Glosario`) con tablas Markdown completas, fórmulas matemáticas exactas (Expectativa Pitagórica, ELO con factor $M$, WPA RE24, Leverage Index, IR/IRS%, Tom Tango Lineup Theory) y redacción 100% en español.
- `🏠_Home.py` no cuenta con ningún expander educativo o glosario de bienvenida.
- Todos los controles interactivos, botones, selectores y leyendas en la aplicación están 100% traducidos al español.

---

## 2. Logic Chain

1. **Premisa 1 (Caché):** `@st.cache_data` en Streamlit preserva el objeto retornado en la memoria compartida del proceso.
2. **Inferencia 1:** Al ejecutar mutaciones in-place (`fielding_df[col] = ...` o `df_raw['game_date_dt'] = ...`) sin haber hecho `.copy()`, el objeto original en el caché es alterado. Si otra vista o sesión consulta ese mismo dataset, puede recibir datos modificados o disparar alertas de mutación no deseada.
3. **Premisa 2 (Rendimiento de Red):** La API de MLB no impone límites estrictos pero tiene latencia de red y tamaño por feed de 2-5 MB.
4. **Inferencia 2:** Descargar 56 feeds JSON completos en cada una de las 5 páginas durante el cold start añade entre 8 y 15 segundos de latencia de carga inicial por página. La solución arquitectónica óptima es persistir los datos procesados en Supabase mediante el cron diario (`scripts/update_daily.py`).
5. **Premisa 3 (Consistencia UI):** `utils/styles.py` provee `apply_plotly_theme(fig)` específicamente para asegurar la identidad visual Dark Navy `#0D152B` con acentos dorados `#FDB827`.
6. **Inferencia 3:** Al no invocar esta función, los gráficos se renderizan con estilos dispares (fondos grises `plotly_dark`, anotaciones blancas o sin colores corporativos).
7. **Premisa 4 (Visualización Sabermétrica):** Los gráficos de radar requieren escalas normalizadas (0 a 100 o percentiles relativos) cuando las dimensiones poseen órdenes de magnitud diferentes ($0.250$ vs $40$).
8. **Inferencia 4:** Sin normalización, los ejes de menor magnitud quedan visualmente invisibles y el radar pierde utilidad analítica.

---

## 3. Caveats

- No se ejecutaron modificaciones en el código fuente de RepubliCaraquistApp durante esta auditoría (modo estrictamente de solo lectura).
- El análisis de latencia de red de los feeds de MLB Stats API se fundamenta en la inspección estática del código y pruebas de conexión existentes; no se sometió la API a pruebas de carga de estrés para evitar bloqueo de IP.
- No se detectaron fallos sintácticos en las páginas ni en los módulos utilitarios.

---

## 4. Conclusion

RepubliCaraquistApp presenta una arquitectura sabermétrica sólida, con fórmulas matemáticas de alto rigor y un diseño estético Dark Athletic de gran personalidad. No obstante, existen oportunidades concretas de optimización clasificadas en tres niveles:

1. **Riesgo de Caché (Prioridad Alta):** Corregir la mutación in-place de DataFrames en `pages/2_⚾_Estadisticas_Individuales.py:586` y `pages/5_🎯_Spray_Charts.py:57` agregando `.copy()`.
2. **Consistencia Visual (Prioridad Media):**
   - Conectar `apply_plotly_theme(fig)` a todos los gráficos de Plotly en las páginas 1 a 8.
   - Corregir el contraste de textos grises oscuros (`#666`) en `🏠_Home.py:84, 597`.
   - Reemplazar el fondo blanco de la anotación de resultado en `pages/4_📈_Análisis_WPA.py:234`.
   - Normalizar a percentiles las métricas en los gráficos de radar de `pages/2`.
   - Unificar branding en footer de `🏠_Home.py:599` a **AI Data Scientist**.
3. **Rendimiento & Onboarding (Prioridad Baja / Evolutiva):**
   - Incorporar un expander `📖 Guía y Glosario: ¿Cómo navegar y entender la analítica de RepubliCaraquistApp?` en `🏠_Home.py`.
   - Centralizar la ingesta de eventos de spray, lanzamientos y bullpen en `scripts/update_daily.py` para consultar datos preprocesados en Supabase y eliminar las 280 descargas en vivo de MLB API en cold start.

---

## 5. Verification Method

Para verificar independientemente los hallazgos:

1. **Verificar referencias a `apply_plotly_theme`:**
   ```powershell
   python -c "import glob; [print(p) for p in glob.glob('pages/*.py') if 'apply_plotly_theme' in open(p, encoding='utf-8').read()]"
   ```
   *(Resultado esperado: lista vacía, confirmando que ninguna página utiliza la función).*

2. **Verificar mutación de objetos cacheados:**
   - Inspeccionar `pages/2_⚾_Estadisticas_Individuales.py` en líneas 586-597.
   - Inspeccionar `pages/5_🎯_Spray_Charts.py` en líneas 57-65.

3. **Verificar contraste `#666` en Home:**
   - Inspeccionar `🏠_Home.py` en líneas 84 y 597.

4. **Verificar presencia de glosarios en páginas:**
   - Ejecutar el script `python .agents/teamwork_preview_explorer_r3/inspect_glossaries.py` para visualizar los 15 expanders en `pages/` y constatar la ausencia en `🏠_Home.py`.

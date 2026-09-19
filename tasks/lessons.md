# Lessons Learned — RepubliCaraquistApp (Streamlit)

## Visualización y Tarjetas de Pitcheo (Thomas Nestico)

### 1. Arquitectura de GridSpec (20x20)
- **Cabecera:** El headshot debe asignarse exclusivamente a `gs[1, 1]`, la biografía a `gs[1, 2:6]` (garantizando 72 unidades de ancho para evitar colisiones con fotos o logos), y el logo a `gs[1, 6]`.
- **Textos de Biografía:** El nombre del lanzador debe posicionarse en `y=0.88` para balancearse verticalmente con el headshot y el logo, usando tamaños de fuente dinámicos según la longitud del rival o fecha.

### 2. Aislamiento del Panel Gráfico Triple (Fila 3)
- Nunca declarar los 3 subplots adyacentes directamente sobre el GridSpec principal sin espaciado.
- Debe utilizarse siempre: `GridSpecFromSubplotSpec(1, 3, subplot_spec=gs[3, 1:7], wspace=0.36)` para garantizar un 36% de separación horizontal que impida el solapamiento de títulos y etiquetas de los ejes Y.

### 3. Consistencia Estadística en Modo PBP (LVBP)
- **Gráfico de Carga:** Barras apiladas (Strikes en la base + Bolas en la parte superior) con etiquetas enteras `Inn {i}` (nunca marcas decimales continuas).
- **Leverage Index:** Gráfico de líneas con cota visual promedio de 1.0 LI y etiquetas numéricas por punto.
- **Platoon Splits:** Comparar únicamente tasas porcentuales (0-100% para Strike%, Whiff% y CSW%) con etiquetas sobre las barras, y registrar el conteo absoluto de pitcheos (`N=X`) en la leyenda para evitar mezclas de escalas.
- **Fallback de Pitcheos:** `game_summary.get('pitches') or analysis.get('total_pitches') or len(pitches) or 0` para evitar desplegar 0 lanzamientos en el boxscore.

### 4. Pie de Página y Atribución
- Footer organizado en 2 líneas independientes para evitar colisiones: izquierda con marca `@republicaraquista • Jorge Leonardo Loreto`, centro con metodología/subtítulo y derecha con créditos a Thomas Nestico (@TJStats) y origen de la data.

### 5. Política de Base de Datos (Zero Bloat)
- La data Statcast de MLB/MiLB descargada debe almacenarse exclusivamente en caché local Parquet (`.cache/statcast/`) y nunca ocupar espacio ni tablas en Supabase.

### 6. Prohibición Estricta de Jerga Técnica y Nombres de Librerías en UI
- **Cero nombres de librerías en la interfaz:** Prohibido exhibir nombres de librerías internas (como `Matplotlib`, `Matplotlib HD`, `FastAPI`, `Pandas`, etc.) en títulos, subtítulos, botones, tabs o modales dirigidos al usuario. Usar denominaciones descriptivas y sabermétricas limpias (ej: *"Tarjeta Panorámica Oficial de Pitcheo"*, *"Descargar Tarjeta HD"*).

### 7. Compatibilidad Universal de Argumentos en Generadores Gráficos
- Las firmas de exportación gráfica de alto nivel (como `build_pitching_summary_card`) deben aceptar indistintamente los pares de argumentos utilizados entre capas de la aplicación: `pitcher_info` / `pitcher_data`, `game_summary` / `game_data`, `analysis` / `pitch_analysis`, modos temporales (`game`, `season`, `range`), DataFrames Statcast y `**kwargs` para prevenir `TypeError` por desajuste de parámetros nombrados.

### 8. Proporción de Aspecto 1:1 en Tarjetas Cuadradas LVBP y Eliminación de Distorsión
- **Clasificación del error:** Ruptura de fidelidad visual por redimensionamiento destructivo (forzar un canvas 1:1 a 16:9).
- **Causa raíz:** `build_lvbp_matplotlib_summary` genera un canvas cuadrado `(20, 20)` (1:1). Al finalizar, `build_pitching_summary_card` redimensionaba indiscriminadamente a `CANVAS_SIZE = (2400, 1350)` (16:9), aplastando verticalmente los elementos, achatando fotos y deformando textos.
- **Regla específica:**
  1. Separar los tamaños canónicos de exportación: `CANVAS_SIZE = (2400, 1350)` para MLB (16:9) y `CANVAS_SIZE_LVBP = (2400, 2400)` para LVBP (1:1).
  2. En modo temporada/rango de LVBP, emplear los 3 gráficos sabermétricos exactos: Bolas y Strikes apilados, Whiff% por salida y CSW% por salida (con umbral de 30% élite).
  3. En la cuadrícula, insertar un espaciador vertical (`gs[4]`) de al menos 4 unidades entre los subplots y la tabla inferior para garantizar que las fechas rotadas a 45° nunca colisionen con los encabezados.
  4. Enriquecer los `game_logs` con `get_game_pitch_data` de forma concurrente para que la columna de Pitcheos muestre el desglose `P (S-B)` en vez de guiones vacíos.

## Políticas de Red y Prevención de Bloqueos (Curls & Timeouts)

### 1. Requisito Innegociable de Timeouts en `curl`
- En shells, scripts `.sh` / `.bat`, Dockerfiles, workflows de CI/CD y healthchecks de contenedores, la invocación de `curl` sin banderas de timeout corre el riesgo de congelar el proceso indefinidamente si la conexión se bloquea o el servidor no responde ("fatal").
- Banderas estándar:
  - Chequeos de salud: `curl -f --connect-timeout 5 --max-time 15 ...`
  - Descargas e instalaciones: `curl -fsSL --connect-timeout 15 --max-time 120 --retry 3 --retry-delay 2 ...`
  - Pruebas rápidas CLI / PowerShell: `curl.exe -sS -I --connect-timeout 5 -m 10 ...`

### 2. Timeouts en Peticiones HTTP y Sockets en Python
- Todas las peticiones con `requests` o `urllib.request` deben declarar un argumento `timeout=` explícito (ej: `timeout=15` o `timeout=30`).
- Fijar siempre `socket.setdefaulttimeout(30.0)` al inicio de la aplicación para blindar llamadas internas de librerías de terceros (`pybaseball`, etc.).

## Gestión de Estado y Ciclo de Vida de Widgets en Streamlit

### 1. Robustez en Alternancia de Ramas, Fases y Caché
- **Prohibición de `importlib.reload` en producción:** Nunca invocar `importlib.reload` en scripts de páginas sobre módulos que utilizan decoradores de caché (`@st.cache_data`), ya que redefinen las funciones en memoria, invalidando los hashes de firma y provocando `TypeError: _handle_cache_miss` en `cache_utils.py`.
- **Claves de widgets dinámicas / scoped:** Cuando las opciones de un `st.selectbox` o `st.radio` dependen del contexto (ej: `branch`, `season`, `phase`, `pitcher_id`), usar siempre claves dinámicas compuestas (ej: `f"sb_game_select_{active_branch}_{effective_season}_{selected_phase}_{p_id}"`).
- **Purga defensiva de claves obsoletas:** Antes de instanciar un widget cuyo valor anterior pueda quedar huérfano, verificar si la clave existe en `st.session_state` y no pertenece a las nuevas opciones (`if k in st.session_state and st.session_state[k] not in options: del st.session_state[k]`). Asimismo, purgar claves hijas en los callbacks o bloques de alternancia de ramas (`new_b != st.session_state["active_branch"]`).
- **Inmutabilidad de estado de widgets padre:** Nunca mutar en medio de la ejecución del script claves de `st.session_state` vinculadas a widgets ya instanciados en el sidebar (como `st.session_state["pitcher_season"] = fallback_s`), ya que provoca desincronización y advertencias de mutación posterior. En su lugar, utilizar variables locales de ámbito efectivo (`effective_season = fallback_s`).


# Análisis Técnico y Auditoría de Código — Explorer R1
**Fecha:** 2026-08-29T00:51:00Z  
**Objetivo:** Diagnóstico de Arquitectura, Sintaxis, Compilación AST, Integridad de Importaciones y Dependencias para `RepubliCaraquistApp`.  
**Alcance:** 24 archivos Python (`🏠_Home.py`, `Home.py`, `app.py`, `pages/*.py`, `utils/*.py`, `scripts/*.py`), configuración CI/CD (`.github/workflows/`), contenedor (`.devcontainer/`), entorno Streamlit (`.streamlit/`) y dependencias (`requirements.txt`).

---

## 1. Resumen Ejecutivo

| Métrica / Dimensión | Resultado | Estado |
|---|---|---|
| **Archivos Python Evaluados** | 24 archivos | Evaluados al 100% |
| **Compilación AST (`py_compile`)** | 24 / 24 exitosos (0 errores de sintaxis) | ✅ PASS |
| **Archivos con UTF-8 BOM** | 4 archivos (`app.py`, `Home.py`, `scripts/elo_sanity_check.py`, `utils/wpa_engine.py`) | ⚠️ ADVERTENCIA |
| **Ciclos de Importación (Imports Circulares)** | 0 ciclos detectados en todo el repositorio | ✅ PASS |
| **Símbolos Exportados en `utils/`** | 100% resueltos (0 imports rotos hacia `utils/`) | ✅ PASS |
| **Ejecución Local de Scripts** | `scripts/update_daily.py` falla con `ModuleNotFoundError` si no se exporta `PYTHONPATH` | 🚨 CRÍTICO |
| **Dependencias en `requirements.txt`** | 10 paquetes declarados / 0 versiones fijadas (`unpinned`) | ⚠️ ADVERTENCIA |
| **Dependencia No Utilizada** | `scipy` declarada pero nunca importada en el repositorio | ⚠️ ADVERTENCIA |
| **Módulo Huérfano (Dead Code)** | `utils/ai_insights.py` (usa `openai`, no invocado por ninguna página) | ⚠️ ADVERTENCIA |
| **Suite de Pruebas Automatizadas** | Directorio `tests/` inexistente en el repositorio | ⚠️ ADVERTENCIA |
| **Seguridad y Consultas Supabase** | 100% consultas de solo lectura en UI; credenciales vía env/secrets | ✅ PASS |

---

## 2. Diagnóstico Detallado por Componente

### 2.1. Compilación y Sintaxis AST
Se ejecutó validación sintáctica y compilación de bytecode con `py_compile` sobre los 24 archivos Python del proyecto:
- **Resultado:** 24/24 archivos superaron la compilación sin errores de sintaxis (`SyntaxError` / `IndentationError`).
- **Codificación:** 4 archivos contienen la marca de orden de bytes UTF-8 BOM (`\xef\xbb\xbf`):
  1. `app.py`
  2. `Home.py`
  3. `scripts/elo_sanity_check.py`
  4. `utils/wpa_engine.py`
  *Impacto:* Si bien el intérprete de Python en Windows/Linux lo ignora al ejecutar archivos directamente, herramientas de análisis estático o parsers que procesan texto sin `utf-8-sig` pueden generar fallos (`SyntaxError: invalid non-printable character U+FEFF`).

### 2.2. Importaciones y Resolución de Módulos

#### A. Fallo de `ModuleNotFoundError` en `scripts/update_daily.py`
- **Ubicación:** `scripts/update_daily.py:7`
- **Código:**
  ```python
  from utils.elo import BASE_ELO, HOME_ADVANTAGE, K_BY_PHASE, update_elo
  ```
- **Evidencia Empírica:** Al ejecutar `python scripts/update_daily.py` en consola local:
  ```
  Traceback (most recent call last):
    File "C:\Users\Administrator\Projets\RepubliCaraquistApp\scripts\update_daily.py", line 7, in <module>
      from utils.elo import BASE_ELO, HOME_ADVANTAGE, K_BY_PHASE, update_elo
  ModuleNotFoundError: No module named 'utils'
  ```
- **Causa Raíz:** A diferencia de `scripts/backfill_elo.py` (línea 16) y `scripts/elo_sanity_check.py` (línea 5), `scripts/update_daily.py` no agrega el directorio raíz del repositorio a `sys.path`. En GitHub Actions se compensó mediante `PYTHONPATH: ${{ github.workspace }}` en `.github/workflows/update_data.yml:30`, pero rompe la ejecución en entornos locales o cron jobs independientes.

#### B. Fallback Legado Innecesario (`streamlit_app`)
- **Ubicación:** `pages/1_📊_Standings.py:42-59`, `pages/2_⚾_Estadisticas_Individuales.py:25-33`, `pages/3_📊_Estadisticas_Colectivas.py:28-33`, `pages/4_📈_Análisis_WPA.py:38-50`, `utils/elo.py:37-45`, `utils/wpa_engine.py:379`.
- **Código:**
  ```python
  try:
      from utils.supabase_client import get_standings...
  except:
      from streamlit_app.utils.supabase_client import get_standings...
  ```
- **Causa Raíz:** Remanente de una estructura previa donde el paquete se llamaba `streamlit_app`. El módulo `streamlit_app` no existe en el repositorio actual ni en `requirements.txt`. Las páginas 5 a 8 ya utilizan la importación canónica `from utils.xxx import yyy`.

#### C. Importaciones Duplicadas
- **Ubicación:** `🏠_Home.py:10` y `🏠_Home.py:94`
- **Código:**
  - Línea 10: `from utils.supabase_client import get_standings, get_recent_games, get_current_season, get_available_seasons, get_leones_advanced_stats, get_batting_stats, get_pitching_stats, get_weekly_records`
  - Línea 94: `from utils.supabase_client import get_standings, get_recent_games, get_current_season, get_available_seasons`

#### D. Importaciones Tardías (Late Imports)
- `utils/teams.py:130`: `import os` aparece en la línea 130 luego de 4 definiciones de funciones públicas.
- `utils/wpa_engine.py:377`: `from utils.supabase_client import init_supabase` dentro del cuerpo de la función `get_season_wpa_leaderboard()`.
- `🏠_Home.py:60, 69, 94`: Importaciones intermedias después de definir funciones y renderizar columnas.

#### E. Importaciones No Utilizadas (Dead Imports)
| Archivo | Línea | Importación No Utilizada |
|---|---|---|
| `🏠_Home.py` | L5, L6, L8 | `import numpy as np`, `import requests`, `import os` |
| `pages/3_📊_Estadisticas_Colectivas.py` | L4, L6, L19 | `import numpy as np`, `import plotly.graph_objects as go`, `get_team_name, get_team_abbr, get_team_color, LVBP_TEAMS` |
| `pages/4_📈_Análisis_WPA.py` | L8, L11, L20, L31 | `import numpy as np`, `from datetime import datetime`, `LVBP_ABBR, LVBP_COLORS, get_team_name, get_team_abbr, get_team_color, resolve_team_id`, `format_base_state` |
| `pages/5_🎯_Spray_Charts.py` | L4, L6, L7, L8 | `import numpy as np`, `import plotly.graph_objects as go`, `get_current_season`, `get_team_logo, get_team_name, get_team_abbr, LVBP_TEAMS` |
| `pages/6_🎯_Disciplina_y_Zonas.py` | L4, L6, L8 | `import numpy as np`, `import plotly.graph_objects as go`, `get_team_logo, get_team_name, get_team_abbr, LVBP_TEAMS` |
| `pages/7_⚡_Situacional_y_BvP.py` | L3, L4, L6, L8 | `import pandas as pd`, `import numpy as np`, `import plotly.graph_objects as go`, `get_team_name, get_team_abbr, LVBP_TEAMS` |
| `pages/8_🛡️_Bullpen_y_Lineups.py` | L4, L6, L8 | `import numpy as np`, `import plotly.graph_objects as go`, `get_team_name, get_team_abbr, LVBP_TEAMS` |
| `utils/bullpen_lineups.py` | L4 | `import numpy as np` |
| `utils/elo.py` | L11, L26 | `import numpy as np`, `LVBP_ABBR, LVBP_COLORS, get_team_logo, get_team_name, get_team_abbr, get_team_color, resolve_team_id` |
| `utils/spray_chart.py` | L6, L9 | `import plotly.express as px`, `from datetime import datetime` |
| `utils/strike_zone.py` | L6 | `import plotly.express as px` |
| `utils/wpa_engine.py` | L8, L12 | `import numpy as np`, `from typing import List` |

---

## 3. Auditoría de Dependencias (`requirements.txt`)

Contenido actual de `requirements.txt`:
```
streamlit
supabase
pandas
numpy
scipy
plotly
python-dotenv
requests
MLB-StatsAPI
openai
```

### Hallazgos:
1. **Falta de Fijación de Versiones (`unpinned`):** Ninguna de las 10 dependencias cuenta con operadores de versión (`==` o `>=`). Esto expone los despliegues en Streamlit Cloud y GitHub Actions a rupturas imprevistas por breaking changes en actualizaciones mayores de dependencias (ej. Streamlit 1.x vs 2.x, Pydantic/Supabase v2 vs v3, Numpy 2.x).
2. **Dependencia Sobrante (`scipy`):** `scipy` está listada en la línea 5 pero no es importada ni referenciada en ningún archivo `.py` de todo el proyecto.
3. **Módulo Desconectado / Dependencia OpenAI:** `openai` está listada en la línea 10 pero solo es utilizada por `utils/ai_insights.py`. Ninguna página de la aplicación web (`🏠_Home.py` ni `pages/*.py`) invoca `ai_insights.py`. Adicionalmente, según `GEMINI.md` §1, existe una migración en curso de OpenAI a Anthropic API.
4. **Dependencias Activas y Saludables:** `streamlit` (1.52.1), `supabase` (2.27.2), `pandas` (2.3.3), `numpy` (2.3.5), `plotly` (6.9.0), `python-dotenv` (1.2.1), `requests` (2.32.5), `MLB-StatsAPI` (1.9.0).

---

## 4. Estructura y Arquitectura

### 4.1. Puntos de Entrada
- `🏠_Home.py` (25 KB): Página principal de la aplicación Streamlit con dashboard general, standing resumido, últimos juegos, MVP sabermétrico y desglose semanal.
- `Home.py` (191 B): Script wrapper que redirige a `🏠_Home.py` vía `runpy.run_path`.
- `app.py` (287 B): Script wrapper que redirige a `🏠_Home.py` para compatibilidad con DevContainers y plataformas PaaS.

### 4.2. Función Temática Desaprovechada
- `apply_plotly_theme(fig)` en `utils/styles.py:352-378`: Función que estandariza los colores de fondo (`#0D152B`, `#070B19`), fuentes y leyendas para gráficos Plotly. Sin embargo, no es importada por ninguna página; cada página recrea configuraciones de layout manualmente.

### 4.3. Cláusulas `except:` Genéricas (Error Silencing)
Se detectaron 26 cláusulas `except:` desnudas (bare excepts) que silencian excepciones sin registrar el error:
- `scripts/update_daily.py:169, 198, 230`: `try: supabase.table(...).upsert(...).execute() except: pass` — si ocurre un fallo de base de datos o timeout, se ignora silenciosamente.
- `pages/2` a `pages/8`: `try: from utils.styles import inject_custom_css; inject_custom_css() except: pass`.

### 4.4. Ausencia de Suite de Pruebas Formal
A pesar de que `PROJECT.md` define un directorio `tests/`, la carpeta no existe en el árbol de archivos. El único archivo de verificación es `scripts/elo_sanity_check.py`.

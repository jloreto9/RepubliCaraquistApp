# Original User Request

## 2026-08-29T00:46:36Z

<USER_REQUEST>
Auditoría integral y diagnóstico exhaustivo de salud técnica, integridad de datos sabermétricos, estabilidad de páginas de Streamlit y calidad de arquitectura para la plataforma RepubliCaraquistApp.

Working directory: c:/Users/Administrator/Projets/RepubliCaraquistApp
Integrity mode: development

## Requirements

### R1. Diagnóstico de Arquitectura, Sintaxis e Importaciones
Verificar que la aplicación raíz (`🏠_Home.py`), todas las páginas secundarias (`pages/*.py`) y los módulos utilitarios (`utils/`, `scripts/`) compilen sin errores de sintaxis, no tengan imports rotos o dependencias no declaradas en `requirements.txt`.

### R2. Integridad de Métricas Sabermétricas y Flujo de Datos
Auditar la consistencia matemática y de dominio de las métricas avanzadas (wOBA, WPA, LI, FIP, LOB Tracker, fildeo individual/colectivo, splits día/noche y récords por semana). Verificar el manejo seguro de valores `NaN`, `Inf`, nulos y resiliencia ante errores de conexión con Supabase o MLB Stats API.

### R3. Evaluación de Rendimiento, Caché y UI/UX
Revisar la estrategia de almacenamiento en caché (`st.cache_data` con TTL apropiado), la separación entre capa de datos y capa de presentación, el contraste visual en gráficos Plotly (tema Dark Navy) y la claridad didáctica de los glosarios en español.

### R4. Reporte Estructurado de Diagnóstico (Solo Lectura)
Compilar un informe de auditoría detallado y clasificado por severidad (Crítico, Advertencia, Oportunidad de Optimización) con evidencia comprobable (fragmentos de código, stack traces o resultados de tests), causa raíz identificada y recomendaciones accionables, manteniendo el código intacto sin mutaciones directas.

## Verification Resources
- Suite de pruebas y scripts de validación existentes en el repositorio (`tests/`, `scripts/update_daily.py`, etc.).
- Análisis estático de código y verificación de compilación en entorno Python.

## Acceptance Criteria

### Estabilidad y Sintaxis
- [ ] Todas las páginas de la aplicación (`🏠_Home.py` y subpáginas `pages/1_...` a `pages/8_...`) y módulos en `utils/` son verificados contra errores de sintaxis, dependencias faltantes e imports circulares.
- [ ] Las pruebas unitarias existentes son ejecutadas y sus resultados (éxitos/fallos) quedan documentados objetivamente.

### Integridad de Datos y Seguridad
- [ ] Se verifica que las consultas a Supabase sean de solo lectura y que las credenciales provengan estrictamente de variables de entorno (`.env` / Streamlit secrets).
- [ ] Se validan las fórmulas sabermétricas clave y el control de excepciones ante datos incompletos.

### Calidad del Entregable
- [ ] Se genera un reporte final exhaustivo en Markdown con hallazgos concretos sustentados en código y logs, organizado por severidad y módulo.
- [ ] No se realizan modificaciones ni escrituras destructivas sobre el código fuente de RepubliCaraquistApp durante este chequeo.
</USER_REQUEST>

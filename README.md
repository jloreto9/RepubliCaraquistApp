# 🦁 RepubliCaraquistApp

**RepubliCaraquistApp** es una aplicación web de análisis avanzado de la LVBP (Liga Venezolana de Béisbol Profesional), enfocada en los **Leones del Caracas**, desarrollada con Python, Streamlit y Supabase.  
Integra estadísticas tradicionales y sabermétricas, automatización diaria y un módulo de inteligencia artificial para análisis contextual.

---

## 🚀 Características principales

### ⚾ 1. Standings y Resultados
- Calendario completo de la temporada.
- Resultados por fase: temporada regular, round robin y final.
- Diferencial de carreras (RF/RA), racha, récord home/away.

### 📊 2. Estadísticas Individuales
- Bateo: AVG, OBP, SLG, OPS, OPS+, WAR estimado.
- Pitcheo: ERA, WHIP, FIP, ERA+, FIP+, K/BB, HR/9.
- Comparativas por fase o rival.

### 🧩 3. Estadísticas Colectivas
- Promedios de liga y comparativas entre equipos.
- Métricas ajustadas (OPS+, ERA+) respecto al promedio de la LVBP.
- Gráficos de rendimiento acumulado.

### 🧠 4. Analista AI (OpenAI API)
Un asistente inteligente que responde con análisis naturales:
- Resumen del desempeño del equipo en la semana o el mes.
- Identificación del mejor y peor jugador del período.
- Proyección de clasificación usando **ELO Rating System + Monte Carlo Simulation**.
- Diferenciación por fase: Regular / RR / Final.

---

```## 🧱 Arquitectura General

n8n (Job diario 2am)
↓
Python Scraper → Supabase (DB + Storage)
↓
Streamlit App → (Usuarios / Dashboard / AI Analysis)
↓
OpenAI API (insights generados)


### 🔹 Componentes

| Componente | Descripción |
|-------------|-------------|
| **Supabase** | Base de datos PostgreSQL con vistas materializadas (batting, pitching, standings). |
| **n8n (VPS Hostinger)** | Orquestador que ejecuta el job de ingesta diaria de datos (StatsAPI). |
| **Streamlit** | Interfaz principal con módulos separados: standings, estadísticas, analista AI. |
| **OpenAI API** | Motor de generación de análisis y narrativas deportivas. |

---

## 🧩 Estructura del Proyecto

``` republicaraquistapp/
│
├── streamlit_app/
│ ├── pages/
│ │ ├── 1_Standings_y_Resultados.py
│ │ ├── 2_Estadisticas_Individuales.py
│ │ ├── 3_Estadisticas_Colectivas.py
│ │ └── 4_Analista_AI.py
│ ├── assets/
│ │ └── logos/ (logos de equipos LVBP)
│ ├── utils/
│ │ ├── supabase_client.py
│ │ ├── elo_montecarlo.py
│ │ └── ai_analyzer.py
│ └── app.py
│
├── supabase/
│ ├── 001_init.sql
│ ├── 002_views.sql
│ ├── 003_seed.sql
│ ├── 004_rls.sql
│ └── 006_refresh.sql
│
├── n8n/
│ └── job_ingesta_lvbp.json
│
├── requirements.txt
└── README.md

---

## ⚙️ Instalación y Ejecución

### 1️⃣ Clonar el repositorio
```bash
git clone https://github.com/tuusuario/RepubliCaraquistApp.git
cd RepubliCaraquistApp

### 2️⃣ Crear entorno e instalar dependencias
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

### 3️⃣ Configurar variables de entorno

SUPABASE_URL="https://xxxxx.supabase.co"
SUPABASE_KEY="public-anon-key"
OPENAI_API_KEY="sk-xxxxx"

### 4️⃣ Ejecutar la app

streamlit run streamlit_app/app.py

📦 Dependencias principales

- streamlit
- supabase-py
- pandas
- numpy
- plotly
- openai
- python-dotenv

🧮 Futuras mejoras

Módulo de WAR estimado y predicciones por posición.
Integración de visualizaciones dinámicas con Plotly Express.
Exportación automática de reportes PDF por semana.

📣 Autor

Jorge Leonardo Loreto
📊 Científico de Datos | ⚾ Analista de Béisbol | 🦁 Fanático de los Leones del Caracas
Twitter: @RepubCaraquista

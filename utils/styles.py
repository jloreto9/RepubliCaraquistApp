# utils/styles.py
"""
Sistema de Diseño y Estilos CSS Personalizados para República Caraquista.
Provee una estética Dark Athletic / Sabermétrica moderna inspirada en los Leones del Caracas.
"""
import streamlit as st

def inject_custom_css():
    """Inyecta los estilos CSS globales en la aplicación de Streamlit."""
    st.markdown("""
    <style>
    /* ==========================================================================
       VARIABLES Y FUENTES GLOBALES
       ========================================================================== */
    :root {
        --caraquista-gold: #FDB827;
        --caraquista-gold-hover: #FFC72C;
        --caraquista-gold-glow: rgba(253, 184, 39, 0.25);
        --caraquista-navy: #070B19;
        --caraquista-card: #0D152B;
        --caraquista-surface: #121D3A;
        --caraquista-border: rgba(255, 255, 255, 0.08);
        --caraquista-border-gold: rgba(253, 184, 39, 0.22);
        --text-primary: #FFFFFF;
        --text-secondary: #94A3B8;
    }

    /* Ocultar barra superior redundante y footer por defecto */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {background-color: transparent !important;}

    /* ==========================================================================
       SIDEBAR MODERNA & NAVEGACIÓN
       ========================================================================== */
    [data-testid="stSidebar"] {
        background-color: #070B19 !important;
        border-right: 1px solid var(--caraquista-border) !important;
    }

    [data-testid="stSidebarNav"] {
        padding-top: 1rem;
    }

    [data-testid="stSidebarNav"] a {
        border-radius: 8px !important;
        margin: 2px 8px !important;
        padding: 0.5rem 0.75rem !important;
        transition: all 0.2s ease-in-out !important;
    }

    [data-testid="stSidebarNav"] a:hover {
        background-color: rgba(253, 184, 39, 0.1) !important;
        color: var(--caraquista-gold) !important;
    }

    [data-testid="stSidebarNav"] a[aria-selected="true"] {
        background-color: rgba(253, 184, 39, 0.15) !important;
        border-left: 3px solid var(--caraquista-gold) !important;
        font-weight: 700 !important;
    }

    /* Renombrar slug principal a "🏠 Home" si aplica */
    [data-testid="stSidebarNav"] a[href="/"] span,
    [data-testid="stSidebarNav"] a[href=""] span {
        font-weight: 600;
    }

    /* ==========================================================================
       TARJETAS DE MÉTRICAS (st.metric) - GLASSMORHPISM PREMIUM
       ========================================================================== */
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, rgba(13, 21, 43, 0.85), rgba(7, 11, 25, 0.95)) !important;
        border: 1px solid var(--caraquista-border-gold) !important;
        border-radius: 14px !important;
        padding: 1.1rem 1.25rem !important;
        box-shadow: 0 8px 24px -6px rgba(0, 0, 0, 0.5) !important;
        backdrop-filter: blur(12px) !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    [data-testid="stMetric"]:hover {
        transform: translateY(-3px) !important;
        border-color: rgba(253, 184, 39, 0.45) !important;
        box-shadow: 0 14px 28px -6px rgba(0, 0, 0, 0.7), 0 0 15px rgba(253, 184, 39, 0.15) !important;
    }

    [data-testid="stMetricLabel"] {
        color: var(--text-secondary) !important;
        font-size: 0.8rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
    }

    [data-testid="stMetricValue"] {
        color: #FFFFFF !important;
        font-weight: 900 !important;
        font-size: 1.85rem !important;
        letter-spacing: -0.02em !important;
    }

    /* ==========================================================================
       CONTENEDORES CON BORDE (st.container(border=True))
       ========================================================================== */
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        background-color: rgba(13, 21, 43, 0.6) !important;
        border: 1px solid var(--caraquista-border) !important;
        border-radius: 16px !important;
        padding: 1.25rem !important;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4) !important;
        backdrop-filter: blur(8px) !important;
    }

    /* ==========================================================================
       PESTAÑAS / TABS (st.tabs)
       ========================================================================== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px !important;
        background-color: transparent !important;
        border-bottom: 1px solid var(--caraquista-border) !important;
        padding-bottom: 4px !important;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0 !important;
        color: var(--text-secondary) !important;
        font-weight: 600 !important;
        font-size: 0.92rem !important;
        padding: 0.6rem 1.2rem !important;
        transition: all 0.2s ease !important;
        background-color: transparent !important;
        border: none !important;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: #FFFFFF !important;
        background-color: rgba(255, 255, 255, 0.04) !important;
    }

    .stTabs [aria-selected="true"] {
        color: var(--caraquista-gold) !important;
        font-weight: 800 !important;
        border-bottom: 3px solid var(--caraquista-gold) !important;
        background-color: rgba(253, 184, 39, 0.08) !important;
    }

    /* ==========================================================================
       BOTONES MODERNOS (st.button)
       ========================================================================== */
    .stButton > button {
        border-radius: 10px !important;
        font-weight: 700 !important;
        padding: 0.5rem 1.25rem !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        border: 1px solid var(--caraquista-border) !important;
    }

    .stButton > button:hover {
        transform: translateY(-1px) !important;
        border-color: var(--caraquista-gold) !important;
        box-shadow: 0 4px 14px rgba(253, 184, 39, 0.2) !important;
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #FDB827, #E5A315) !important;
        color: #070B19 !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(253, 184, 39, 0.3) !important;
    }

    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #FFC72C, #FDB827) !important;
        box-shadow: 0 6px 20px rgba(253, 184, 39, 0.45) !important;
    }

    /* ==========================================================================
       DATAFRAMES Y TABLAS
       ========================================================================== */
    [data-testid="stDataFrame"] {
        border: 1px solid var(--caraquista-border) !important;
        border-radius: 12px !important;
        overflow: hidden !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3) !important;
    }

    /* ==========================================================================
       EXPANDERS (st.expander)
       ========================================================================== */
    [data-testid="stExpander"] {
        background-color: rgba(13, 21, 43, 0.5) !important;
        border: 1px solid var(--caraquista-border) !important;
        border-radius: 12px !important;
        margin-bottom: 0.75rem !important;
        overflow: hidden !important;
    }

    [data-testid="stExpander"] summary {
        font-weight: 700 !important;
        color: #FFFFFF !important;
        padding: 0.75rem 1rem !important;
    }

    [data-testid="stExpander"] summary:hover {
        color: var(--caraquista-gold) !important;
    }

    /* ==========================================================================
       CONTROLES DE FORMULARIO (Selectbox, Radio, Multiselect, Inputs)
       ========================================================================== */
    div[data-baseweb="select"] > div {
        background-color: #0D152B !important;
        border: 1px solid var(--caraquista-border) !important;
        border-radius: 8px !important;
    }

    div[data-baseweb="select"] > div:focus-within {
        border-color: var(--caraquista-gold) !important;
        box-shadow: 0 0 0 1px var(--caraquista-gold) !important;
    }

    /* ==========================================================================
       CLASES DE UTILIDAD
       ========================================================================== */
    .gold-text { color: var(--caraquista-gold) !important; }
    .muted-text { color: var(--text-secondary) !important; }
    
    .badge-gold {
        background: rgba(253, 184, 39, 0.15);
        color: #FDB827;
        border: 1px solid rgba(253, 184, 39, 0.3);
        border-radius: 6px;
        padding: 2px 8px;
        font-size: 0.75rem;
        font-weight: 700;
        display: inline-block;
    }

    .badge-green {
        background: rgba(34, 197, 94, 0.15);
        color: #22C55E;
        border: 1px solid rgba(34, 197, 94, 0.3);
        border-radius: 6px;
        padding: 2px 8px;
        font-size: 0.75rem;
        font-weight: 700;
        display: inline-block;
    }

    .badge-red {
        background: rgba(239, 68, 68, 0.15);
        color: #EF4444;
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-radius: 6px;
        padding: 2px 8px;
        font-size: 0.75rem;
        font-weight: 700;
        display: inline-block;
    }

    .card-glass {
        background: linear-gradient(145deg, rgba(13, 21, 43, 0.85), rgba(7, 11, 25, 0.95));
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
    }

    .metric-card {
        background: linear-gradient(145deg, rgba(13, 21, 43, 0.85), rgba(7, 11, 25, 0.95)) !important;
        border: 1px solid var(--caraquista-border-gold) !important;
        border-left: 4px solid var(--caraquista-gold) !important;
        border-radius: 12px !important;
        padding: 1rem 1.25rem !important;
        box-shadow: 0 8px 20px -4px rgba(0, 0, 0, 0.5) !important;
        margin-bottom: 10px !important;
        backdrop-filter: blur(10px) !important;
        transition: all 0.2s ease !important;
    }

    .metric-card:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 12px 25px -4px rgba(0, 0, 0, 0.7), 0 0 12px rgba(253, 184, 39, 0.2) !important;
    }

    .metric-title {
        color: var(--text-secondary) !important;
        font-size: 0.78rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }

    .metric-value {
        color: #FFFFFF !important;
        font-size: 1.75rem !important;
        font-weight: 900 !important;
        letter-spacing: -0.02em !important;
    }

    .metric-sub {
        color: #22C55E !important;
        font-size: 0.78rem !important;
        font-weight: 600 !important;
    }

    .main-header {
        font-size: 2.75rem !important;
        color: var(--caraquista-gold) !important;
        text-align: center !important;
        font-weight: 900 !important;
        text-shadow: 2px 2px 6px rgba(0, 0, 0, 0.5) !important;
        letter-spacing: -0.02em !important;
    }

    .sub-header {
        font-size: 1.1rem !important;
        color: var(--text-secondary) !important;
        text-align: center !important;
        margin-bottom: 1.75rem !important;
    }

    .atbat-banner {
        background: linear-gradient(135deg, rgba(13, 21, 43, 0.9) 0%, rgba(7, 11, 25, 0.95) 100%) !important;
        border: 1px solid var(--caraquista-border-gold) !important;
        border-left: 5px solid var(--caraquista-gold) !important;
        border-radius: 12px !important;
        padding: 14px 20px !important;
        margin-bottom: 16px !important;
        color: #F8FAFC !important;
        box-shadow: 0 8px 20px -4px rgba(0, 0, 0, 0.5) !important;
    }

    /* Scrollbars elegantes */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #070B19;
    }
    ::-webkit-scrollbar-thumb {
        background: #1E293B;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: var(--caraquista-gold);
    }
    </style>
    """, unsafe_allow_html=True)

def apply_plotly_theme(fig):
    """Aplica la plantilla visual de República Caraquista a cualquier figura de Plotly."""
    fig.update_layout(
        paper_bgcolor="#0D152B",
        plot_bgcolor="#070B19",
        font=dict(color="#FFFFFF", family="sans-serif"),
        title_font=dict(color="#FDB827", size=16),
        legend=dict(
            bgcolor="rgba(13, 21, 43, 0.8)",
            bordercolor="rgba(255, 255, 255, 0.1)",
            borderwidth=1,
            font=dict(color="#FFFFFF")
        ),
        xaxis=dict(
            gridcolor="rgba(255, 255, 255, 0.07)",
            linecolor="rgba(255, 255, 255, 0.15)",
            tickfont=dict(color="#94A3B8")
        ),
        yaxis=dict(
            gridcolor="rgba(255, 255, 255, 0.07)",
            linecolor="rgba(255, 255, 255, 0.15)",
            tickfont=dict(color="#94A3B8")
        ),
        margin=dict(l=40, r=40, t=50, b=40)
    )
    return fig

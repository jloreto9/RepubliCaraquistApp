import streamlit as st

st.set_page_config(
    page_title="RepubliCaraquistApp",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS para ocultar "app" del sidebar
st.markdown("""
    <style>
    /* Ocultar el item "app" del menú */
    [data-testid="stSidebarNav"] > ul > li:first-child {
        display: none !important;
    }
    </style>
""", unsafe_allow_html=True)

# Redirección automática a Home
import time
st.write("Cargando...")
time.sleep(0.1)
st.switch_page("pages/1_🏠_Home.py")

# app.py (simplificado)
import streamlit as st

st.set_page_config(
    page_title="RepubliCaraquistApp",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
    <h1 style='text-align: center; color: #FDB827;'>
        🦁 RepubliCaraquistApp
    </h1>
    <p style='text-align: center;'>
        Por favor, selecciona una página del menú lateral
    </p>
""", unsafe_allow_html=True)

st.info("👈 Selecciona una opción del menú lateral")

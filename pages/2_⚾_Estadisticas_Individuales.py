# pages/2_⚾_Estadisticas_Individuales.py
import streamlit as st

st.set_page_config(page_title="Estadísticas Individuales - RepubliCaraquistApp", page_icon="⚾", layout="wide")

# Header
st.title("⚾ Estadísticas Individuales")
st.markdown("### Líderes de Bateo y Pitcheo - Leones del Caracas")

# Mensaje de en desarrollo
st.info("📊 **Sección en desarrollo**")
st.markdown("""
Esta sección mostrará próximamente:
- 🏏 **Líderes de Bateo**: AVG, HR, RBI, OBP, SLG, OPS
- ⚾ **Líderes de Pitcheo**: ERA, WHIP, K, Saves
- 📈 **Gráficos interactivos** de rendimiento
- 🔍 **Búsqueda de jugadores** específicos
- 📅 **Estadísticas por temporada**
""")

st.markdown("---")

# Placeholder con datos de ejemplo
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🏏 Top Bateadores (Próximamente)")
    st.dataframe({
        'Jugador': ['Jugador 1', 'Jugador 2', 'Jugador 3'],
        'AVG': ['.000', '.000', '.000'],
        'HR': [0, 0, 0],
        'RBI': [0, 0, 0]
    })

with col2:
    st.markdown("### ⚾ Top Lanzadores (Próximamente)")
    st.dataframe({
        'Jugador': ['Lanzador 1', 'Lanzador 2', 'Lanzador 3'],
        'ERA': ['0.00', '0.00', '0.00'],
        'K': [0, 0, 0],
        'WHIP': ['0.00', '0.00', '0.00']
    })

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 2rem;'>
    <p>⚠️ Los datos de estadísticas individuales se están procesando</p>
    <p>Disponible próximamente con actualización diaria</p>
</div>
""", unsafe_allow_html=True)

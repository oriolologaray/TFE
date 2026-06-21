"""Punto de entrada de la aplicación. Ejecutar con: streamlit run app/app.py"""

import streamlit as st

dashboard = st.Page(
    "pages/Dashboard_de_partido.py",
    title="Dashboard de partido",
    icon="⚽",
)
simulador = st.Page(
    "pages/Simulador.py",
    title="Simulador",
    icon="🎲",
)

pg = st.navigation([dashboard, simulador])
pg.run()

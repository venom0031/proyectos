import streamlit as st
import pandas as pd
import sys
import os

# Agregar módulos al path
sys.path.insert(0, os.path.dirname(__file__))

from etl import load_week_from_db, load_historic_from_db
from matrix_builder import build_matrix
from format_utils import format_dataframe_for_display

def show_admin_matrix():
    st.subheader("🔎 Visualización Global de Matriz Semanal")
    with st.spinner("Cargando datos globales de la base de datos..."):
        try:
            df_long = load_week_from_db(user_id=None, is_admin=True)
            df_hist = load_historic_from_db(user_id=None, is_admin=True)
            if df_long.empty:
                st.warning("No hay datos semanales cargados en la base de datos.")
                return
            semana_actual = int(df_long["N° Semana"].dropna().max()) if "N° Semana" in df_long.columns else None
            st.info(f"Semana más reciente en la base: {semana_actual}")
            df_matrix = build_matrix(df_long, df_hist=df_hist, current_week=semana_actual)
            df_display, col_config = format_dataframe_for_display(df_matrix)
            st.dataframe(df_display, use_container_width=True, height=500)
        except Exception as e:
            st.error(f"Error al cargar matriz global: {e}")
            st.exception(e)

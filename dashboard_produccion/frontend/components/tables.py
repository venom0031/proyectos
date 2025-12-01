"""
Componentes de tablas para visualización de datos
"""
import streamlit as st
import pandas as pd


def get_name(val):
    """Extrae el nombre de un valor que puede ser dict o False"""
    if isinstance(val, dict):
        return val.get("name", "N/A")
    return "N/A"


def render_componentes_table(componentes: list):
    """
    Renderiza la tabla de componentes (materia prima)
    
    Args:
        componentes: Lista de componentes de la OF
    """
    if not componentes:
        st.info("No hay componentes registrados")
        return
    
    df_comp = pd.DataFrame([{
        "Producto": get_name(c.get("product_id")),
        "Lote": get_name(c.get("lot_id")),
        "Cantidad (kg)": c.get("qty_done", 0) or 0,
        "Ubicación Origen": get_name(c.get("location_id")),
        "Ubicación Destino": get_name(c.get("location_dest_id")),
        "Pallet Origen": get_name(c.get("package_id")),
        "Pallet Destino": get_name(c.get("result_package_id")),
        "Categoría": c.get("product_category_name", "N/A")
    } for c in componentes])
    
    st.dataframe(df_comp, use_container_width=True, height=400)


def render_subproductos_table(subproductos: list):
    """
    Renderiza la tabla de subproductos
    
    Args:
        subproductos: Lista de subproductos de la OF
    """
    if not subproductos:
        st.info("No hay subproductos registrados")
        return
    
    df_sub = pd.DataFrame([{
        "Producto": get_name(s.get("product_id")),
        "Lote": get_name(s.get("lot_id")),
        "Cantidad (kg)": s.get("qty_done", 0) or 0,
        "Ubicación Origen": get_name(s.get("location_id")),
        "Ubicación Destino": get_name(s.get("location_dest_id")),
        "Pallet Origen": get_name(s.get("package_id")),
        "Pallet Destino": get_name(s.get("result_package_id")),
        "Categoría": s.get("product_category_name", "N/A")
    } for s in subproductos])
    
    st.dataframe(df_sub, use_container_width=True, height=400)


def render_detenciones_table(detenciones: list):
    """
    Renderiza la tabla de detenciones
    
    Args:
        detenciones: Lista de detenciones de la OF
    """
    if not detenciones:
        st.info("No hay detenciones registradas")
        return
    
    df_det = pd.DataFrame([{
        "Responsable": get_name(d.get("x_studio_responsable")),
        "Motivo": get_name(d.get("x_motivodetencion")),
        "Hora Inicio": d.get("x_horainiciodetencion", "N/A"),
        "Hora Fin": d.get("x_horafindetencion", "N/A"),
        "Horas Detención": d.get("x_studio_horas_de_detencin", 0) or 0
    } for d in detenciones])
    
    st.dataframe(df_det, use_container_width=True, height=400)


def render_consumo_table(consumo: list):
    """
    Renderiza la tabla de horas de consumo
    
    Args:
        consumo: Lista de horas de consumo de la OF
    """
    if not consumo:
        st.info("No hay horas de consumo registradas")
        return
    
    # Separar por tipo
    comp_consumo = [c for c in consumo if c.get("type") == "Componente"]
    sub_consumo = [c for c in consumo if c.get("type") == "Subproducto"]
    
    if comp_consumo:
        st.markdown("**Componentes (MP)**")
        df_comp_consumo = pd.DataFrame([{
            "Pallet": c.get("x_name", "N/A"),
            "Producto": c.get("x_studio_many2one_field_sPOmE", "N/A"),
            "Lote": c.get("x_studio_nmero_de_lote", "N/A"),
            "Hora Inicio": c.get("x_studio_hora_inicio", "N/A"),
            "Hora Fin": c.get("x_studio_hora_fin", "N/A")
        } for c in comp_consumo])
        st.dataframe(df_comp_consumo, use_container_width=True, height=300)
    
    if sub_consumo:
        st.markdown("**Subproductos**")
        df_sub_consumo = pd.DataFrame([{
            "Pallet": c.get("x_name", "N/A"),
            "Producto": c.get("x_studio_many2one_field_sPOmE", "N/A"),
            "Lote": c.get("x_studio_nmero_de_lote", "N/A"),
            "Hora Inicio": c.get("x_studio_hora_inicio", "N/A"),
            "Hora Fin": c.get("x_studio_hora_fin", "N/A")
        } for c in sub_consumo])
        st.dataframe(df_sub_consumo, use_container_width=True, height=300)

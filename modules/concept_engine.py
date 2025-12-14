# concept_engine.py

import pandas as pd
import numpy as np
import unicodedata
import re

# ==========================================
# Mapeo de conceptos Excel → clave interna
# Los conceptos vienen limpios (sin prefijo "(A) ", "(B) ", etc.)
# gracias a _clean_concept en etl.py
# ==========================================

CONCEPT_MAP = {
    # Vacas - con y sin tilde, y variantes encoding
    "Vacas en ordeña": "vacas_ordena",
    "Vacas en ordena": "vacas_ordena",
    "Vacas masa": "vacas_masa",
    "Superficie Praderas": "superficie_praderas",

    # Producción y precio - con y sin tilde
    "Producción promedio": "produccion_prom",
    "Produccion promedio": "produccion_prom",
    "Precio de la leche": "precio_leche",
    "Producción total": "produccion_total",
    "Produccion total": "produccion_total",

    # MS
    "Kg MS Pradera / vaca": "ms_pradera",
    "Kg MS Verde / vaca": "ms_verde",
    "Kg MS Conservado / vaca": "ms_conservado",
    "Kg MS Concentrado / vaca": "ms_concentrado",
    "Praderas y otros verdes": "praderas_otros_verdes",
    "Total MS": "total_ms",
    "Consumo de mat. seca": "consumo_ms",
    "Mat. Seca por Ha": "ms_por_ha",

    # Costos - con y sin tilde
    "Costo ración vaca": "costo_racion_vaca",
    "Costo racion vaca": "costo_racion_vaca",
    "Costo promedio concentrado": "costo_concentrado",
    "Grms concentrado / ltr leche": "gramos_por_litro",

    # Calidad
    "Porcentaje de grasa": "porc_grasa",
    "Proteinas": "proteinas",
    
    # MDAT
    "MDAT": "mdat",
    
    # Otros indicadores
    "Días de lactancia promedio": "dias_lactancia",
    "Dias de lactancia promedio": "dias_lactancia",
    "Porcentaje leche no vendible": "porc_leche_no_vendible",
    "Relación vaca ordeña / vaca masa": "relacion_ordena_masa",
    "Relacion vaca ordena / vaca masa": "relacion_ordena_masa",
    "Relación vaca ordeña / vaca masa ": "relacion_ordena_masa",  # con espacio final
}


def _normalize_text(txt: str) -> str:
    """
    Normaliza texto quitando acentos y caracteres especiales
    para hacer matching más robusto.
    """
    if not txt:
        return ""
    # Normalizar unicode (NFD = descomponer caracteres con acentos)
    txt = unicodedata.normalize('NFD', txt)
    # Quitar caracteres de combinación (acentos)
    txt = ''.join(c for c in txt if unicodedata.category(c) != 'Mn')
    # Reemplazar caracteres problemáticos de encoding
    txt = txt.replace('�', '')
    txt = txt.replace('?', '')
    return txt


# ==========================================
# Normalizador de conceptos
# ==========================================

def attach_normalized_concepts(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adjunta la columna Concepto_Norm mapeando CONCEPTO → clave interna.
    Usa matching normalizado (sin acentos) para mayor robustez.
    """
    df = df.copy()
    
    # Crear versión normalizada del CONCEPT_MAP
    concept_map_norm = {}
    for k, v in CONCEPT_MAP.items():
        key_norm = _normalize_text(k.lower())
        concept_map_norm[key_norm] = v
    
    def map_concept(concepto):
        if pd.isna(concepto):
            return None
        # Intentar mapeo directo primero
        if concepto in CONCEPT_MAP:
            return CONCEPT_MAP[concepto]
        # Si no, normalizar y buscar
        concepto_norm = _normalize_text(str(concepto).lower())
        return concept_map_norm.get(concepto_norm)
    
    df["Concepto_Norm"] = df["CONCEPTO"].apply(map_concept)
    return df


# ==========================================
# Motor de cálculo: usa SOLO A. TOTAL
# ==========================================

def compute_metric(df: pd.DataFrame, est: str, concept_key: str) -> float:
    """
    Devuelve el valor semanal para un concepto/establecimiento,
    usando únicamente la columna 'A. TOTAL'.
    """
    sub = df[
        (df["Establecimiento"] == est)
        & (df["Concepto_Norm"] == concept_key)
    ]

    if sub.empty:
        # Intentar consultar datos diarios si el DataFrame tiene la función disponible
        try:
            from etl import load_daily_from_db
            # Se asume que user_id y is_admin están disponibles en session_state
            import streamlit as st
            user_id = getattr(st.session_state, "user_id", None)
            is_admin = getattr(st.session_state, "is_admin", False)
            df_daily = load_daily_from_db(user_id=user_id, is_admin=is_admin, establecimiento=est)
            # Normalizar conceptos en el diario
            if not df_daily.empty:
                df_daily = attach_normalized_concepts(df_daily)
                sub_daily = df_daily[df_daily["Concepto_Norm"] == concept_key]
                # Buscar columnas de fechas
                date_pattern = re.compile(r'^\d{1,2}-\d{1,2}-\d{4}$')
                date_cols = [col for col in sub_daily.columns if date_pattern.match(str(col))]
                if date_cols:
                    vals = pd.to_numeric(sub_daily[date_cols].values.flatten(), errors="coerce")
                    vals = pd.Series(vals).dropna()
                    if len(vals) > 0:
                        return vals.mean()
        except Exception:
            pass
        return np.nan

    # Definir conceptos que deben promediarse por día (no sumarse)
    avg_concepts = {
        "produccion_promedio",
        "precio_leche",
        "porcentaje_costo_alimentos",
        "costo_racion_vaca",
        "gramos_por_litro",
        "ms_concentrado",
        "ms_conservado",
        "ms_pradera",
        "ms_verde",
        "praderas_otros_verdes",
        "total_ms",
        "porc_grasa",
        "proteinas",
    }

    # Si existe 'A. TOTAL' y tiene valores, usarlo. Si está vacío pero hay columnas de fecha, devolver promedio de días con datos (para cualquier concepto)
    if "A. TOTAL" in sub.columns:
        a_total_vals = pd.to_numeric(sub["A. TOTAL"], errors="coerce").dropna()
        if len(a_total_vals) > 0:
            return float(a_total_vals.mean())
        else:
            # Si 'A. TOTAL' está vacío, pero hay columnas de fecha, promediar los días con datos
            date_pattern = re.compile(r'^\d{1,2}-\d{1,2}-\d{4}$')
            date_cols = [col for col in sub.columns if date_pattern.match(str(col))]
            if date_cols:
                vals = pd.to_numeric(sub[date_cols].values.flatten(), errors="coerce")
                vals = pd.Series(vals).dropna()
                if len(vals) > 0:
                    return float(vals.mean())

    # Si no hay 'A. TOTAL', calcular promedio de los días con datos
    date_pattern = re.compile(r'^\d{1,2}-\d{1,2}-\d{4}$')
    date_cols = [col for col in sub.columns if date_pattern.match(str(col))]
    if date_cols:
        vals = pd.to_numeric(sub[date_cols].values.flatten(), errors="coerce")
        vals = pd.Series(vals).dropna()
        if len(vals) > 0:
            return vals.mean()

    # Depuración removida (no mostrar expanders en producción)
    return np.nan

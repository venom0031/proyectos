# concept_engine.py

import pandas as pd
import numpy as np

# ==========================================
# Mapeo de conceptos Excel → clave interna
# ==========================================

CONCEPT_MAP = {
    # Vacas
    "Vacas en ordeña": "vacas_ordena",
    "Vacas masa": "vacas_masa",
    "Superficie Praderas": "superficie_praderas",

    # Producción y precio
    "Producción promedio": "produccion_prom",
    "Produccion promedio": "produccion_prom",  # por si viene sin tilde
    "Precio de la leche": "precio_leche",

    # MS
    "Kg MS Pradera / vaca": "ms_pradera",
    "Kg MS Verde / vaca": "ms_verde",
    "Kg MS Conservado / vaca": "ms_conservado",
    "Kg MS Concentrado / vaca": "ms_concentrado",

    # Costos
    "Costo ración vaca": "costo_racion_vaca",
    "Costo promedio concentrado": "costo_concentrado",
    "Grms concentrado / ltr leche": "gramos_por_litro",

    # Calidad
    "Porcentaje de grasa": "porc_grasa",
    "Proteinas": "proteinas",
}


# ==========================================
# Normalizador de conceptos
# ==========================================

def attach_normalized_concepts(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Concepto_Norm"] = df["CONCEPTO"].map(CONCEPT_MAP)
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
        return np.nan

    return sub["A. TOTAL"].astype(float).mean()

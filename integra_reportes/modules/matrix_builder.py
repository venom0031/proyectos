# matrix_builder.py

import pandas as pd
import numpy as np

from concept_engine import (
    compute_metric,
    attach_normalized_concepts,
    CONCEPT_MAP,
)

# Orden de columnas igual al Power BI
MATRIX_COLUMNS = [
    "Establecimiento",
    "Superficie Praderas", "Vacas masa", "Vacas en ordeña",
    "Carga animal",
    "Porcentaje de grasa", "Proteinas",
    "Costo promedio concentrado",
    "Grms concentrado / ltr leche",
    "Kg MS Concentrado / vaca", "Kg MS Conservado / vaca", "Praderas y otros verdes", "Total MS",
    "Producción promedio",
    "Costo ración vaca",
    "Precio de la leche",
    "MDAT (L/vaca/día)",
    "Porcentaje costo alimentos",
    "MDAT",
    "Ranking MDAT",
    "MDAT 4 sem", "Vacas 4 sem", "Ranking 4 sem",
    "MDAT 52 sem", "Vacas 52 sem", "Ranking 52 sem",
]


def _safe_val(row: dict, col: str) -> float:
    v = row.get(col)
    return 0.0 if v is None or pd.isna(v) else float(v)


def _sinteticos(row: dict):
    """Praderas y otros verdes / Total MS por establecimiento."""
    pr = _safe_val(row, "Kg MS Pradera / vaca")
    ve = _safe_val(row, "Kg MS Verde / vaca")
    co = _safe_val(row, "Kg MS Conservado / vaca")
    cn = _safe_val(row, "Kg MS Concentrado / vaca")

    return pr + ve, pr + ve + co + cn


def _derivados(row: dict):
    """MDAT, MDAT (L/vaca/día), Costo ración (L/vaca/día) por establecimiento."""
    prod = row.get("Producción promedio")
    precio = row.get("Precio de la leche")
    costo = row.get("Costo ración vaca")
    vacas_masa = row.get("Vacas masa")
    sup = row.get("Superficie Praderas")

    # Carga animal
    if sup and sup > 0 and vacas_masa is not None:
        carga = vacas_masa / sup
    else:
        carga = np.nan

    # % Costo alimentos = Costo / (Precio * Prod)
    # Ingreso = Precio * Prod
    if prod and precio and costo:
        ingreso = precio * prod
        pct_costo = (costo / ingreso) if ingreso > 0 else np.nan
    else:
        pct_costo = np.nan

    if any(pd.isna(x) for x in [prod, precio, costo]):
        return np.nan, np.nan, np.nan, np.nan

    mdat = precio * prod - costo
    mdat_l = mdat / precio if precio not in (0, None, np.nan) else np.nan
    
    # Costo ración (L/vaca/día) ya no se usa en la visual nueva, pero lo dejamos calculado si se quiere
    # costo_l = costo / precio if precio not in (0, None, np.nan) else np.nan
    
    return mdat, mdat_l, carga, pct_costo


def _get_historic_metrics(
    est: str,
    current_week: int | None,
    df_hist: pd.DataFrame | None
) -> tuple[float, float]:
    """
    Calcula MDAT y Vacas promedio 4 sem y 52 sem.
    Retorna (mdat_4w, vacas_4w, mdat_52w, vacas_52w).
    """
    if df_hist is None or current_week is None or df_hist.empty:
        return np.nan, np.nan, np.nan, np.nan
    
    # Check if required columns exist
    if "Establecimiento" not in df_hist.columns:
        return np.nan, np.nan, np.nan, np.nan
    
    # Filtrar por establecimiento
    # (Asumimos que en df_hist la columna se llama 'Establecimiento' y 'N° Semana')
    # Normalizamos nombre est para asegurar match
    # (Ojo: df_hist ya viene cargado, asumimos nombres limpios o hacemos strip)
    mask_est = df_hist["Establecimiento"].astype(str).str.strip() == str(est).strip()
    
    # Filtrar semanas ANTERIORES o IGUALES a la actual (historia)
    # Normalmente el reporte es de la semana cerrada, así que incluimos la actual si está en el histórico?
    # O el histórico es "lo anterior"?
    # Supuesto: El histórico tiene datos hasta la semana pasada o incluye esta si ya se cerró.
    # Usaremos <= current_week.
    mask_week = df_hist["N° Semana"] <= current_week
    
    df_est = df_hist[mask_est & mask_week].copy()
    
    if df_est.empty:
        return np.nan, np.nan, np.nan, np.nan

    # Asegurar orden descendente por semana
    df_est = df_est.sort_values("N° Semana", ascending=False)
    
    # Lógica DAX:
    # MDAT 4 sem = SUM(MDAT en rango [end-3, end]) / 4
    # MDAT 52 sem = SUM(MDAT en rango [end-51, end]) / 52
    # Nota: El rango es INCLUSIVO.
    
    # Filtrar rangos explícitos
    # Rango 4 semanas: [current_week - 3, current_week]
    start_4w = current_week - 3
    df_4w = df_est[(df_est["N° Semana"] >= start_4w) & (df_est["N° Semana"] <= current_week)]
    
    # Rango 52 semanas: [current_week - 51, current_week]
    start_52w = current_week - 51
    df_52w = df_est[(df_est["N° Semana"] >= start_52w) & (df_est["N° Semana"] <= current_week)]
    
    # Calculo MDAT
    # DAX: DIVIDE ( SUMX ( Historico, VALUE ( Historico[(I) MDAT] ) ), 4 )
    # Si no hay datos, la suma es 0. 0/4 = 0. 
    # Pero queremos NaN si no hay NADA de datos? 
    # El DAX devuelve 0 si no hay datos? DIVIDE maneja div/0, pero aquí el denominador es cte.
    # Asumiremos que si el df filtrado está vacío, devolvemos NaN para no ensuciar con ceros.
    
    if not df_4w.empty:
        val_4w = df_4w["MDAT"].sum() / 4.0
    else:
        val_4w = np.nan
        
    if not df_52w.empty:
        val_52w = df_52w["MDAT"].sum() / 52.0
    else:
        val_52w = np.nan
    
    # Vacas (si existe la columna, asumimos "Vacas en ordeña" o similar en histórico)
    # Buscamos columna de vacas en histórico
    vacas_col = next((c for c in df_est.columns if "vacas" in c.lower() and "ordeña" in c.lower()), None)
    if not vacas_col:
        # Fallback: intentar buscar solo "Vacas" si no hay ambigüedad
        vacas_col = next((c for c in df_est.columns if c.lower() == "vacas"), None)
        
    if vacas_col:
        # Aplicamos la misma lógica de promedio simple (suma / N) o promedio real?
        # El usuario solo pasó DAX de MDAT.
        # Para vacas, "Promedio 4 sem" suele ser promedio real (SUM / count) o (SUM / 4)?
        # Si MDAT es (L/vaca/día * Precio) o similar, es un flujo.
        # Vacas es stock. Promedio de stock tiene sentido.
        # Si usamos la lógica de MDAT (SUM/4), estaríamos sumando vacas de 4 semanas y dividiendo por 4.
        # Eso es el promedio aritmético simple, asumiendo 4 datos.
        # Si faltan datos (ej. solo 2 semanas), SUM/4 daría la mitad del stock real.
        # Para vacas, tiene más sentido mean().
        # PERO, si queremos consistencia con MDAT DAX, quizás debamos usar la misma lógica.
        # Sin embargo, MDAT DAX divide por 4 fijo.
        # Si falta una semana, el MDAT promedio baja.
        # Haremos lo mismo para vacas para ser consistentes con "Promedio 4 sem" del reporte.
        
        if not df_4w.empty:
            vacas_4w = df_4w[vacas_col].sum() / 4.0
        else:
            vacas_4w = np.nan
            
        if not df_52w.empty:
            vacas_52w = df_52w[vacas_col].sum() / 52.0
        else:
            vacas_52w = np.nan
    else:
        vacas_4w = np.nan
        vacas_52w = np.nan
    
    return val_4w, vacas_4w, val_52w, vacas_52w


def _wavg(values: pd.Series, weights: pd.Series) -> float:
    """Promedio ponderado seguro (ignora NaNs y pesos cero)."""
    if values is None or weights is None:
        return np.nan

    values = pd.to_numeric(values, errors="coerce")
    weights = pd.to_numeric(weights, errors="coerce")

    mask = (~pd.isna(values)) & (~pd.isna(weights)) & (weights != 0)
    if not mask.any():
        return np.nan

    num = (values[mask] * weights[mask]).sum()
    den = weights[mask].sum()
    if den == 0 or pd.isna(den):
        return np.nan

    return float(num / den)


def _total_row(df_matrix: pd.DataFrame) -> dict:
    """
    Calcula la fila 'Sumas y Promedios' imitando la lógica de tu medida DAX:

    - Algunas columnas: SUMA directa (vacas, superficie).
    - Otras: promedios ponderados por Vacas en ordeña o Vacas×Producción.
    - MDAT y MDAT (L/vaca/día) coherentes con esos ponderados.
    """
    # Trabajamos solo con filas de establecimientos (sin el total)
    est_rows = df_matrix.copy()
    est_rows = est_rows[est_rows["Establecimiento"] != "Sumas y Promedios"]

    totals: dict = {"Establecimiento": "Sumas y Promedios"}

    # Sumas directas
    for col in ["Vacas en ordeña", "Vacas masa", "Superficie Praderas"]:
        if col in est_rows.columns:
            totals[col] = pd.to_numeric(est_rows[col], errors="coerce").sum()
        else:
            totals[col] = np.nan

    # Series auxiliares
    vacas = pd.to_numeric(est_rows.get("Vacas en ordeña"), errors="coerce")
    prod = pd.to_numeric(est_rows.get("Producción promedio"), errors="coerce")
    precio = pd.to_numeric(est_rows.get("Precio de la leche"), errors="coerce")
    costo_racion = pd.to_numeric(est_rows.get("Costo ración vaca"), errors="coerce")
    
    # Componentes de MS (ya no están en MATRIX_COLUMNS, pero los necesitamos para el total?)
    # Si no están en la matriz, no podemos leerlos de est_rows.
    # Debemos usar "Praderas y otros verdes" y "Total MS" directamente si es posible,
    # o aceptar que sin los componentes no podemos recalcular ponderados exactos de componentes.
    # Pero "Praderas y otros verdes" es un promedio de (Kg MS Pradera + Kg MS Verde).
    # El promedio ponderado de una suma es la suma de los promedios ponderados.
    # Así que podemos ponderar "Praderas y otros verdes" directamente.
    
    praderas_otros = pd.to_numeric(est_rows.get("Praderas y otros verdes"), errors="coerce")
    total_ms = pd.to_numeric(est_rows.get("Total MS"), errors="coerce")
    
    ms_concentrado = pd.to_numeric(est_rows.get("Kg MS Concentrado / vaca"), errors="coerce")
    ms_conservado = pd.to_numeric(est_rows.get("Kg MS Conservado / vaca"), errors="coerce")
    
    gramos_litro = pd.to_numeric(est_rows.get("Grms concentrado / ltr leche"), errors="coerce")
    grasa = pd.to_numeric(est_rows.get("Porcentaje de grasa"), errors="coerce")
    prote = pd.to_numeric(est_rows.get("Proteinas"), errors="coerce")
    mdat = pd.to_numeric(est_rows.get("MDAT"), errors="coerce")

    # Pesos
    peso_vacas = vacas
    peso_vacas_litros = vacas * prod  # Vacas en ordeña * producción promedio

    # Producción promedio: ponderada por vacas
    totals["Producción promedio"] = _wavg(prod, peso_vacas)

    # Kg MS ... / vaca: ponderados por vacas
    totals["Kg MS Concentrado / vaca"] = _wavg(ms_concentrado, peso_vacas)
    totals["Kg MS Conservado / vaca"] = _wavg(ms_conservado, peso_vacas)
    totals["Praderas y otros verdes"] = _wavg(praderas_otros, peso_vacas)
    totals["Total MS"] = _wavg(total_ms, peso_vacas)

    # Precio de la leche: ponderado por Vacas * Producción (litros totales)
    totals["Precio de la leche"] = _wavg(precio, peso_vacas_litros)

    # Costo ración vaca: ponderado por vacas
    totals["Costo ración vaca"] = _wavg(costo_racion, peso_vacas)

    # Grms concentrado / ltr leche: ponderado por Vacas * Producción
    totals["Grms concentrado / ltr leche"] = _wavg(gramos_litro, peso_vacas_litros)

    # Porcentajes: ponderados por vacas (ya vienen como % “de verdad”)
    totals["Porcentaje de grasa"] = _wavg(grasa, peso_vacas)
    totals["Proteinas"] = _wavg(prote, peso_vacas)

    # Carga animal: Suma vacas masa / Suma superficie
    vacas_masa_tot = totals.get("Vacas masa")
    sup_tot = totals.get("Superficie Praderas")
    if sup_tot and sup_tot > 0:
        totals["Carga animal"] = vacas_masa_tot / sup_tot
    else:
        totals["Carga animal"] = np.nan

    # MDAT total (pesos/vaca/día): ponderado por vacas
    totals["MDAT"] = _wavg(mdat, peso_vacas)

    # MDAT 4 sem y 52 sem (Promedios ponderados por vacas actuales)
    mdat_4w = pd.to_numeric(est_rows.get("MDAT 4 sem"), errors="coerce")
    mdat_52w = pd.to_numeric(est_rows.get("MDAT 52 sem"), errors="coerce")
    vacas_4w = pd.to_numeric(est_rows.get("Vacas 4 sem"), errors="coerce")
    vacas_52w = pd.to_numeric(est_rows.get("Vacas 52 sem"), errors="coerce")
    
    totals["MDAT 4 sem"] = _wavg(mdat_4w, peso_vacas)
    totals["MDAT 52 sem"] = _wavg(mdat_52w, peso_vacas)
    
    # Vacas históricas promedio (ponderado? no, suma de promedios? o promedio simple?)
    # Si es "Vacas en ordeña (Prom 4 sem)" para la empresa total, debería ser la suma de los promedios de cada campo.
    totals["Vacas 4 sem"] = vacas_4w.sum()
    totals["Vacas 52 sem"] = vacas_52w.sum()
    
    # Rankings en totales siempre van vacíos
    totals["Ranking 4 sem"] = np.nan
    totals["Ranking 52 sem"] = np.nan

    # MDAT (L/vaca/día) y % Costo alimentos
    precio_tot = totals.get("Precio de la leche")
    mdat_tot = totals.get("MDAT")
    costo_vaca_tot = totals.get("Costo ración vaca")
    prod_tot = totals.get("Producción promedio")

    if precio_tot and precio_tot != 0:
        totals["MDAT (L/vaca/día)"] = mdat_tot / precio_tot if mdat_tot is not None else np.nan
        
        # % Costo = Costo / (Precio * Prod)
        if prod_tot:
            ingreso_tot = precio_tot * prod_tot
            totals["Porcentaje costo alimentos"] = (costo_vaca_tot / ingreso_tot) if ingreso_tot > 0 else np.nan
        else:
            totals["Porcentaje costo alimentos"] = np.nan
    else:
        totals["MDAT (L/vaca/día)"] = np.nan
        totals["Porcentaje costo alimentos"] = np.nan

    # Sintéticos del total: ya calculados arriba como ponderados
    # (No necesitamos recalcular sumas porque ponderar la suma es igual a sumar los ponderados,
    # y ya ponderamos "Total MS" y "Praderas y otros verdes" directamente).
    pass

    return totals


def build_matrix(
    df: pd.DataFrame,
    df_hist: pd.DataFrame | None = None,
    current_week: int | None = None
) -> pd.DataFrame:
    """
    Construye la matriz semanal estilo Power BI.
    Si df_hist y current_week están presentes, calcula métricas históricas.
    """
    # Normalizar conceptos a claves internas
    df_norm = attach_normalized_concepts(df)
    ests = sorted(df_norm["Establecimiento"].unique())

    rows: list[dict] = []

    for est in ests:
        row: dict = {"Establecimiento": est}

        # Métricas base desde A. TOTAL
        for raw, norm in CONCEPT_MAP.items():
            row[raw] = compute_metric(df_norm, est, norm)

        # Sintéticos (praderas / total MS)
        pv, total_ms = _sinteticos(row)
        row["Praderas y otros verdes"] = pv
        row["Total MS"] = total_ms

        # Derivados
        mdat, mdat_l, carga, pct_costo = _derivados(row)
        row["MDAT"] = mdat
        row["MDAT (L/vaca/día)"] = mdat_l
        row["Carga animal"] = carga
        row["Porcentaje costo alimentos"] = pct_costo

        # Históricos
        m4, v4, m52, v52 = _get_historic_metrics(est, current_week, df_hist)
        row["MDAT 4 sem"] = m4
        row["Vacas 4 sem"] = v4
        row["MDAT 52 sem"] = m52
        row["Vacas 52 sem"] = v52
        
        # Rankings (placeholders, se calculan abajo con todo el DF)
        row["Ranking 4 sem"] = np.nan
        row["Ranking 52 sem"] = np.nan

        rows.append(row)

    # Construimos dataframe en el orden deseado
    df_matrix = pd.DataFrame(rows)

    # Aseguramos que todas las columnas existan (aunque queden NaN)
    for col in MATRIX_COLUMNS:
        if col not in df_matrix.columns:
            df_matrix[col] = np.nan

    df_matrix = df_matrix[MATRIX_COLUMNS]

    # Calcular Rankings Históricos (1 = Mayor MDAT)
    # Solo sobre filas que tengan dato
    if "MDAT 4 sem" in df_matrix.columns:
        df_matrix["Ranking 4 sem"] = (
            df_matrix["MDAT 4 sem"]
            .rank(ascending=False, method="min")
            .astype("Int64")
        )
        
    if "MDAT 52 sem" in df_matrix.columns:
        df_matrix["Ranking 52 sem"] = (
            df_matrix["MDAT 52 sem"]
            .rank(ascending=False, method="min")
            .astype("Int64")
        )

    # Fila Sumas y Promedios (ponderada)
    totals = _total_row(df_matrix)
    totals_df = pd.DataFrame([totals])
    
    # Asegurar que totals_df tenga las mismas columnas y orden que df_matrix para evitar warnings
    # y asegurar consistencia
    totals_df = totals_df.reindex(columns=df_matrix.columns)
    
    # Concatenación segura
    df_matrix = pd.concat([df_matrix, totals_df], ignore_index=True)

    return df_matrix

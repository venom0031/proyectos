# matrix_builder.py

import pandas as pd
import numpy as np

from concept_engine import (
    compute_metric,
    attach_normalized_concepts,
    CONCEPT_MAP,
)
from db_connection import execute_query

# Orden de columnas igual al Power BI
MATRIX_COLUMNS = [
    "Establecimiento",
    "Superficie Praderas",
    "Vacas masa", "Vacas en ordeña",
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
    """Praderas y otros verdes / Total MS por establecimiento.
    
    IMPORTANTE: "Praderas y otros verdes" viene ya sumado de la BD (Pradera + Verde).
    Usamos el valor directamente si existe, si no, lo calculamos de componentes.
    """
    # Intentar obtener "Praderas y otros verdes" directamente (viene de la BD)
    pv = _safe_val(row, "Praderas y otros verdes")
    
    # Si no tiene valor, calcularlo de componentes (para compatibilidad con Excel directo)
    if pv == 0:
        pr = _safe_val(row, "Kg MS Pradera / vaca")
        ve = _safe_val(row, "Kg MS Verde / vaca")
        pv = pr + ve
    
    # Total MS SIEMPRE = Praderas y otros verdes + Concentrado + Conservado
    co = _safe_val(row, "Kg MS Conservado / vaca")
    cn = _safe_val(row, "Kg MS Concentrado / vaca")
    total_ms = pv + co + cn
    return pv, total_ms


def _derivados(row: dict):
    """MDAT, MDAT (L/vaca/día), Costo ración (L/vaca/día) por establecimiento."""
    prod = row.get("Producción promedio")
    precio = row.get("Precio de la leche")
    costo = row.get("Costo ración vaca")
    vacas_masa = row.get("Vacas masa")
    sup = row.get("Superficie Praderas")

    # Carga animal = Vacas masa / Superficie
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


def _load_historico_from_db(current_week: int) -> pd.DataFrame:
    """
    Carga datos históricos desde la tabla datos_historicos.
    Obtiene las últimas 52 semanas para cálculos de promedios.
    """
    try:
        # Cargar histórico de las últimas 52 semanas (excluyendo la actual)
        query = """
            SELECT 
                semana as "N° Semana",
                establecimiento as "Establecimiento",
                mdat as "MDAT",
                vacas_en_ordena as "Vacas en ordeña"
            FROM datos_historicos
            WHERE semana < %s AND semana >= %s
            ORDER BY semana DESC
        """
        start_week = current_week - 52
        results = execute_query(query, (current_week, start_week))
        
        if results:
            return pd.DataFrame(results)
        return pd.DataFrame()
    except Exception as e:
        print(f"Error cargando histórico: {e}")
        return pd.DataFrame()


def _get_historic_metrics(
    est: str,
    current_week: int | None,
    df_hist: pd.DataFrame | None = None
) -> tuple[float, float, float, float]:
    """
    Calcula MDAT y Vacas promedio 4 sem y 52 sem.
    Retorna (mdat_4w, vacas_4w, mdat_52w, vacas_52w).
    
    IMPORTANTE: Usa la semana más alta del histórico para cada establecimiento,
    NO la semana de datos_semanales (que puede tener numeración diferente).
    """
    # Si no se pasa histórico, cargarlo desde la BD
    if df_hist is None or df_hist.empty:
        df_hist = _load_historico_from_db(current_week if current_week else 999)
    
    if df_hist.empty:
        return np.nan, np.nan, np.nan, np.nan
    
    # Check if required columns exist
    if "Establecimiento" not in df_hist.columns or "N° Semana" not in df_hist.columns:
        return np.nan, np.nan, np.nan, np.nan
    
    # Filtrar por establecimiento (match exacto)
    mask_est = df_hist["Establecimiento"].astype(str).str.strip() == str(est).strip()
    df_est = df_hist[mask_est].copy()
    
    if df_est.empty:
        return np.nan, np.nan, np.nan, np.nan

    # Obtener la semana MÁXIMA del histórico para ESTE establecimiento
    # Esta es la "semana actual" desde la perspectiva del histórico
    max_week_est = int(df_est["N° Semana"].max())
    
    # Asegurar orden descendente por semana
    df_est = df_est.sort_values("N° Semana", ascending=False)
    
    # Lógica: Usar las últimas 4 y 52 semanas DESDE la semana máxima del establecimiento
    # Rango 4 semanas: [max_week - 3, max_week] (las últimas 4 incluyendo la más reciente)
    start_4w = max_week_est - 3
    end_4w = max_week_est
    df_4w = df_est[(df_est["N° Semana"] >= start_4w) & (df_est["N° Semana"] <= end_4w)]
    
    # Rango 52 semanas: [max_week - 51, max_week] (las últimas 52 incluyendo la más reciente)
    start_52w = max_week_est - 51
    end_52w = max_week_est
    df_52w = df_est[(df_est["N° Semana"] >= start_52w) & (df_est["N° Semana"] <= end_52w)]
    
    # Calcular MDAT promedio (dividir por cantidad REAL de registros, no por 4 o 52 fijos)
    if not df_4w.empty and "MDAT" in df_4w.columns:
        mdat_values_4w = df_4w["MDAT"].dropna()
        if len(mdat_values_4w) > 0:
            val_4w = float(mdat_values_4w.mean())
        else:
            val_4w = np.nan
    else:
        val_4w = np.nan
        
    if not df_52w.empty and "MDAT" in df_52w.columns:
        mdat_values_52w = df_52w["MDAT"].dropna()
        if len(mdat_values_52w) > 0:
            val_52w = float(mdat_values_52w.mean())
        else:
            val_52w = np.nan
    else:
        val_52w = np.nan
    
    # Calcular Vacas promedio
    vacas_col = "Vacas en ordeña"
    if vacas_col in df_est.columns:
        if not df_4w.empty:
            vacas_values_4w = df_4w[vacas_col].dropna()
            if len(vacas_values_4w) > 0:
                vacas_4w = float(vacas_values_4w.mean())
            else:
                vacas_4w = np.nan
        else:
            vacas_4w = np.nan
            
        if not df_52w.empty:
            vacas_values_52w = df_52w[vacas_col].dropna()
            if len(vacas_values_52w) > 0:
                vacas_52w = float(vacas_values_52w.mean())
            else:
                vacas_52w = np.nan
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
    costo_concentrado = pd.to_numeric(est_rows.get("Costo promedio concentrado"), errors="coerce")
    
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

    # Costo promedio concentrado: ponderado por vacas
    totals["Costo promedio concentrado"] = _wavg(costo_concentrado, peso_vacas)

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
        # Mantener MDAT tal como viene de A. TOTAL (compute_metric se encarga de A TOTAL o promedio de días)
        # Calcular solo derivados sin sobreescribir MDAT
        _, mdat_l, carga, pct_costo = _derivados(row)
        # Si mdat_l es None o NaN, intentar calcular promedio de los días con datos de MDAT (L/vaca/día)
        if mdat_l is None or (isinstance(mdat_l, float) and pd.isna(mdat_l)):
            # Buscar columnas de fechas con formato dd-mm-yyyy
            date_pattern = re.compile(r'^\d{1,2}-\d{1,2}-\d{4}$')
            date_cols = [col for col in df_norm.columns if date_pattern.match(str(col))]
            sub = df_norm[(df_norm["Establecimiento"] == est) & (df_norm["Concepto_Norm"] == "mdat")]
            if not sub.empty and date_cols:
                vals = pd.to_numeric(sub[date_cols].values.flatten(), errors="coerce")
                vals = pd.Series(vals).dropna()
                if len(vals) > 0:
                    mdat_l = vals.mean()
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

# etl.py
# Carga los Excels:
#  - semanal consolidado (base de la matriz tipo Power BI, usando A. TOTAL)
#  - histórico persistente (MDAT por semana, etc.)

from __future__ import annotations

import re
from typing import Any

import pandas as pd


# ---------------------------------------------------------
# Normalizadores auxiliares (semanal)
# ---------------------------------------------------------
def _normalize_col(col: Any) -> str:
    """Normaliza nombres de columnas a un formato estable."""
    col = str(col).strip()
    col = col.replace("\u00A0", "")   # espacio duro
    col = col.replace("\ufeff", "")   # BOM
    col = col.lower().strip()
    col = col.replace(" ", "_")
    col = col.replace(".", "")
    col = col.replace("__", "_")
    return col


def _normalize_number(x: Any) -> float | None:
    """
    Convierte números de texto a float manejando:
    - "869.43"       (punto decimal)
    - "869,43"       (coma decimal)
    - "1.234,56"     (miles con punto, decimal con coma)
    - valores con $, %, espacios, etc.

    Si no puede convertirse, devuelve None.
    """
    if pd.isna(x):
        return None

    txt = str(x).strip()
    if not txt:
        return None

    # quitar símbolos y espacios
    txt = txt.replace("$", "").replace("%", "").replace(" ", "")

    has_dot = "." in txt
    has_comma = "," in txt

    if has_dot and has_comma:
        # Formato tipo "1.234,56" → "1234.56"
        txt = txt.replace(".", "")
        txt = txt.replace(",", ".")
    elif has_comma and not has_dot:
        # Formato tipo "869,43" → "869.43"
        txt = txt.replace(",", ".")
    # Si solo tiene punto o no tiene separador, lo dejamos tal cual:
    #   "869.43" → "869.43"
    #   "200022" → "200022"

    try:
        return float(txt)
    except Exception:
        # Si algo raro se cuela, lo dejamos como None para no reventar
        return None


def _clean_concept(raw: Any) -> str | None:
    """
    Limpia el texto del CONCEPTO:
    - Saca prefijos tipo "(A) ", "(1) Producción ...", "(BB) "
    - Deja el nombre “bonito” que luego mapeamos en concept_engine.
    """
    if raw is None or pd.isna(raw):
        return None

    txt = str(raw).strip()
    # Quitar prefijo entre paréntesis + espacio: "(A) ", "(1) ", "(BB) "
    txt = re.sub(r"^\([A-Za-z0-9]+\)\s*", "", txt)
    # Quitar dobles espacios perdidos
    while "  " in txt:
        txt = txt.replace("  ", " ")
    txt = txt.strip()

    return txt or None


def normalize_est_name(name: str) -> str:
    """
    Normaliza el nombre del establecimiento para asegurar cruces robustos.
    - Quita espacios extra.
    - Quita prefijos comunes: "Agricola", "Soc.", "Ag.", "Fundo".
    - Pasa a mayúsculas/título consistente (opcional, aquí usamos original pero limpio).
    """
    if not isinstance(name, str):
        return str(name)
    
    clean = name.strip()
    
    # Lista de prefijos a eliminar (orden importa: más largos primero)
    prefixes = [
        "Soc. Agricola", "Soc. Agr.", "Agricola", "Agr.", "Ag.", "Fundo", "Soc."
    ]
    
    for p in prefixes:
        if clean.lower().startswith(p.lower() + " "):
            clean = clean[len(p):].strip()
            
    return clean


# ---------------------------------------------------------
# Carga principal semanal (BASE DE LA MATRIZ)
# ---------------------------------------------------------
def load_week_excel(path_or_buffer: Any) -> pd.DataFrame:
    """
    Carga un Excel semanal consolidado y devuelve un DataFrame con:

        Empresa | Empresa_COD | Establecimiento | CONCEPTO | A. TOTAL

    - Acepta ruta, BytesIO o UploadedFile de Streamlit.
    - Lee todo como texto.
    - Normaliza nombres de columnas.
    - Usa solo 'A. TOTAL' como base para la matriz semanal.
    """
    # Leer todo como string para control absoluto
    df = pd.read_excel(path_or_buffer, dtype=str)

    # Normalizar nombres de columnas a snake_case
    df.columns = [_normalize_col(c) for c in df.columns]

    # Mapear las que nos interesan (si existen)
    col_map: dict[str, str] = {}
    if "empresa" in df.columns:
        col_map["empresa"] = "empresa"
    if "empresa_cod" in df.columns:
        col_map["empresa_cod"] = "empresa_cod"
    if "establecimiento" in df.columns:
        col_map["establecimiento"] = "establecimiento"
    if "concepto" in df.columns:
        col_map["concepto"] = "concepto"
    if "a_total" in df.columns:
        col_map["a_total"] = "a_total"
    if "n_semana" in df.columns:
        col_map["n_semana"] = "n_semana"
    elif "semana" in df.columns:
        col_map["semana"] = "n_semana"
    
    # Nuevo: Capturar Categoria
    if "categoria" in df.columns:
        col_map["categoria"] = "categoria"

    # Nuevo: Capturar columnas de fecha (dd-mm-yyyy)
    # Buscamos columnas que coincidan con patrón de fecha
    date_cols = []
    for c in df.columns:
        # Regex simple para dd-mm-yyyy o d-m-yyyy
        if re.match(r"^\d{1,2}-\d{1,2}-\d{4}$", c):
            date_cols.append(c)
            col_map[c] = c

    df = df.rename(columns=col_map)

    # Asegurar columnas mínimas
    if "empresa" not in df.columns:
        raise KeyError(
            "No se encontró la columna 'Empresa' en el Excel "
            "(cabecera normalizada 'empresa')."
        )

    if "establecimiento" not in df.columns:
        raise KeyError(
            "No se encontró la columna 'Establecimiento' en el Excel "
            "(cabecera normalizada 'establecimiento')."
        )

    if "concepto" not in df.columns:
        raise KeyError(
            "No se encontró la columna 'CONCEPTO' en el Excel "
            "(cabecera normalizada 'concepto')."
        )

    if "a_total" not in df.columns:
        raise KeyError(
            "No se encontró la columna 'A. TOTAL' en el Excel "
            "(cabecera normalizada 'a_total')."
        )

    # Si no viene Empresa_COD, la creamos igual a Empresa
    if "empresa_cod" not in df.columns:
        df["empresa_cod"] = df["empresa"]

    # Nos quedamos solo con lo necesario (agregamos n_semana si existe)
    cols_to_keep = ["empresa", "empresa_cod", "establecimiento", "concepto", "a_total"]
    if "n_semana" in df.columns:
        cols_to_keep.append("n_semana")
    
    # Agregamos categoria si existe
    if "categoria" in df.columns:
        cols_to_keep.append("categoria")
        
    # Agregamos columnas de fecha
    cols_to_keep.extend(date_cols)

    df = df[cols_to_keep].copy()

    # Limpiar conceptos a la forma que espera concept_engine
    df["concepto"] = df["concepto"].apply(_clean_concept)

    # Normalizar A. TOTAL a float (respetando decimales reales)
    df["a_total"] = df["a_total"].apply(_normalize_number)

    # Normalizar columnas de fecha a float también (son métricas diarias)
    for dc in date_cols:
        df[dc] = df[dc].apply(_normalize_number)

    if "n_semana" in df.columns:
        df["n_semana"] = df["n_semana"].apply(_normalize_number).astype("Int64")

    # Quitar basura de espacios en texto
    df["establecimiento"] = df["establecimiento"].astype(str).str.strip()
    df["empresa"] = df["empresa"].astype(str).str.strip()
    df["empresa_cod"] = df["empresa_cod"].astype(str).str.strip()
    
    if "categoria" in df.columns:
        df["categoria"] = df["categoria"].astype(str).str.strip()

    # Normalización robusta de nombres
    df["establecimiento"] = df["establecimiento"].apply(normalize_est_name)

    # Devolver con los mismos nombres que usas en Power BI / DAX
    rename_dict = {
        "empresa": "Empresa",
        "empresa_cod": "Empresa_COD",
        "establecimiento": "Establecimiento",
        "concepto": "CONCEPTO",
        "a_total": "A. TOTAL",
        "n_semana": "N° Semana",
        "categoria": "CATEGORIA",
    }
    # Mantener nombres de fechas tal cual
    for dc in date_cols:
        rename_dict[dc] = dc
        
    df = df.rename(columns=rename_dict)

    return df


# ---------------------------------------------------------
# Carga del HISTÓRICO PERSISTENTE (MDAT por semana, etc.)
# ---------------------------------------------------------
def load_historic_excel(path_or_buffer: Any) -> pd.DataFrame:
    """
    Carga el Excel HISTORICO PERSISTENTE.xlsx (hoja 'SIC PROM') y devuelve
    un DataFrame listo para usar como tabla de histórico en la lógica de
    MDAT 4 sem / 12 m, etc.

    Devuelve, al menos, columnas:
        Fecha, N° Semana, Empresa, Establecimiento, MDAT
    """
    # Leemos hoja SIC PROM tal como en Power Query
    df = pd.read_excel(path_or_buffer, sheet_name="SIC PROM")

    # Tipos base
    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")

    if "N° Semana" in df.columns:
        df["N° Semana"] = pd.to_numeric(df["N° Semana"], errors="coerce").astype("Int64")

    # Detectar la columna MDAT real (como en tu M)
    candidatos = ["MDAT", "(I) MDAT", "I) MDAT", "MDAT (I)", "I MDAT"]
    mdat_col = next((c for c in candidatos if c in df.columns), None)

    if mdat_col is None:
        raise KeyError(
            "No se encontró la columna MDAT (ni variantes '(I) MDAT', 'MDAT (I)', etc.) "
            "en el histórico."
        )

    # Conversión robusta SOLO para MDAT
    df["MDAT"] = df[mdat_col].apply(_normalize_number)

    # Normalizar nombre de empresa específico
    # Si existe Empresa pero no Establecimiento, renombramos
    if "Empresa" in df.columns and "Establecimiento" not in df.columns:
        df = df.rename(columns={"Empresa": "Establecimiento"})

    if "Establecimiento" in df.columns:
        df["Establecimiento"] = df["Establecimiento"].replace({"Ag. Los Maitenes": "Los Maitenes"})
        # Normalización robusta
        df["Establecimiento"] = df["Establecimiento"].apply(normalize_est_name)

    # Ordenar por semana descendente (como en M)
    if "N° Semana" in df.columns:
        df = df.sort_values("N° Semana", ascending=False)

    return df


# ---------------------------------------------------------
# Funciones PostgreSQL (con RLS automático)
# ---------------------------------------------------------
def load_week_from_db(user_id: int, is_admin: bool = False, semana: int = None, anio: int = None) -> pd.DataFrame:
    """
    Carga datos semanales desde PostgreSQL para construir la matriz semanal.
    
    IMPORTANTE: Esta función carga datos de datos_semanales que NO tiene RLS,
    por lo que muestra TODAS las empresas (para el ranking semanal).
    
    Args:
        user_id: ID del usuario (para logging, no afecta RLS en esta tabla)
        is_admin: Si es administrador
        semana: Número de semana a cargar (None = última disponible)
        anio: Año de la semana (None = año actual)
        
    Returns:
        DataFrame con estructura similar a load_week_excel:
        Empresa | Empresa_COD | Establecimiento | CONCEPTO | A. TOTAL | N° Semana
    """
    try:
        from db_connection import execute_query
    except ImportError:
        raise ImportError("Módulo db_connection no disponible. Asegúrate de tener psycopg2 instalado.")
    
    # Si no se especifica semana/anio, usar la más reciente
    if semana is None or anio is None:
        query_max = """
            SELECT MAX(semana) as semana, MAX(anio) as anio
            FROM datos_semanales
        """
        result = execute_query(query_max, user_id=user_id, is_admin=is_admin, fetch_one=True)
        if result:
            semana = result['semana'] if semana is None else semana
            anio = result['anio'] if anio is None else anio
    
    # Query principal - datos_semanales NO tiene RLS, muestra todas las empresas
    query = """
        SELECT 
            emp.nombre as "Empresa",
            emp.codigo as "Empresa_COD",
            est.nombre as "Establecimiento",
            ds.semana as "N° Semana",
            -- Transformar datos de columnas a filas (unpivot)
            'Superficie Praderas' as "CONCEPTO", ds.superficie_pradera as "A. TOTAL"
        FROM datos_semanales ds
        JOIN establecimientos est ON ds.establecimiento_id = est.id
        JOIN empresas emp ON ds.empresa_id = emp.id
        WHERE ds.semana = %s AND ds.anio = %s AND ds.superficie_pradera IS NOT NULL
        
        UNION ALL
        
        SELECT 
            emp.nombre, emp.codigo, est.nombre, ds.semana,
            'Vacas masa', ds.vacas_masa
        FROM datos_semanales ds
        JOIN establecimientos est ON ds.establecimiento_id = est.id
        JOIN empresas emp ON ds.empresa_id = emp.id
        WHERE ds.semana = %s AND ds.anio = %s AND ds.vacas_masa IS NOT NULL
        
        UNION ALL
        
        SELECT emp.nombre, emp.codigo, est.nombre, ds.semana,
            'Vacas en ordeña', ds.vacas_en_ordena
        FROM datos_semanales ds
        JOIN establecimientos est ON ds.establecimiento_id = est.id
        JOIN empresas emp ON ds.empresa_id = emp.id
        WHERE ds.semana = %s AND ds.anio = %s AND ds.vacas_en_ordena IS NOT NULL
        
        UNION ALL
        
        SELECT emp.nombre, emp.codigo, est.nombre, ds.semana,
            'Carga animal', ds.carga_animal
        FROM datos_semanales ds
        JOIN establecimientos est ON ds.establecimiento_id = est.id
        JOIN empresas emp ON ds.empresa_id = emp.id
        WHERE ds.semana = %s AND ds.anio = %s AND ds.carga_animal IS NOT NULL
        
        UNION ALL
        
        SELECT emp.nombre, emp.codigo, est.nombre, ds.semana,
            'Porcentaje de grasa', ds.porcentaje_grasa
        FROM datos_semanales ds
        JOIN establecimientos est ON ds.establecimiento_id = est.id
        JOIN empresas emp ON ds.empresa_id = emp.id
        WHERE ds.semana = %s AND ds.anio = %s AND ds.porcentaje_grasa IS NOT NULL
        
        UNION ALL
        
        SELECT emp.nombre, emp.codigo, est.nombre, ds.semana,
            'Proteinas', ds.proteinas
        FROM datos_semanales ds
        JOIN establecimientos est ON ds.establecimiento_id = est.id
        JOIN empresas emp ON ds.empresa_id = emp.id
        WHERE ds.semana = %s AND ds.anio = %s AND ds.proteinas IS NOT NULL
        
        UNION ALL
        
        SELECT emp.nombre, emp.codigo, est.nombre, ds.semana,
            'Costo promedio concentrado', ds.costo_promedio_concentrado
        FROM datos_semanales ds
        JOIN establecimientos est ON ds.establecimiento_id = est.id
        JOIN empresas emp ON ds.empresa_id = emp.id
        WHERE ds.semana = %s AND ds.anio = %s AND ds.costo_promedio_concentrado IS NOT NULL
        
        UNION ALL
        
        SELECT emp.nombre, emp.codigo, est.nombre, ds.semana,
            'Grms concentrado / ltr leche', ds.grms_concentrado_por_litro
        FROM datos_semanales ds
        JOIN establecimientos est ON ds.establecimiento_id = est.id
        JOIN empresas emp ON ds.empresa_id = emp.id
        WHERE ds.semana = %s AND ds.anio = %s AND ds.grms_concentrado_por_litro IS NOT NULL
        
        UNION ALL
        
        SELECT emp.nombre, emp.codigo, est.nombre, ds.semana,
            'Kg MS Concentrado / vaca', ds.kg_ms_concentrado_vaca
        FROM datos_semanales ds
        JOIN establecimientos est ON ds.establecimiento_id = est.id
        JOIN empresas emp ON ds.empresa_id = emp.id
        WHERE ds.semana = %s AND ds.anio = %s AND ds.kg_ms_concentrado_vaca IS NOT NULL
        
        UNION ALL
        
        SELECT emp.nombre, emp.codigo, est.nombre, ds.semana,
            'Kg MS Conservado / vaca', ds.kg_ms_conservado_vaca
        FROM datos_semanales ds
        JOIN establecimientos est ON ds.establecimiento_id = est.id
        JOIN empresas emp ON ds.empresa_id = emp.id
        WHERE ds.semana = %s AND ds.anio = %s AND ds.kg_ms_conservado_vaca IS NOT NULL
        
        UNION ALL
        
        SELECT emp.nombre, emp.codigo, est.nombre, ds.semana,
            'Praderas y otros verdes', ds.praderas_otros_verdes
        FROM datos_semanales ds
        JOIN establecimientos est ON ds.establecimiento_id = est.id
        JOIN empresas emp ON ds.empresa_id = emp.id
        WHERE ds.semana = %s AND ds.anio = %s
        
        UNION ALL
        
        SELECT emp.nombre, emp.codigo, est.nombre, ds.semana,
            'Total MS', ds.total_ms
        FROM datos_semanales ds
        JOIN establecimientos est ON ds.establecimiento_id = est.id
        JOIN empresas emp ON ds.empresa_id = emp.id
        WHERE ds.semana = %s AND ds.anio = %s AND ds.total_ms IS NOT NULL
        
        UNION ALL
        
        SELECT emp.nombre, emp.codigo, est.nombre, ds.semana,
            'Producción promedio', ds.produccion_promedio
        FROM datos_semanales ds
        JOIN establecimientos est ON ds.establecimiento_id = est.id
        JOIN empresas emp ON ds.empresa_id = emp.id
        WHERE ds.semana = %s AND ds.anio = %s AND ds.produccion_promedio IS NOT NULL
        
        UNION ALL
        
        SELECT emp.nombre, emp.codigo, est.nombre, ds.semana,
            'Costo ración vaca', ds.costo_racion_vaca
        FROM datos_semanales ds
        JOIN establecimientos est ON ds.establecimiento_id = est.id
        JOIN empresas emp ON ds.empresa_id = emp.id
        WHERE ds.semana = %s AND ds.anio = %s AND ds.costo_racion_vaca IS NOT NULL
        
        UNION ALL
        
        SELECT emp.nombre, emp.codigo, est.nombre, ds.semana,
            'Precio de la leche', ds.precio_leche
        FROM datos_semanales ds
        JOIN establecimientos est ON ds.establecimiento_id = est.id
        JOIN empresas emp ON ds.empresa_id = emp.id
        WHERE ds.semana = %s AND ds.anio = %s AND ds.precio_leche IS NOT NULL
        
        UNION ALL
        
        SELECT emp.nombre, emp.codigo, est.nombre, ds.semana,
            'MDAT (L/vaca/día)', ds.mdat_litros_vaca_dia
        FROM datos_semanales ds
        JOIN establecimientos est ON ds.establecimiento_id = est.id
        JOIN empresas emp ON ds.empresa_id = emp.id
        WHERE ds.semana = %s AND ds.anio = %s AND ds.mdat_litros_vaca_dia IS NOT NULL
        
        UNION ALL
        
        SELECT emp.nombre, emp.codigo, est.nombre, ds.semana,
            'Porcentaje costo alimentos', ds.porcentaje_costo_alimentos
        FROM datos_semanales ds
        JOIN establecimientos est ON ds.establecimiento_id = est.id
        JOIN empresas emp ON ds.empresa_id = emp.id
        WHERE ds.semana = %s AND ds.anio = %s AND ds.porcentaje_costo_alimentos IS NOT NULL
        
        UNION ALL
        
        SELECT emp.nombre, emp.codigo, est.nombre, ds.semana,
            'MDAT', ds.mdat
        FROM datos_semanales ds
        JOIN establecimientos est ON ds.establecimiento_id = est.id
        JOIN empresas emp ON ds.empresa_id = emp.id
        WHERE ds.semana = %s AND ds.anio = %s AND ds.mdat IS NOT NULL
        
        ORDER BY "Establecimiento", "CONCEPTO"
    """
    
    # Repetir parámetros para cada UNION (18 conceptos: Superficie, Vacas masa, Vacas en ordeña, Carga, Grasa, Proteínas, Costo conc, Grms, KG MS conc, KG MS cons, Praderas, Total MS, Producción, Costo ración, Precio, MDAT L/vaca, Porc costo, MDAT)
    params = tuple([semana, anio] * 18)
    
    results = execute_query(query, params=params, user_id=user_id, is_admin=is_admin, fetch_all=True)
    
    if not results:
        return pd.DataFrame(columns=['Empresa', 'Empresa_COD', 'Establecimiento', 'CONCEPTO', 'A. TOTAL', 'N° Semana'])
    
    df = pd.DataFrame(results)
    return df


def load_daily_from_db(user_id: int, is_admin: bool = False, establecimiento: str = None) -> pd.DataFrame:
    """
    Carga datos diarios desde PostgreSQL para el detalle diario.
    
    IMPORTANTE: Esta función usa datos_diarios que SÍ tiene RLS aplicado,
    por lo que solo muestra datos de las empresas del usuario autenticado.
    
    Args:
        user_id: ID del usuario (para RLS)
        is_admin: Si es administrador
        establecimiento: Nombre del establecimiento (None = todos los permitidos)
        
    Returns:
        DataFrame con estructura similar a load_week_excel para detalle diario:
        Establecimiento | CATEGORIA | CONCEPTO | [fechas] | A. TOTAL
    """
    try:
        from db_connection import execute_query
    except ImportError:
        raise ImportError("Módulo db_connection no disponible")
    
    # Query base con RLS aplicado automáticamente
    where_clause = ""
    params = []
    
    if establecimiento:
        where_clause = "AND est.nombre = %s"
        params.append(establecimiento)
    
    # Primero obtener las fechas disponibles
    query_fechas = f"""
        SELECT DISTINCT fecha
        FROM datos_diarios dd
        JOIN establecimientos est ON dd.establecimiento_id = est.id
        WHERE 1=1 {where_clause}
        ORDER BY fecha
    """
    
    fechas_result = execute_query(query_fechas, params=tuple(params) if params else None, 
                                    user_id=user_id, is_admin=is_admin, fetch_all=True)
    
    if not fechas_result:
        return pd.DataFrame()
    
    fechas = [r['fecha'] for r in fechas_result]
    
    # Query para obtener los datos en formato largo
    query = f"""
        SELECT 
            est.nombre as "Establecimiento",
            dd.categoria as "CATEGORIA",
            dd.concepto as "CONCEPTO",
            dd.fecha,
            dd.valor
        FROM datos_diarios dd
        JOIN establecimientos est ON dd.establecimiento_id = est.id
        WHERE 1=1 {where_clause}
        ORDER BY est.nombre, dd.categoria, dd.concepto, dd.fecha
    """
    
    results = execute_query(query, params=tuple(params) if params else None,
                            user_id=user_id, is_admin=is_admin, fetch_all=True)
    
    if not results:
        return pd.DataFrame()
    
    df_long = pd.DataFrame(results)
    
    # Pivotar para tener fechas como columnas
    df_pivot = df_long.pivot_table(
        index=['Establecimiento', 'CATEGORIA', 'CONCEPTO'],
        columns='fecha',
        values='valor',
        aggfunc='first'
    ).reset_index()
    
    # Renombrar columnas de fecha al formato dd-mm-yyyy
    date_cols = {}
    for col in df_pivot.columns:
        if isinstance(col, pd.Timestamp) or hasattr(col, 'strftime'):
            date_cols[col] = col.strftime('%d-%m-%Y')
    
    df_pivot = df_pivot.rename(columns=date_cols)
    
    # Calcular A. TOTAL (suma de todas las fechas)
    fecha_columns = [c for c in df_pivot.columns if re.match(r'^\d{1,2}-\d{1,2}-\d{4}$', str(c))]
    df_pivot['A. TOTAL'] = df_pivot[fecha_columns].sum(axis=1, skipna=True)
    
    return df_pivot


def load_historic_from_db(user_id: int = None, is_admin: bool = False) -> pd.DataFrame:
    """
    Carga histórico MDAT desde PostgreSQL.
    
    Args:
        user_id: ID del usuario (opcional para histórico)
        is_admin: Si es administrador
        
    Returns:
        DataFrame con estructura similar a load_historic_excel:
        Fecha | N° Semana | Empresa | Establecimiento | MDAT
    """
    try:
        from db_connection import execute_query
    except ImportError:
        raise ImportError("Módulo db_connection no disponible")
    
    # CORREGIDO: Usar datos_historicos en lugar de historico_mdat
    query = """
        SELECT 
            fecha as "Fecha",
            semana as "N° Semana",
            establecimiento as "Establecimiento",
            mdat as "MDAT",
            vacas_en_ordena as "Vacas en ordeña"
        FROM datos_historicos
        ORDER BY semana DESC
    """
    
    results = execute_query(query, user_id=user_id, is_admin=is_admin, fetch_all=True)
    
    if not results:
        return pd.DataFrame()
    
    df = pd.DataFrame(results)
    # Convertir columnas numéricas potencialmente en Decimal a float para evitar
    # errores de operaciones con tipos mezclados (Decimal vs float)
    for col in ["MDAT", "Vacas en ordeña"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# ---------------------------------------------------------
# Compatibilidad hacia atrás
# ---------------------------------------------------------
def process_excel(path_or_buffer: Any) -> pd.DataFrame:
    """
    Alias de compatibilidad para código antiguo que hacía:
        from etl import process_excel

    Ahora simplemente delega a load_week_excel(path_or_buffer).
    """
    return load_week_excel(path_or_buffer)


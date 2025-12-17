"""
Excel Processor - Estandarización Excel → Base de Datos
Módulo para procesar reportes semanales e históricos
"""
import pandas as pd
import numpy as np
from datetime import datetime, date
from typing import Dict, List, Tuple, Optional
import re
from db_connection import execute_query, execute_update, get_connection
from psycopg2 import extras

class ExcelProcessor:
    """Procesador de archivos Excel con estandarización robusta"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.stats = {
            'empresas_procesadas': 0,
            'establecimientos_creados': 0,
            'registros_diarios': 0,
            'registros_semanales': 0
        }
    
    # ==============================
    # VALIDACIÓN
    # ==============================
    
    def validate_semanal(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Valida estructura de reporte semanal
        Returns: (is_valid, errors_list)
        """
        errors = []
        
        # Columnas requeridas
        required = ['Empresa_COD', 'Establecimiento', 'CATEGORIA', 'CONCEPTO']
        missing = [col for col in required if col not in df.columns]
        
        if missing:
            errors.append(f"Columnas faltantes: {', '.join(missing)}")
        
        # Verificar que haya columnas de fecha
        date_pattern = re.compile(r'^\d{1,2}-\d{1,2}-\d{4}$')
        date_cols = [col for col in df.columns if date_pattern.match(str(col))]
        
        if not date_cols:
            errors.append("No se encontraron columnas de fecha (formato: dd-mm-yyyy)")
        
        # Validar que haya datos
        if df.empty:
            errors.append("El archivo está vacío")
        
        return (len(errors) == 0, errors)
    
    def validate_historico(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Valida estructura de histórico MDAT
        Returns: (is_valid, errors_list)
        """
        errors = []
        
        # Columnas correctas según el Excel real
        required = ['Empresa', 'N° Semana', '(I) MDAT']
        missing = [col for col in required if col not in df.columns]
        
        if missing:
            errors.append(f"Columnas faltantes: {', '.join(missing)}")
        
        if df.empty:
            errors.append("El archivo está vacío")
        
        return (len(errors) == 0, errors)
    
    # ==============================
    # MAPEO EMPRESA
    # ==============================
    
    def get_empresa_mapping(self) -> Dict[str, int]:
        """
        Obtiene mapeo de código empresa → ID en BD
        Returns: {'96.719.960-5': 1, ...}
        """
        empresas = execute_query("SELECT id, codigo FROM empresas")
        return {e['codigo']: e['id'] for e in empresas}
    
    def get_or_create_empresa(self, codigo: str, nombre: str = None) -> int:
        """
        Obtiene ID de empresa o la crea si no existe
        """
        # Buscar existente
        result = execute_query(
            "SELECT id FROM empresas WHERE codigo = %s",
            (codigo,),
            fetch_one=True
        )
        
        if result:
            return result['id']
        
        # Crear nueva
        if not nombre:
            nombre = f"Empresa {codigo}"
        
        result = execute_query(
            "INSERT INTO empresas (codigo, nombre) VALUES (%s, %s) RETURNING id",
            (codigo, nombre),
            fetch_one=True
        )
        
        self.stats['empresas_procesadas'] += 1
        self.warnings.append(f"Nueva empresa creada: {codigo} - {nombre}")
        
        return result['id']
    
    # ==============================
    # MAPEO ESTABLECIMIENTO
    # ==============================
    
    def get_establecimiento_mapping(self) -> Dict[Tuple[int, str], int]:
        """
        Obtiene mapeo (empresa_id, nombre_establecimiento) → establecimiento_id
        Returns: {(1, 'Eduvigis 2'): 5, ...}
        """
        establecimientos = execute_query(
            "SELECT id, empresa_id, nombre FROM establecimientos"
        )
        return {(e['empresa_id'], e['nombre']): e['id'] for e in establecimientos}
    
    def get_or_create_establecimiento(self, empresa_id: int, nombre: str) -> int:
        """
        Obtiene ID de establecimiento o lo crea
        """
        result = execute_query(
            "SELECT id FROM establecimientos WHERE empresa_id = %s AND nombre = %s",
            (empresa_id, nombre),
            fetch_one=True
        )
        
        if result:
            return result['id']
        
        # Crear nuevo
        result = execute_query(
            "INSERT INTO establecimientos (empresa_id, nombre) VALUES (%s, %s) RETURNING id",
            (empresa_id, nombre),
            fetch_one=True
        )
        
        self.stats['establecimientos_creados'] += 1
        
        return result['id']
    
    # ==============================
    # PROCESAMIENTO SEMANAL
    # ==============================
    
    def process_semanal(self, df: pd.DataFrame, semana: int = None, anio: int = None) -> Dict:
        """
        Procesa reporte semanal completo
        
        Steps:
        1. Validar estructura
        2. Mapear empresas
        3. Crear/obtener establecimientos
        4. Insertar datos_diarios
        5. Agregar datos_semanales
        
        Returns: stats dict con resultados
        """
        self.errors = []
        self.warnings = []
        self.logs = []
        self.stats = {
            'empresas_procesadas': 0,
            'establecimientos_creados': 0,
            'registros_diarios': 0,
            'registros_semanales': 0,
            'registros_omitidos': 0
        }
        
        # Validar
        is_valid, errors = self.validate_semanal(df)
        if not is_valid:
            self.errors.extend(errors)
            self.logs.extend(errors)
            return {'success': False, 'errors': self.errors, 'logs': self.logs}
        
        # Detectar fechas y calcular semana/año si no se proporcionan
        date_pattern = re.compile(r'^\d{1,2}-\d{1,2}-\d{4}$')
        date_cols = [col for col in df.columns if date_pattern.match(str(col))]
        
        if not semana or not anio:
            # Tomar primera fecha para determinar semana
            primera_fecha = pd.to_datetime(date_cols[0], dayfirst=True)
            semana = primera_fecha.isocalendar()[1]
            anio = primera_fecha.year
        
        # Detectar fecha inicio y fin del período
        fechas_dt = [pd.to_datetime(col, dayfirst=True) for col in date_cols]
        fecha_inicio = min(fechas_dt).date()
        fecha_fin = max(fechas_dt).date()
        
        # Mapeos
        empresa_map = self.get_empresa_mapping()
        
        try:
            # Batch de datos diarios
            batch_diarios = []
            # Mapeo establecimientos (lo vamos construyendo)
            est_map = {}
            # Asegurar 'A. TOTAL' si falta: sumar fechas
            if 'A. TOTAL' not in df.columns:
                try:
                    df['A. TOTAL'] = pd.to_numeric(df[date_cols].apply(pd.to_numeric, errors='coerce').sum(axis=1), errors='coerce')
                except Exception:
                    df['A. TOTAL'] = np.nan

            for idx, row in df.iterrows():
                raw_empresa_cod = str(row['Empresa_COD'])
                empresa_cod = raw_empresa_cod.split('_')[0].strip()
                establecimiento = str(row['Establecimiento'])
                categoria = str(row.get('CATEGORIA', ''))
                concepto = str(row.get('CONCEPTO', ''))

                # Get/create empresa
                if empresa_cod not in empresa_map:
                    empresa_id = self.get_or_create_empresa(empresa_cod)
                    empresa_map[empresa_cod] = empresa_id
                else:
                    empresa_id = empresa_map[empresa_cod]

                # Get/create establecimiento
                est_key = (empresa_id, establecimiento)
                if est_key not in est_map:
                    est_id = self.get_or_create_establecimiento(empresa_id, establecimiento)
                    est_map[est_key] = est_id
                else:
                    est_id = est_map[est_key]

                omitido = False
                omitido_motivo = []
                # Validaciones de omisión (ejemplo: valor NaN, concepto vacío, etc.)
                for date_col in date_cols:
                    valor = row.get(date_col)
                    if pd.isna(valor):
                        omitido = True
                        omitido_motivo.append(f"Valor NaN en fecha {date_col}")
                        continue
                    if not concepto:
                        omitido = True
                        omitido_motivo.append("Concepto vacío")
                        continue
                    try:
                        fecha = pd.to_datetime(date_col, dayfirst=True).date()
                        batch_diarios.append((
                            est_id, empresa_id, fecha, categoria, concepto, float(valor)
                        ))
                    except Exception as ex:
                        omitido = True
                        omitido_motivo.append(f"Error en fecha {date_col}: {ex}")
                        continue
                if omitido:
                    self.stats['registros_omitidos'] += 1
                    self.logs.append(f"Fila {idx+1} omitida: Empresa={empresa_cod}, Establecimiento={establecimiento}, Concepto={concepto}, Motivo={' | '.join(omitido_motivo)}")
            
            # Insertar datos diarios en batch
            if batch_diarios:
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        extras.execute_batch(cur, """
                            INSERT INTO datos_diarios (establecimiento_id, empresa_id, fecha, categoria, concepto, valor)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT (establecimiento_id, fecha, concepto) DO UPDATE
                            SET valor = EXCLUDED.valor
                        """, batch_diarios, page_size=1000)
                        conn.commit()
                self.stats['registros_diarios'] = len(batch_diarios)

            # Agregar datos semanales
            semanales_count = self._aggregate_to_semanal(df, semana, anio, est_map, fecha_inicio, fecha_fin)
            self.stats['registros_semanales'] = semanales_count

            return {
                'success': True,
                'stats': self.stats,
                'warnings': self.warnings,
                'logs': self.logs
            }
            
        except Exception as e:
            self.errors.append(f"Error en procesamiento: {str(e)}")
            self.logs.append(f"Error en procesamiento: {str(e)}")
            return {'success': False, 'errors': self.errors, 'logs': self.logs}
    
    def _aggregate_to_semanal(self, df_original: pd.DataFrame, semana: int, anio: int, est_map: Dict, fecha_inicio: 'date' = None, fecha_fin: 'date' = None) -> int:
        """
        Copia datos de Excel → semanales sin cálculos.
        
        Los valores en 'A. TOTAL' ya están agregados en el Excel.
        Solo guardamos lo que viene del archivo sin procesamiento.
        
        Args:
            df_original: DataFrame del Excel
            semana: Número de semana ISO (puede ser None)
            anio: Año (puede ser None)
            est_map: Mapeo de establecimientos
            fecha_inicio: Fecha de inicio del período (nueva)
            fecha_fin: Fecha de fin del período (nueva)
        
        Mapeo de conceptos Excel → columnas BD:
        Los conceptos vienen con prefijo (A), (B), etc.
        Usamos contains con el texto relevante (sin el prefijo de letra).
        """
        # Mapeo: concepto_excel (lowercase, substring) → columna_db
        concepto_map = {
            # Superficie
            'superficie': 'superficie_pradera',
            
            # Vacas (con variantes por encoding)
            'vacas en orde': 'vacas_en_ordena',  # Captura encoding corrupto
            'vacas masa': 'vacas_masa',
            
            # Producción promedio (ESPECÍFICO: buscar "promedio" para evitar "Producción total")
            'promedio': 'produccion_promedio',  # Captura solo "Producción promedio", no "total"
            
            # Precio de la leche
            'precio de la leche': 'precio_leche',
            
            # Calidad (grasa y proteína)
            'porcentaje de grasa': 'porcentaje_grasa',
            '% de grasa': 'porcentaje_grasa',
            'proteinas': 'proteinas',
            
            # Materia seca (MS) por vaca - del Excel
            'kg ms pradera / vaca': 'kg_ms_pradera_vaca',
            'kg ms concentrado / vaca': 'kg_ms_concentrado_vaca',
            'kg ms conservado / vaca': 'kg_ms_conservado_vaca',
            'kg ms verde / vaca': 'kg_ms_verde_vaca',
            'total ms': 'total_ms',
            # Si quieres guardar 'mat. seca por ha' o 'consumo de mat. seca', usa columnas separadas en la BD
            # 'mat. seca por ha': 'mat_seca_por_ha',
            # 'consumo de mat. seca': 'consumo_mat_seca',
            
            # Costos (con variantes por encoding)
            'costo raci': 'costo_racion_vaca',
            'costo promedio concentrado': 'costo_promedio_concentrado',
            'grms concentrado / ltr leche': 'grms_concentrado_por_litro',
            
            # MDAT
            ') mdat': 'mdat',
            'mdat (l/vaca': 'mdat_litros_vaca_dia',
            
            # Porcentaje costo alimentos
            'porcentaje costo alimentos': 'porcentaje_costo_alimentos',
        }
        
        count = 0
        conceptos_no_mapeados = set()
        
        # Verificar que tenemos la columna A. TOTAL
        has_a_total = 'A. TOTAL' in df_original.columns

        for (empresa_id, est_nombre), est_id in est_map.items():
            valores = {}  # columna_db → valor único
            pradera_val = None
            verde_val = None
            df_est = df_original[df_original['Establecimiento'].astype(str).str.strip() == str(est_nombre).strip()].copy()
            if df_est.empty:
                continue

            # Normalizar conceptos a lowercase para matching
            df_est['__concepto_norm'] = df_est['CONCEPTO'].astype(str).str.lower()

            for concepto_excel, columna_db in concepto_map.items():
                mask = df_est['__concepto_norm'].str.contains(concepto_excel.lower(), na=False, regex=False)
                sub = df_est[mask]
                val_final = None
                if not sub.empty:
                    # Tomar A. TOTAL si existe
                    if has_a_total and 'A. TOTAL' in sub.columns:
                        vals = pd.to_numeric(sub['A. TOTAL'], errors='coerce').dropna()
                        if len(vals) > 0:
                            val_final = float(vals.mean())
                        else:
                            # Si no hay A. TOTAL pero hay días, promediar días
                            date_pattern = re.compile(r'^\d{1,2}-\d{1,2}-\d{4}$')
                            date_cols = [col for col in sub.columns if date_pattern.match(str(col))]
                            if date_cols:
                                vals = pd.to_numeric(sub[date_cols].values.flatten(), errors='coerce')
                                vals = pd.Series(vals).dropna()
                                val_final = float(vals.mean()) if len(vals) > 0 else None
                    else:
                        # Si no hay fila, buscar días en el df_est
                        date_pattern = re.compile(r'^\d{1,2}-\d{1,2}-\d{4}$')
                        date_cols = [col for col in df_est.columns if date_pattern.match(str(col))]
                        if date_cols:
                            vals = pd.to_numeric(df_est[date_cols].values.flatten(), errors='coerce')
                            vals = pd.Series(vals).dropna()
                            val_final = float(vals.mean()) if len(vals) > 0 else None

                # Guardar el valor real, solo redondear a 2 decimales
                if val_final is not None:
                    val_final = round(val_final, 2)
                    # Guardar temporalmente para suma
                    if columna_db == 'kg_ms_pradera_vaca':
                        pradera_val = val_final
                    elif columna_db == 'kg_ms_verde_vaca':
                        verde_val = val_final
                    else:
                        valores[columna_db] = val_final

            # Detectar conceptos no mapeados en este establecimiento
            for concepto in df_est['__concepto_norm'].unique():
                mapeado = any(pattern in concepto for pattern in concepto_map.keys())
                if not mapeado:
                    conceptos_no_mapeados.add(concepto)
                    self.logs.append(f"Concepto no mapeado: '{concepto}' en establecimiento '{est_nombre}'")

            # Sumar pradera + verde para praderas_otros_verdes
            if pradera_val is not None or verde_val is not None:
                suma = (pradera_val or 0) + (verde_val or 0)
                valores['praderas_otros_verdes'] = round(suma, 2)

            if valores:
                cols = ['establecimiento_id', 'empresa_id', 'semana', 'anio', 'fecha_inicio', 'fecha_fin'] + list(valores.keys())
                vals = [est_id, empresa_id, semana, anio, fecha_inicio, fecha_fin] + list(valores.values())
                placeholders = ', '.join(['%s'] * len(cols))
                execute_update(f"""
                    INSERT INTO datos_semanales ({', '.join(cols)})
                    VALUES ({placeholders})
                    ON CONFLICT (establecimiento_id, semana, anio) DO UPDATE
                    SET {', '.join([f'{col} = EXCLUDED.{col}' for col in valores.keys()] + ['fecha_inicio = EXCLUDED.fecha_inicio', 'fecha_fin = EXCLUDED.fecha_fin'])}
                """, tuple(vals))
                count += 1
                
                # NUEVO: Si tenemos superficie, actualizar también en la tabla establecimientos
                # para que esté disponible como dato maestro
                if 'superficie_pradera' in valores and valores['superficie_pradera'] is not None:
                    superficie_val = valores['superficie_pradera']
                    execute_update("""
                        UPDATE establecimientos 
                        SET superficie_praderas = %s 
                        WHERE id = %s
                    """, (superficie_val, est_id))
                    self.logs.append(f"Superficie actualizada para '{est_nombre}': {superficie_val} ha")

        return count

    # ==============================
    # PREVIEW SEMANAL (sin persistir)
    # ==============================
    def preview_semanal(self, df: pd.DataFrame) -> Dict:
        """Genera vista previa de la matriz semanal sin escribir en BD.

        Devuelve dict con: semana, anio, df_long (normalizado), df_matrix (matriz final).
        Acepta un DataFrame ya leído con pd.read_excel().
        """
        try:
            # Detectar semana/año igual que en process_semanal
            date_pattern = re.compile(r'^\d{1,2}-\d{1,2}-\d{4}$')
            date_cols = [col for col in df.columns if date_pattern.match(str(col))]
            if not date_cols:
                return {'success': False, 'errors': ['No se detectaron columnas de fecha para preview']}
            primera_fecha = pd.to_datetime(date_cols[0], dayfirst=True)
            semana = primera_fecha.isocalendar()[1]
            anio = primera_fecha.year
            # Transformar el DataFrame al formato largo usando la misma lógica de load_week_excel
            # pero pasando el DataFrame directamente (no un archivo)
            from etl import _normalize_col, _normalize_number, _clean_concept, normalize_est_name
            from matrix_builder import build_matrix
            
            # Normalizar columnas
            df_copy = df.copy()
            df_copy.columns = [_normalize_col(c) for c in df_copy.columns]
            
            # Mapear columnas
            col_map = {}
            if "empresa" in df_copy.columns:
                col_map["empresa"] = "empresa"
            if "empresa_cod" in df_copy.columns:
                col_map["empresa_cod"] = "empresa_cod"
            if "establecimiento" in df_copy.columns:
                col_map["establecimiento"] = "establecimiento"
            if "concepto" in df_copy.columns:
                col_map["concepto"] = "concepto"
            if "a_total" in df_copy.columns:
                col_map["a_total"] = "a_total"
            if "categoria" in df_copy.columns:
                col_map["categoria"] = "categoria"
            
            df_copy = df_copy.rename(columns=col_map)
            
            # Validar columnas mínimas
            for col in ["empresa", "establecimiento", "concepto", "a_total"]:
                if col not in df_copy.columns:
                    return {'success': False, 'errors': [f"Columna '{col}' no encontrada en el archivo"]}
            
            if "empresa_cod" not in df_copy.columns:
                df_copy["empresa_cod"] = df_copy["empresa"]
            
            # Limpiar conceptos
            df_copy["concepto"] = df_copy["concepto"].apply(_clean_concept)
            
            # Normalizar A. TOTAL a float
            df_copy["a_total"] = df_copy["a_total"].apply(_normalize_number)
            
            # Limpiar texto
            df_copy["establecimiento"] = df_copy["establecimiento"].astype(str).str.strip().apply(normalize_est_name)
            df_copy["empresa"] = df_copy["empresa"].astype(str).str.strip()
            df_copy["empresa_cod"] = df_copy["empresa_cod"].astype(str).str.strip()
            
            # Renombrar a formato final
            rename_dict = {
                "empresa": "Empresa",
                "empresa_cod": "Empresa_COD",
                "establecimiento": "Establecimiento",
                "concepto": "CONCEPTO",
                "a_total": "A. TOTAL",
            }
            df_long = df_copy.rename(columns=rename_dict)

            # Agregar N° Semana
            df_long["N° Semana"] = semana

            # --- Parche: asegurar fila MDAT si hay días pero no fila ---
            mdat_names = [
                "MDAT (L/vaca/día)",
                "mdat (l/vaca/día)",
                "mdat (l/vaca/dia)",
                "mdat_litros_vaca_dia",
                "mdat"
            ]
            for est in df_long["Establecimiento"].unique():
                df_est = df_long[df_long["Establecimiento"] == est]
                if not any(df_est["CONCEPTO"].str.lower().str.contains("mdat")):
                    # Buscar en el DataFrame original si hay columnas de días para ese establecimiento
                    df_est_orig = df_copy[df_copy["establecimiento"] == est]
                    date_pattern = re.compile(r'^\d{1,2}-\d{1,2}-\d{4}$')
                    date_cols = [col for col in df_est_orig.columns if date_pattern.match(str(col))]
                    if date_cols:
                        # Si hay datos diarios, calcular promedio fila a fila y agregar fila MDAT
                        vals = pd.to_numeric(df_est_orig[date_cols].values.flatten(), errors="coerce")
                        vals = pd.Series(vals).dropna()
                        if len(vals) > 0:
                            avg = float(vals.mean())
                            new_row = {
                                "Empresa": df_est_orig["empresa"].iloc[0] if "empresa" in df_est_orig.columns else None,
                                "Empresa_COD": df_est_orig["empresa_cod"].iloc[0] if "empresa_cod" in df_est_orig.columns else None,
                                "Establecimiento": est,
                                "CONCEPTO": "MDAT (L/vaca/día)",
                                "A. TOTAL": np.nan,
                                "N° Semana": semana
                            }
                            # Insertar la fila
                            df_long = pd.concat([df_long, pd.DataFrame([new_row])], ignore_index=True)

            current_week = semana
            df_matrix = build_matrix(df_long, df_hist=None, current_week=current_week)
            return {
                'success': True,
                'semana': semana,
                'anio': anio,
                'df_long': df_long,
                'df_matrix': df_matrix
            }
        except Exception as e:
            return {'success': False, 'errors': [str(e)]}
    
    # ==============================
    # PROCESAMIENTO HISTÓRICO
    # ==============================
    
    def process_historico(self, df: pd.DataFrame) -> Dict:
        """
        Procesa histórico MDAT con columnas correctas: 'Empresa', '(I) MDAT'
        """
        self.logs = []
        is_valid, errors = self.validate_historico(df)
        if not is_valid:
            self.logs.extend(errors)
            return {'success': False, 'errors': errors, 'logs': self.logs, 'stats': {}}
        
        try:
            # Mapeo de establecimientos por nombre de empresa
            establecimientos = execute_query("""
                SELECT est.id, est.nombre, est.empresa_id, emp.nombre as empresa_nombre
                FROM establecimientos est
                JOIN empresas emp ON est.empresa_id = emp.id
            """)
            
            # Crear mapeo por empresa (tomar primer establecimiento de cada empresa)
            empresa_to_est = {}
            for est in establecimientos:
                from etl import normalize_est_name
                empresa_nom = normalize_est_name(est['empresa_nombre']).lower()
                if empresa_nom not in empresa_to_est:
                    empresa_to_est[empresa_nom] = {
                        'est_id': est['id'],
                        'empresa_id': est['empresa_id']
                    }
            
            inserted = 0
            skipped = 0
            semanas_unicas = set()
            
            for idx, row in df.iterrows():
                from etl import normalize_est_name
                empresa_nombre = normalize_est_name(str(row['Empresa'])).lower()
                
                log_msg = None
                if empresa_nombre not in empresa_to_est:
                    skipped += 1
                    log_msg = f"Fila {idx+1} omitida: Empresa/Establecimiento no encontrado ('{row['Empresa']}')"
                    self.logs.append(log_msg)
                else:
                    est_info = empresa_to_est[empresa_nombre]
                    try:
                        semana = int(row['N° Semana'])
                        anio = int(row.get('Año', datetime.now().year))
                        mdat = float(row['(I) MDAT']) if not pd.isna(row.get('(I) MDAT')) else None
                        vacas = int(row['Vacas en ordeña']) if 'Vacas en ordeña' in row and not pd.isna(row['Vacas en ordeña']) else None
                        
                        if mdat is None:
                            skipped += 1
                            log_msg = f"Fila {idx+1} omitida: MDAT vacío para '{row['Empresa']}' semana {semana}"
                            self.logs.append(log_msg)
                        else:
                            execute_update("""
                                INSERT INTO historico_mdat (establecimiento_id, empresa_id, semana, anio, mdat, vacas_en_ordena)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                ON CONFLICT (establecimiento_id, semana, anio) DO UPDATE
                                SET mdat = EXCLUDED.mdat, vacas_en_ordena = EXCLUDED.vacas_en_ordena
                            """, (est_info['est_id'], est_info['empresa_id'], semana, anio, mdat, vacas))
                            inserted += 1
                            semanas_unicas.add((semana, anio))
                    except Exception as ex:
                        skipped += 1
                        log_msg = f"Fila {idx+1} omitida: Error en procesamiento - {str(ex)}"
                        self.logs.append(log_msg)
            
            return {
                'success': True,
                'stats': {
                    'filas_procesadas': len(df),
                    'filas_insertadas': inserted,
                    'filas_omitidas': skipped,
                    'semanas_unicas': len(semanas_unicas)
                },
                'logs': self.logs
            }
            
        except Exception as e:
            self.logs.append(f"Error en procesamiento: {str(e)}")
            return {'success': False, 'errors': [str(e)], 'logs': self.logs, 'stats': {}}

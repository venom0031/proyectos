"""
Excel Processor - Estandarización Excel → Base de Datos
Módulo para procesar reportes semanales e históricos
"""
import pandas as pd
import numpy as np
from datetime import datetime
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
        self.stats = {
            'empresas_procesadas': 0,
            'establecimientos_creados': 0,
            'registros_diarios': 0,
            'registros_semanales': 0
        }
        
        # Validar
        is_valid, errors = self.validate_semanal(df)
        if not is_valid:
            self.errors.extend(errors)
            return {'success': False, 'errors': self.errors}
        
        # Detectar fechas y calcular semana/año si no se proporcionan
        date_pattern = re.compile(r'^\d{1,2}-\d{1,2}-\d{4}$')
        date_cols = [col for col in df.columns if date_pattern.match(str(col))]
        
        if not semana or not anio:
            # Tomar primera fecha para determinar semana
            primera_fecha = pd.to_datetime(date_cols[0], dayfirst=True)
            semana = primera_fecha.isocalendar()[1]
            anio = primera_fecha.year
        
        # Mapeos
        empresa_map = self.get_empresa_mapping()
        
        try:
            # Batch de datos diarios
            batch_diarios = []
            
            # Mapeo establecimientos (lo vamos construyendo)
            est_map = {}
            
            for _, row in df.iterrows():
                # Limpiar código de empresa (quitar sufijos como _Eduvigis)
                raw_empresa_cod = str(row['Empresa_COD'])
                empresa_cod = raw_empresa_cod.split('_')[0].strip()
                
                establecimiento = str(row['Establecimiento'])
                categoria = str(row.get('CATEGORIA', ''))
                concepto = str(row.get('CONCEPTO', ''))
                
                # Get/create empresa
                if empresa_cod not in empresa_map:
                    # Si no existe, intentar crearla (o reportar)
                    # En este caso, si limpiamos el código y aún no existe, se creará nueva
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
                
                # Procesar cada fecha
                for date_col in date_cols:
                    valor = row.get(date_col)
                    
                    if pd.isna(valor):
                        continue
                    
                    try:
                        fecha = pd.to_datetime(date_col, dayfirst=True).date()
                        batch_diarios.append((
                            est_id, empresa_id, fecha, categoria, concepto, float(valor)
                        ))
                    except:
                        continue
            
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
            # Agregación semanal determinista usando los datos del Excel (no ventana relativa de 7 días)
            semanales_count = self._aggregate_to_semanal(df, semana, anio, est_map)
            self.stats['registros_semanales'] = semanales_count
            
            return {
                'success': True,
                'stats': self.stats,
                'warnings': self.warnings
            }
            
        except Exception as e:
            self.errors.append(f"Error en procesamiento: {str(e)}")
            return {'success': False, 'errors': self.errors}
    
    def _aggregate_to_semanal(self, df_original: pd.DataFrame, semana: int, anio: int, est_map: Dict) -> int:
        """
        Agrega datos diarios → semanales
        
        Mapeo de conceptos:
        - '(A) Vacas en ordeña' → vacas_en_ordena
        - 'Producción bruta' → produccion_promedio
        - 'MDAT $' → mdat
        - etc.
        """
        concepto_map = {
            'vacas en ordeña': 'vacas_en_ordena',
            'vacas masa': 'vacas_masa',
            'producción bruta': 'produccion_promedio',
            'producción promedio': 'produccion_promedio',
            'mdat': 'mdat',
            'mdat $': 'mdat',
            'grasa': 'porcentaje_grasa',
            'proteína': 'proteinas',
        }
        
        count = 0
        
        # Asegurar columnas esperadas
        cols_lower = {c.lower(): c for c in df_original.columns}
        has_a_total = 'a. total' in [c.lower() for c in df_original.columns]

        for (empresa_id, est_nombre), est_id in est_map.items():
            valores = {}
            df_est = df_original[df_original['Establecimiento'].astype(str).str.strip() == str(est_nombre).strip()].copy()
            if df_est.empty:
                continue
            # Usar columna 'A. TOTAL' si existe como base; si no, intentar sumar fechas.
            # Normalización de concepto a lower para matching robusto.
            df_est['__concepto_norm'] = df_est['CONCEPTO'].astype(str).str.lower()
            for concepto_excel, columna_db in concepto_map.items():
                # Buscar filas cuyo concepto contenga el substring concepto_excel
                mask = df_est['__concepto_norm'].str.contains(concepto_excel.lower(), na=False)
                sub = df_est[mask]
                if sub.empty:
                    continue
                try:
                    # Si hay múltiple filas, tomar promedio de A. TOTAL (o suma si no tiene A. TOTAL)
                    if has_a_total and 'A. TOTAL' in sub.columns:
                        val = pd.to_numeric(sub['A. TOTAL'], errors='coerce').dropna().mean()
                    else:
                        # Sumar todas las columnas de fecha detectadas como dd-mm-yyyy
                        date_pattern = re.compile(r'^\d{1,2}-\d{1,2}-\d{4}$')
                        date_cols = [c for c in sub.columns if date_pattern.match(str(c))]
                        if date_cols:
                            numeric_vals = pd.to_numeric(sub[date_cols].values.flatten(), errors='coerce')
                            val = numeric_vals[~np.isnan(numeric_vals)].mean() if numeric_vals.size else None
                        else:
                            val = None
                    if val is not None and not np.isnan(val):
                        valores[columna_db] = float(val)
                except Exception:
                    continue
            if valores:
                cols = ['establecimiento_id', 'empresa_id', 'semana', 'anio'] + list(valores.keys())
                vals = [est_id, empresa_id, semana, anio] + list(valores.values())
                placeholders = ', '.join(['%s'] * len(cols))
                execute_update(f"""
                    INSERT INTO datos_semanales ({', '.join(cols)})
                    VALUES ({placeholders})
                    ON CONFLICT (establecimiento_id, semana, anio) DO UPDATE
                    SET {', '.join([f'{col} = EXCLUDED.{col}' for col in valores.keys()])}
                """, tuple(vals))
                count += 1
        
        return count

    # ==============================
    # PREVIEW SEMANAL (sin persistir)
    # ==============================
    def preview_semanal(self, df: pd.DataFrame) -> Dict:
        """Genera vista previa de la matriz semanal sin escribir en BD.

        Devuelve dict con: semana, anio, df_long (normalizado), df_matrix (matriz final).
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
            # Reusar load_week_excel para generar formato largo
            from etl import load_week_excel
            from matrix_builder import build_matrix
            df_long = load_week_excel(df)
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
        is_valid, errors = self.validate_historico(df)
        if not is_valid:
            return {'success': False, 'errors': errors}
        
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
                empresa_nom = est['empresa_nombre'].strip().lower()
                if empresa_nom not in empresa_to_est:
                    empresa_to_est[empresa_nom] = {
                        'est_id': est['id'],
                        'empresa_id': est['empresa_id']
                    }
            
            inserted = 0
            skipped = 0
            
            for _, row in df.iterrows():
                empresa_nombre = str(row['Empresa']).strip().lower()
                
                if empresa_nombre not in empresa_to_est:
                    skipped += 1
                    continue
                
                est_info = empresa_to_est[empresa_nombre]
                
                semana = int(row['N° Semana'])
                anio = int(row.get('Año', datetime.now().year))
                mdat = float(row['(I) MDAT']) if not pd.isna(row.get('(I) MDAT')) else None
                vacas = int(row['Vacas en ordeña']) if 'Vacas en ordeña' in row and not pd.isna(row['Vacas en ordeña']) else None
                
                if mdat is None:
                    skipped += 1
                    continue
                
                execute_update("""
                    INSERT INTO historico_mdat (establecimiento_id, empresa_id, semana, anio, mdat, vacas_en_ordena)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (establecimiento_id, semana, anio) DO UPDATE
                    SET mdat = EXCLUDED.mdat, vacas_en_ordena = EXCLUDED.vacas_en_ordena
                """, (est_info['est_id'], est_info['empresa_id'], semana, anio, mdat, vacas))
                
                inserted += 1
            
            return {
                'success': True,
                'stats': {'inserted': inserted, 'skipped': skipped}
            }
            
        except Exception as e:
            return {'success': False, 'errors': [str(e)]}

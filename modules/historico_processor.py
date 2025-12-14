"""
Procesador de Histórico Completo
Módulo para cargar y procesar el archivo histórico de datos semanales
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from db_connection import execute_query, execute_update, get_connection
from psycopg2 import extras


class HistoricoProcessor:
    """Procesador para archivos de histórico completo"""
    
    # Mapeo de columnas del Excel histórico a columnas de la BD
    # Basado en el Excel "HISTORICO PERSISTENTE"
    # IMPORTANTE: Los patrones más específicos deben ir PRIMERO para evitar conflictos
    COLUMN_MAP = {
        # Identificadores
        'semana': 'semana',
        'n° semana': 'semana',
        'nâ° semana': 'semana',  # encoding alternativo
        'fecha': 'fecha',
        'establecimiento': 'establecimiento',  # Es el nombre del fundo
        'empresa': 'establecimiento',  # Alias por si viene como "empresa"
        
        # VACAS - Patrones específicos PRIMERO para evitar conflictos
        # "(A) Vacas en ordeña" debe mapear a vacas_en_ordena, NO a vacas_en_produccion
        'vacas en ordeña': 'vacas_en_ordena',    # Match exacto primero
        'vacas en ordena': 'vacas_en_ordena',    # Sin tilde
        'vacas en ord': 'vacas_en_ordena',       # Parcial
        '(a) vacas': 'vacas_en_ordena',          # Con prefijo (A)
        
        # Vacas masa
        'vacas masa': 'vacas_masa',
        
        # Vacas en producción (después de los más específicos)
        'vacas en producción': 'vacas_en_produccion',
        'vacas en produccion': 'vacas_en_produccion',
        'vacas en producci': 'vacas_en_produccion',
        
        # Leche
        'le envían': 'leche_enviada',
        'le envian': 'leche_enviada',
        'leche enviada': 'leche_enviada',
        'che no': 'leche_no_vendible',
        'pna terr': 'pna_terneros',
        'pna tern': 'pna_terneros',
        'producción': 'produccion_total',
        'produccion': 'produccion_total',
        'precio de': 'precio_leche',
        'dias lactancia': 'dias_lactancia',
        'días lactancia': 'dias_lactancia',
        'lactancia': 'dias_lactancia',
        
        # Calidad
        '% grasa': 'porcentaje_grasa',
        'grasa': 'porcentaje_grasa',
        '% prot': 'porcentaje_proteina',
        'proteina': 'porcentaje_proteina',
        'proteínas': 'porcentaje_proteina',
        
        # MS
        'kg ms prad': 'kg_ms_pradera',
        'ms pradera': 'kg_ms_pradera',
        'kg ms cons': 'kg_ms_conservado',
        'ms conserv': 'kg_ms_conservado',
        'kg ms conc': 'kg_ms_concentrado',
        'ms concent': 'kg_ms_concentrado',
        'consumo ms': 'consumo_ms',
        'ms var': 'consumo_ms',
        'ms por ha': 'ms_por_ha',
        'ms/ha': 'ms_por_ha',
        
        # Costos
        'taje leche': 'costo_racion_vaca',
        'costo raci': 'costo_racion_vaca',
        
        # MDAT
        'mdat': 'mdat',
        '(i) mdat': 'mdat',
        
        # Eficiencia
        'eficie': 'eficiencia',
        'eficiencia': 'eficiencia',
        
        # Relaciones
        'centaje c': 'relacion_ordena_masa',
        
        # Superficie
        'superficie': 'superficie_praderas',
        
        # Otros
        '% leche no': 'porcentaje_leche_no_vendible',
    }
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.stats = {
            'filas_procesadas': 0,
            'filas_insertadas': 0,
            'filas_actualizadas': 0,
            'filas_omitidas': 0,
            'semanas_unicas': 0,
            'empresas_unicas': 0
        }
    
    def _normalize_column_name(self, col: str) -> str:
        """Normaliza nombre de columna para matching"""
        if not col:
            return ""
        col = str(col).lower().strip()
        # Quitar caracteres especiales de encoding
        col = col.replace('â', 'a').replace('ã', 'a').replace('ñ', 'n')
        col = col.replace('°', '').replace('º', '')
        return col
    
    def _map_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Mapea columnas del Excel a columnas de BD
        Returns: dict con {columna_excel: columna_bd}
        """
        mapping = {}
        
        for excel_col in df.columns:
            excel_col_norm = self._normalize_column_name(excel_col)
            
            for pattern, db_col in self.COLUMN_MAP.items():
                if pattern in excel_col_norm:
                    mapping[excel_col] = db_col
                    break
        
        return mapping
    
    def validate_historico(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """Valida estructura del archivo histórico"""
        errors = []
        
        # Verificar columnas esenciales
        col_mapping = self._map_columns(df)
        
        # Solo requerimos semana y establecimiento (fecha es opcional, se calcula si falta)
        required_fields = ['semana', 'establecimiento']
        mapped_fields = set(col_mapping.values())
        
        missing = [f for f in required_fields if f not in mapped_fields]
        if missing:
            errors.append(f"Columnas requeridas no encontradas: {', '.join(missing)}")
            errors.append(f"Columnas detectadas en el archivo: {list(df.columns[:10])}...")
            errors.append(f"Columnas mapeadas: {list(col_mapping.keys())}")
        
        if df.empty:
            errors.append("El archivo está vacío")
        
        return (len(errors) == 0, errors)
    
    def get_semanas_disponibles(self) -> List[Dict]:
        """
        Obtiene lista de semanas disponibles en el histórico
        Returns: [{semana, fecha, registros}, ...]
        """
        query = """
            SELECT 
                semana,
                fecha,
                COUNT(*) as registros,
                COUNT(DISTINCT empresa) as empresas
            FROM datos_historicos
            GROUP BY semana, fecha
            ORDER BY fecha DESC
        """
        return execute_query(query)
    
    def get_datos_semana(self, semana: int = None, fecha: str = None) -> pd.DataFrame:
        """
        Obtiene datos de una semana específica
        Args:
            semana: Número de semana
            fecha: Fecha de cierre (formato: YYYY-MM-DD)
        Returns: DataFrame con los datos
        """
        if fecha:
            query = """
                SELECT * FROM datos_historicos
                WHERE fecha = %s
                ORDER BY empresa, establecimiento
            """
            params = (fecha,)
        elif semana:
            query = """
                SELECT * FROM datos_historicos
                WHERE semana = %s
                ORDER BY fecha DESC, empresa, establecimiento
            """
            params = (semana,)
        else:
            return pd.DataFrame()
        
        results = execute_query(query, params)
        return pd.DataFrame(results) if results else pd.DataFrame()
    
    def process_historico(self, df: pd.DataFrame) -> Dict:
        """
        Procesa y carga archivo histórico completo
        
        Args:
            df: DataFrame del Excel histórico
            
        Returns:
            Dict con resultado del procesamiento
        """
        self.errors = []
        self.warnings = []
        self.logs = []
        self.stats = {
            'filas_procesadas': 0,
            'filas_insertadas': 0,
            'filas_actualizadas': 0,
            'filas_omitidas': 0,
            'semanas_unicas': set(),
            'empresas_unicas': set()
        }
        
        # Validar
        is_valid, errors = self.validate_historico(df)
        if not is_valid:
            self.errors.extend(errors)
            self.logs.extend(errors)
            return {'success': False, 'errors': self.errors, 'logs': self.logs, 'stats': {}}
        
        # Mapear columnas
        col_mapping = self._map_columns(df)
        
        # Mostrar mapeo detectado
        self.warnings.append(f"Columnas mapeadas: {len(col_mapping)}")
        for excel_col, db_col in col_mapping.items():
            self.warnings.append(f"  '{excel_col}' → {db_col}")
        
        try:
            # Primera pasada: calcular fecha más común por semana (para filas sin fecha)
            fechas_por_semana = {}
            for _, row in df.iterrows():
                record = {}
                for excel_col, db_col in col_mapping.items():
                    val = row.get(excel_col)
                    if pd.notna(val):
                        record[db_col] = val
                
                if 'semana' in record and 'fecha' in record:
                    semana = int(record['semana'])
                    try:
                        if isinstance(record['fecha'], str):
                            fecha = pd.to_datetime(record['fecha'], dayfirst=True).date()
                        else:
                            fecha = pd.to_datetime(record['fecha']).date()
                        
                        if semana not in fechas_por_semana:
                            fechas_por_semana[semana] = {}
                        if fecha not in fechas_por_semana[semana]:
                            fechas_por_semana[semana][fecha] = 0
                        fechas_por_semana[semana][fecha] += 1
                    except:
                        pass
            
            # Determinar fecha más común por semana
            fecha_default_por_semana = {}
            for semana, fechas in fechas_por_semana.items():
                if fechas:
                    fecha_default_por_semana[semana] = max(fechas, key=fechas.get)
            
            batch_data = []
            
            for idx, row in df.iterrows():
                self.stats['filas_procesadas'] += 1
                
                # Extraer datos mapeados
                record = {}
                for excel_col, db_col in col_mapping.items():
                    val = row.get(excel_col)
                    if pd.notna(val):
                        record[db_col] = val
                
                # Validar campos requeridos: semana y establecimiento son obligatorios
                # La fecha ya no es obligatoria - usamos la más común de la semana si falta
                if 'semana' not in record or 'establecimiento' not in record:
                    self.stats['filas_omitidas'] += 1
                    razon = []
                    if 'semana' not in record:
                        razon.append("Semana vacía")
                    if 'establecimiento' not in record:
                        razon.append("Establecimiento vacío")
                    self.logs.append(f"Fila {idx+1} omitida: {' | '.join(razon)}")
                    continue
                
                semana = int(record['semana'])
                
                # Normalizar fecha (si existe) o usar la más común de la semana
                fecha = None
                if 'fecha' in record:
                    try:
                        if isinstance(record['fecha'], str):
                            fecha = pd.to_datetime(record['fecha'], dayfirst=True).date()
                        else:
                            fecha = pd.to_datetime(record['fecha']).date()
                    except:
                        pass
                
                # Si no hay fecha, usar la más común de esa semana o una fecha genérica
                if fecha is None:
                    fecha = fecha_default_por_semana.get(semana)
                    if fecha is None:
                        # Última opción: generar fecha basada en semana (primer día de 2025)
                        from datetime import date, timedelta
                        fecha = date(2025, 1, 1) + timedelta(weeks=semana-1)
                
                establecimiento = str(record['establecimiento']).strip()
                
                self.stats['semanas_unicas'].add(semana)
                self.stats['empresas_unicas'].add(establecimiento)
                
                # Construir tupla para insert (sin campo empresa, solo establecimiento)
                batch_data.append((
                    semana,
                    fecha,
                    establecimiento,
                    self._safe_int(record.get('vacas_en_produccion')),
                    self._safe_float(record.get('leche_enviada')),
                    self._safe_float(record.get('leche_no_vendible')),
                    self._safe_float(record.get('pna_terneros')),
                    self._safe_float(record.get('produccion_total')),
                    self._safe_float(record.get('precio_leche')),
                    self._safe_int(record.get('dias_lactancia')),
                    self._safe_float(record.get('porcentaje_grasa')),
                    self._safe_float(record.get('porcentaje_proteina')),
                    self._safe_float(record.get('kg_ms_pradera')),
                    self._safe_float(record.get('kg_ms_conservado')),
                    self._safe_float(record.get('kg_ms_concentrado')),
                    self._safe_float(record.get('consumo_ms')),
                    self._safe_float(record.get('ms_por_ha')),
                    self._safe_float(record.get('costo_racion_vaca')),
                    self._safe_float(record.get('mdat')),
                    self._safe_float(record.get('eficiencia')),
                    self._safe_int(record.get('vacas_masa')),
                    self._safe_int(record.get('vacas_en_ordena')),
                    self._safe_float(record.get('relacion_ordena_masa')),
                    self._safe_float(record.get('superficie_praderas')),
                    self._safe_float(record.get('porcentaje_leche_no_vendible')),
                    self._safe_float(record.get('carga_animal')),
                ))
            
            # Insertar en batch
            if batch_data:
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        extras.execute_batch(cur, """
                            INSERT INTO datos_historicos (
                                semana, fecha, establecimiento,
                                vacas_en_produccion, leche_enviada, leche_no_vendible, pna_terneros,
                                produccion_total, precio_leche, dias_lactancia,
                                porcentaje_grasa, porcentaje_proteina,
                                kg_ms_pradera, kg_ms_conservado, kg_ms_concentrado, consumo_ms, ms_por_ha,
                                costo_racion_vaca, mdat, eficiencia,
                                vacas_masa, vacas_en_ordena, relacion_ordena_masa,
                                superficie_praderas, porcentaje_leche_no_vendible, carga_animal
                            ) VALUES (
                                %s, %s, %s,
                                %s, %s, %s, %s,
                                %s, %s, %s,
                                %s, %s,
                                %s, %s, %s, %s, %s,
                                %s, %s, %s,
                                %s, %s, %s,
                                %s, %s, %s
                            )
                            ON CONFLICT (semana, establecimiento) DO UPDATE SET
                                fecha = EXCLUDED.fecha,
                                vacas_en_produccion = EXCLUDED.vacas_en_produccion,
                                leche_enviada = EXCLUDED.leche_enviada,
                                leche_no_vendible = EXCLUDED.leche_no_vendible,
                                pna_terneros = EXCLUDED.pna_terneros,
                                produccion_total = EXCLUDED.produccion_total,
                                precio_leche = EXCLUDED.precio_leche,
                                dias_lactancia = EXCLUDED.dias_lactancia,
                                porcentaje_grasa = EXCLUDED.porcentaje_grasa,
                                porcentaje_proteina = EXCLUDED.porcentaje_proteina,
                                kg_ms_pradera = EXCLUDED.kg_ms_pradera,
                                kg_ms_conservado = EXCLUDED.kg_ms_conservado,
                                kg_ms_concentrado = EXCLUDED.kg_ms_concentrado,
                                consumo_ms = EXCLUDED.consumo_ms,
                                ms_por_ha = EXCLUDED.ms_por_ha,
                                costo_racion_vaca = EXCLUDED.costo_racion_vaca,
                                mdat = EXCLUDED.mdat,
                                eficiencia = EXCLUDED.eficiencia,
                                vacas_masa = EXCLUDED.vacas_masa,
                                vacas_en_ordena = EXCLUDED.vacas_en_ordena,
                                relacion_ordena_masa = EXCLUDED.relacion_ordena_masa,
                                superficie_praderas = EXCLUDED.superficie_praderas,
                                porcentaje_leche_no_vendible = EXCLUDED.porcentaje_leche_no_vendible,
                                carga_animal = EXCLUDED.carga_animal
                        """, batch_data, page_size=500)
                        conn.commit()
                
                self.stats['filas_insertadas'] = len(batch_data)
            
            # Convertir sets a counts para el resultado
            result_stats = {
                'filas_procesadas': self.stats['filas_procesadas'],
                'filas_insertadas': self.stats['filas_insertadas'],
                'filas_omitidas': self.stats['filas_omitidas'],
                'semanas_unicas': len(self.stats['semanas_unicas']),
                'empresas_unicas': len(self.stats['empresas_unicas'])
            }
            
            return {
                'success': True,
                'stats': result_stats,
                'warnings': self.warnings,
                'logs': self.logs
            }
            
        except Exception as e:
            self.errors.append(f"Error en procesamiento: {str(e)}")
            import traceback
            self.errors.append(traceback.format_exc())
            self.logs.extend(self.errors)
            return {'success': False, 'errors': self.errors, 'logs': self.logs}
    
    def _safe_float(self, val) -> Optional[float]:
        """Convierte a float de forma segura"""
        if val is None or pd.isna(val):
            return None
        try:
            return float(val)
        except:
            return None
    
    def _safe_int(self, val) -> Optional[int]:
        """Convierte a int de forma segura"""
        if val is None or pd.isna(val):
            return None
        try:
            return int(float(val))
        except:
            return None
    
    def get_historico_for_matrix(self, empresa: str = None, semanas_atras: int = 52) -> pd.DataFrame:
        """
        Obtiene datos históricos para cálculo de promedios en la matriz
        
        Args:
            empresa: Filtrar por empresa (opcional)
            semanas_atras: Cuántas semanas hacia atrás obtener
            
        Returns:
            DataFrame con histórico para la matriz
        """
        query = """
            SELECT 
                semana as "N° Semana",
                fecha,
                empresa as "Empresa",
                establecimiento as "Establecimiento",
                mdat as "MDAT",
                vacas_en_ordena as "Vacas en ordeña",
                produccion_total as "Producción promedio",
                precio_leche as "Precio de la leche",
                costo_racion_vaca as "Costo ración vaca"
            FROM datos_historicos
            WHERE fecha >= CURRENT_DATE - INTERVAL '%s weeks'
        """
        params = [semanas_atras]
        
        if empresa:
            query += " AND LOWER(empresa) = LOWER(%s)"
            params.append(empresa)
        
        query += " ORDER BY fecha DESC, empresa"
        
        results = execute_query(query, tuple(params))
        return pd.DataFrame(results) if results else pd.DataFrame()
    
    def calcular_promedios_historicos(self, establecimiento: str, semana_actual: int, fecha_actual) -> Dict:
        """
        Calcula promedios de 4 semanas y 52 semanas para un establecimiento
        
        Args:
            establecimiento: Nombre del establecimiento
            semana_actual: Semana actual del reporte
            fecha_actual: Fecha de cierre del período actual
            
        Returns:
            Dict con mdat_4sem, vacas_4sem, mdat_52sem, vacas_52sem
        """
        # Obtener histórico del establecimiento
        query = """
            SELECT 
                semana,
                fecha,
                mdat,
                vacas_en_ordena
            FROM datos_historicos
            WHERE LOWER(establecimiento) = LOWER(%s)
              AND fecha < %s
            ORDER BY fecha DESC
        """
        
        results = execute_query(query, (establecimiento, fecha_actual))
        
        if not results:
            return {
                'mdat_4sem': None,
                'vacas_4sem': None,
                'mdat_52sem': None,
                'vacas_52sem': None
            }
        
        df = pd.DataFrame(results)
        
        # Últimas 4 semanas (excluyendo actual)
        df_4sem = df.head(4)
        # Últimas 52 semanas
        df_52sem = df.head(52)
        
        # Calcular promedios (según lógica DAX: SUM / N fijo)
        mdat_4sem = df_4sem['mdat'].sum() / 4 if len(df_4sem) > 0 else None
        vacas_4sem = df_4sem['vacas_en_ordena'].sum() / 4 if len(df_4sem) > 0 else None
        
        mdat_52sem = df_52sem['mdat'].sum() / 52 if len(df_52sem) > 0 else None
        vacas_52sem = df_52sem['vacas_en_ordena'].sum() / 52 if len(df_52sem) > 0 else None
        
        return {
            'mdat_4sem': mdat_4sem,
            'vacas_4sem': vacas_4sem,
            'mdat_52sem': mdat_52sem,
            'vacas_52sem': vacas_52sem
        }


# Función helper para uso directo
def load_historico_excel(file_path: str) -> Dict:
    """
    Carga un archivo Excel histórico
    
    Args:
        file_path: Ruta al archivo Excel
        
    Returns:
        Dict con resultado del procesamiento
    """
    processor = HistoricoProcessor()
    df = pd.read_excel(file_path)
    return processor.process_historico(df)

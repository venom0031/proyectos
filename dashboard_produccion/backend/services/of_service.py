"""
Servicio para gestión de Órdenes de Fabricación
"""
from typing import List, Dict
from datetime import datetime
from fastapi import HTTPException

from backend.core.odoo_connection import odoo
from backend.utils.helpers import clean_record


class OFService:
    """Servicio para operaciones de Órdenes de Fabricación"""
    
    def search_ofs(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Busca órdenes de fabricación por rango de fechas
        
        Args:
            start_date: Fecha de inicio (formato: YYYY-MM-DD)
            end_date: Fecha de fin (formato: YYYY-MM-DD)
        
        Returns:
            Lista de órdenes de fabricación
        """
        uid, models = odoo.connect()
        
        domain = [
            ("date_planned_start", ">=", start_date),
            ("date_planned_start", "<=", end_date)
        ]
        
        ids = odoo.execute_kw(
            "mrp.production", "search",
            [domain]
        )
        
        if not ids:
            return []
        
        ofs = odoo.execute_kw(
            "mrp.production", "read",
            [ids],
            {"fields": ["id", "name", "date_planned_start", "product_id"]}
        )
        
        return [clean_record(of) for of in ofs]
    
    def get_of_detail(self, of_id: int) -> Dict:
        """
        Obtiene el detalle completo de una orden de fabricación
        
        Args:
            of_id: ID de la orden de fabricación
        
        Returns:
            Diccionario con todos los datos de la OF y KPIs calculados
        """
        uid, models = odoo.connect()
        
        # Campos básicos que siempre existen
        basic_fields = [
            "name", "product_id", "product_qty", "qty_produced", "user_id",
            "date_planned_start", "date_start", "date_finished", "state", 
            "company_id", "move_raw_ids", "move_finished_ids"
        ]
        
        # Campos personalizados - verificar cuáles existen
        custom_fields_to_try = [
            "x_studio_cantidad_consumida", "x_studio_kghh_efectiva", 
            "x_studio_kghora_efectiva", "x_studio_horas_detencion_totales",
            "x_studio_dotacin", "x_studio_merma_bolsas",
            "x_studio_odf_es_para_una_po_en_particular", "x_studio_nmero_de_po_1",
            "x_studio_clientes", "x_studio_po_asociada", "x_studio_kg_totales_po",
            "x_studio_kg_consumidos_po", "x_studio_kg_disponibles_po",
            "x_studio_inicio_de_proceso", "x_studio_termino_de_proceso",
            "x_studio_hh", "x_studio_hh_efectiva", "x_studio_sala_de_proceso",
            "x_detenciones_id", "x_studio_one2many_field_edeem"
        ]
        
        # Primero intentar obtener los campos disponibles del modelo
        available_custom_fields = []
        try:
            # Obtener metadatos del modelo para saber qué campos existen
            fields_info = odoo.execute_kw(
                "mrp.production", "fields_get",
                [],
                {"attributes": ["string", "type"]}
            )
            available_field_names = set(fields_info.keys())
            
            # Filtrar solo los campos custom que existen
            available_custom_fields = [f for f in custom_fields_to_try if f in available_field_names]
            print(f"Available custom fields: {len(available_custom_fields)}/{len(custom_fields_to_try)}")
        except Exception as e:
            print(f"Could not get field metadata: {e}")
            # Si no podemos obtener los metadatos, intentar con todos y manejar el error
            available_custom_fields = custom_fields_to_try
        
        # Construir lista de campos
        fields = basic_fields + available_custom_fields
        
        # Intentar obtener la OF con los campos disponibles
        try:
            result = odoo.execute_kw(
                "mrp.production", "read",
                [[of_id]], {"fields": fields}
            )
        except Exception as e:
            # Si aún falla, usar solo campos básicos
            print(f"Warning: Error loading fields, using basic fields only: {e}")
            result = odoo.execute_kw(
                "mrp.production", "read",
                [[of_id]], {"fields": basic_fields}
            )
        
        if not result:
            raise HTTPException(status_code=404, detail="Orden de Fabricación no encontrada")
        
        of_raw = result[0]
        of = clean_record(of_raw)
        
        # Obtener datos complementarios (solo si existen los campos)
        componentes = self._get_lines_detail(of_raw.get("move_raw_ids", []))
        subproductos_raw = self._get_lines_detail(of_raw.get("move_finished_ids", []))
        subproductos = self._filter_subproductos(subproductos_raw)
        detenciones = self._get_detenciones(of_raw.get("x_detenciones_id", []))
        consumo = self._get_consumo(
            of_raw.get("x_studio_one2many_field_edeem", []),
            componentes,
            subproductos
        )
        
        # Calcular KPIs
        kpis = self._calculate_kpis(of, componentes, subproductos)
        
        return {
            "of": of,
            "componentes": componentes,
            "subproductos": subproductos,
            "detenciones": detenciones,
            "consumo": consumo,
            "kpis": kpis
        }
    
    def _get_lines_detail(self, move_ids: List[int]) -> List[Dict]:
        """Obtiene el detalle de líneas de movimiento (lotes, pallets, ubicaciones)"""
        if not move_ids:
            return []
        
        line_ids = odoo.execute_kw(
            "stock.move.line", "search",
            [[("move_id", "in", move_ids)]]
        )
        
        if not line_ids:
            return []
        
        lines_raw = odoo.execute_kw(
            "stock.move.line", "read",
            [line_ids],
            {"fields": [
                "product_id", "lot_id", "result_package_id", "package_id",
                "qty_done", "location_id", "location_dest_id", "product_category_name"
            ]}
        )
        
        return [clean_record(x) for x in lines_raw]
    
    def _filter_subproductos(self, subproductos_raw: List[Dict]) -> List[Dict]:
        """Filtra subproductos excluyendo 'Proceso Retail'"""
        subproductos = []
        
        for sub in subproductos_raw:
            prod_name = sub.get("product_id", {}).get("name", "") if isinstance(sub.get("product_id"), dict) else ""
            
            # Excluir "Proceso Retail"
            if "proceso retail" in prod_name.lower():
                continue
            
            subproductos.append(sub)
        
        return subproductos
    
    def _get_detenciones(self, ids_det: List[int]) -> List[Dict]:
        """Obtiene las detenciones de una OF"""
        if not ids_det:
            return []
        
        det_raw = odoo.execute_kw(
            "x_detenciones_proceso", "read",
            [ids_det],
            {"fields": [
                "x_studio_responsable", "x_motivodetencion",
                "x_horainiciodetencion", "x_horafindetencion",
                "x_studio_horas_de_detencin"
            ]}
        )
        
        return [clean_record(x) for x in det_raw]
    
    def _get_consumo(self, ids_cons: List[int], componentes: List[Dict], 
                     subproductos: List[Dict]) -> List[Dict]:
        """Obtiene las horas de consumo enriquecidas con datos de producto/lote"""
        if not ids_cons:
            return []
        
        cons_raw = odoo.execute_kw(
            "x_mrp_production_line_d413e", "read",
            [ids_cons],
            {"fields": ["x_name", "x_studio_hora_inicio", "x_studio_hora_fin"]}
        )
        
        # Crear mapa de Pallet -> {Producto, Lote, Tipo}
        pallet_map = self._create_pallet_map(componentes, subproductos)
        
        consumo = []
        for r in cons_raw:
            clean_r = clean_record(r)
            pallet = clean_r.get("x_name", "").strip()
            
            if pallet in pallet_map:
                clean_r["x_studio_many2one_field_sPOmE"] = pallet_map[pallet]["product"]
                clean_r["x_studio_nmero_de_lote"] = pallet_map[pallet]["lot"]
                clean_r["type"] = pallet_map[pallet]["type"]
            else:
                clean_r["x_studio_many2one_field_sPOmE"] = "Desconocido"
                clean_r["x_studio_nmero_de_lote"] = ""
                clean_r["type"] = "Desconocido"
            
            consumo.append(clean_r)
        
        return consumo
    
    def _create_pallet_map(self, componentes: List[Dict], 
                          subproductos: List[Dict]) -> Dict[str, Dict]:
        """Crea un mapa de pallet a información de producto"""
        pallet_map = {}
        
        # Map Componentes
        for c in componentes:
            prod_info = {
                "product": c.get("product_id", {}).get("name", "") if isinstance(c.get("product_id"), dict) else "",
                "lot": c.get("lot_id", {}).get("name", "") if isinstance(c.get("lot_id"), dict) else "",
                "type": "Componente"
            }
            
            # Try Source Package
            p_src = c.get("package_id", {}).get("name", "") if isinstance(c.get("package_id"), dict) else ""
            if p_src:
                pallet_map[p_src.strip()] = prod_info
            
            # Try Destination Package
            p_dest = c.get("result_package_id", {}).get("name", "") if isinstance(c.get("result_package_id"), dict) else ""
            if p_dest:
                pallet_map[p_dest.strip()] = prod_info
        
        # Map Subproductos
        for s in subproductos:
            prod_info = {
                "product": s.get("product_id", {}).get("name", "") if isinstance(s.get("product_id"), dict) else "",
                "lot": s.get("lot_id", {}).get("name", "") if isinstance(s.get("lot_id"), dict) else "",
                "type": "Subproducto"
            }
            
            p_src = s.get("package_id", {}).get("name", "") if isinstance(s.get("package_id"), dict) else ""
            if p_src:
                pallet_map[p_src.strip()] = prod_info
            
            p_dest = s.get("result_package_id", {}).get("name", "") if isinstance(s.get("result_package_id"), dict) else ""
            if p_dest:
                pallet_map[p_dest.strip()] = prod_info
        
        return pallet_map
    
    def _calculate_kpis(self, of: Dict, componentes: List[Dict], 
                       subproductos: List[Dict]) -> Dict:
        """Calcula los KPIs de una OF"""
        
        # Datos principales
        product_qty = of.get("product_qty", 0) or 0
        kghh = of.get("x_studio_kghh_efectiva", 0) or 0
        dotacion = of.get("x_studio_dotacin", 0) or 0
        horas_detencion = of.get("x_studio_horas_detencion_totales", 0) or 0
        
        # Filtrar insumos para el cálculo de consumo real de MP (Fruta)
        excluded_cat_keywords = ["insumo", "envase", "etiqueta", "embalaje", "merma"]
        excluded_name_keywords = ["caja", "bolsa", "insumo", "envase", "pallet", "etiqueta"]
        
        consumo_real_mp_fruta = 0
        for line in componentes:
            cat_name = (line.get("product_category_name", "") or "").lower()
            prod_name = (line.get("product_id", {}).get("name", "") if isinstance(line.get("product_id"), dict) else "").lower()
            qty = line.get("qty_done", 0) or 0
            
            is_excluded = False
            
            # Check Category Exclusion
            if any(k in cat_name for k in excluded_cat_keywords):
                is_excluded = True
            # Check Category Inclusion (Safety Net)
            elif "producto" in cat_name or "ptt" in cat_name:
                is_excluded = False
            # Check Name Exclusion
            else:
                if any(k in prod_name for k in excluded_name_keywords):
                    is_excluded = True
            
            if not is_excluded:
                consumo_real_mp_fruta += qty
        
        # Total Subproductos (sin Merma para rendimiento)
        total_subproductos_yield_kg = 0
        for sub in subproductos:
            cat_name = (sub.get("product_category_name", "") or "").lower()
            qty = sub.get("qty_done", 0) or 0
            
            # Excluir Merma del cálculo de rendimiento
            if "merma" not in cat_name:
                total_subproductos_yield_kg += qty
        
        # Total Subproductos (para display, incluye todo)
        total_subproductos_kg = sum([s.get("qty_done", 0) or 0 for s in subproductos])
        
        # Consumo MP total
        consumo_real_mp_total = sum([m.get("qty_done", 0) or 0 for m in componentes])
        
        # Rendimiento
        rendimiento_real = (total_subproductos_yield_kg / consumo_real_mp_fruta * 100) if consumo_real_mp_fruta else 0
        
        # Productividad
        kg_por_hh_efectiva = (total_subproductos_kg / kghh) if kghh else 0
        kg_por_operario = (total_subproductos_kg / dotacion) if dotacion else 0
        
        # Duración real
        duracion_real_horas = 0
        if of.get("date_start") and of.get("date_finished"):
            try:
                fmt = "%Y-%m-%d %H:%M:%S"
                d0 = datetime.strptime(of["date_start"], fmt)
                d1 = datetime.strptime(of["date_finished"], fmt)
                duracion_real_horas = round((d1 - d0).total_seconds() / 3600, 2)
            except:
                duracion_real_horas = 0
        
        # Eficiencia
        eficiencia_hh = (total_subproductos_kg / (kghh or 1))
        eficiencia_global = rendimiento_real
        
        return {
            "produccion_total_kg": total_subproductos_kg,
            "produccion_plan_kg": product_qty,
            "rendimiento_real_%": rendimiento_real,
            "kg_por_hh_efectiva": kg_por_hh_efectiva,
            "kg_por_operario": kg_por_operario,
            "duracion_real_horas": duracion_real_horas,
            "horas_detencion": horas_detencion,
            "consumo_real_mp_kg": consumo_real_mp_fruta,
            "consumo_total_kg": consumo_real_mp_total,
            "eficiencia_hh": eficiencia_hh,
            "eficiencia_global": eficiencia_global,
        }


# Instancia global del servicio
of_service = OFService()

"""
Servicio para gestión de Stock y Cámaras
"""
from typing import List, Dict, Optional
from datetime import datetime, date
from backend.core.odoo_connection import odoo
from backend.utils.helpers import clean_record

class StockService:
    """Servicio para operaciones de Stock y Cámaras"""

    def get_chambers_stock(self) -> List[Dict]:
        """
        Obtiene el stock de las cámaras agrupado por Especie y Condición.
        Incluye información de la ubicación padre (Zona).
        Incluye capacidad en pallets y posiciones ocupadas.
        Usa read_group para optimizar rendimiento.
        """
        uid, models = odoo.connect()

        # 1. Primero obtener ubicaciones que tienen stock
        try:
            # Buscar quants con stock > 0
            quants_with_stock = odoo.execute_kw(
                "stock.quant", "search_read",
                [[("quantity", ">", 0)]],
                {"fields": ["location_id", "package_id"], "limit": 100000}
            )
            
            # Extraer IDs únicos de ubicaciones con stock
            loc_ids_with_stock = list(set([q["location_id"][0] for q in quants_with_stock if q.get("location_id")]))
            
            if not loc_ids_with_stock:
                print("No locations with stock found")
                return []
            
            # Contar pallets por ubicación
            pallets_per_location = {}
            for q in quants_with_stock:
                if q.get("location_id") and q.get("package_id"):
                    loc_id = q["location_id"][0]
                    pkg_id = q["package_id"][0]
                    if loc_id not in pallets_per_location:
                        pallets_per_location[loc_id] = set()
                    pallets_per_location[loc_id].add(pkg_id)
            
            # Ahora obtener solo esas ubicaciones internas
            domain_loc = [("id", "in", loc_ids_with_stock), ("usage", "=", "internal")]
            # Campos básicos (sin campos Studio que pueden no existir)
            fields_loc = ["name", "display_name", "location_id"]
            
            loc_ids = odoo.execute_kw("stock.location", "search", [domain_loc])
            locations = odoo.execute_kw("stock.location", "read", [loc_ids], {"fields": fields_loc})
            
        except Exception as e:
            print(f"Error fetching locations: {e}")
            return []

        chambers = {}
        for loc in locations:
            clean_loc = clean_record(loc)
            loc_id = clean_loc["id"]
            
            parent = loc.get("location_id")
            parent_name = parent[1] if parent else "Sin Padre"
            
            # Pallets ocupados (conteo real desde quants)
            occupied = len(pallets_per_location.get(loc_id, set()))
            # Capacidad estimada (pallets ocupados * 1.2 como placeholder, o un valor fijo)
            # Si tienes un campo de capacidad real, podemos agregarlo después
            capacity = max(occupied, 50)  # Mínimo 50 o lo que tenga ocupado
            
            chambers[loc_id] = {
                "id": loc_id,
                "name": clean_loc["name"],
                "full_name": clean_loc["display_name"],
                "parent_name": parent_name,
                "capacity_pallets": capacity,
                "occupied_pallets": occupied,
                "stock_data": {} 
            }

        # 2. Obtener Stock Agrupado (read_group)
        domain_quant = [
            ("location_id", "in", list(chambers.keys())),
            ("quantity", ">", 0)
        ]
        
        try:
            # Agrupamos por location_id y product_id
            grouped_data = odoo.execute_kw(
                "stock.quant", "read_group",
                [domain_quant, ["location_id", "product_id", "quantity"], ["location_id", "product_id"]],
                {"lazy": False}
            )
        except Exception as e:
            print(f"Error fetching grouped stock: {e}")
            return []

        # 3. Obtener Info de Productos (Categorías)
        product_ids = set()
        for g in grouped_data:
            if g.get("product_id"):
                product_ids.add(g["product_id"][0])
        
        products_info = {}
        if product_ids:
            try:
                p_fields = ["categ_id", "name"]
                p_data = odoo.execute_kw("product.product", "read", [list(product_ids)], {"fields": p_fields})
                for p in p_data:
                    products_info[p["id"]] = {
                        "category": p["categ_id"][1] if p["categ_id"] else "Sin Categoría",
                        "name": p["name"]
                    }
            except Exception as e:
                print(f"Error fetching products: {e}")

        # 4. Procesar Datos Agrupados
        for g in grouped_data:
            loc_data = g.get("location_id")
            prod_data = g.get("product_id")
            qty = g.get("quantity", 0)
            
            if not loc_data or not prod_data:
                continue
                
            loc_id = loc_data[0]
            prod_id = prod_data[0]
            
            if loc_id not in chambers:
                continue
                
            if prod_id not in products_info:
                species = "Desconocido"
                condition = "N/A"
            else:
                p_info = products_info[prod_id]
                species = p_info["category"]
                prod_name_lower = p_info["name"].lower()
                if "org" in prod_name_lower:
                    condition = "Orgánico"
                else:
                    condition = "Convencional"

            key = f"{species} - {condition}"
            
            if key not in chambers[loc_id]["stock_data"]:
                chambers[loc_id]["stock_data"][key] = 0
            
            chambers[loc_id]["stock_data"][key] += qty

        # Formatear salida
        result = []
        for cid, data in chambers.items():
            if data["stock_data"]:
                result.append(data)
                
        return result

    def get_pallets(self, location_id: int, category: Optional[str] = None) -> List[Dict]:
        """
        Obtiene el detalle de pallets de una ubicación, opcionalmente filtrado por categoría/especie.
        """
        uid, models = odoo.connect()
        
        domain = [
            ("location_id", "=", location_id),
            ("quantity", ">", 0),
            ("package_id", "!=", False) # Solo pallets
        ]
        
        fields = [
            "package_id", "product_id", "lot_id", "quantity", 
            "in_date", "location_id"
        ]
        
        try:
            quant_ids = odoo.execute_kw("stock.quant", "search", [domain])
            quants = odoo.execute_kw("stock.quant", "read", [quant_ids], {"fields": fields})
        except Exception as e:
            print(f"Error fetching pallets: {e}")
            return []
            
        # Filtrar y formatear
        pallets = []
        
        # Necesitamos categorías para filtrar
        product_ids = set(q["product_id"][0] for q in quants if q["product_id"])
        products_map = {}
        if product_ids:
             p_data = odoo.execute_kw("product.product", "read", [list(product_ids)], {"fields": ["categ_id", "name"]})
             for p in p_data:
                 products_map[p["id"]] = p
        
        for q in quants:
            prod_id = q["product_id"][0] if q["product_id"] else None
            if not prod_id: 
                continue
                
            p_info = products_map.get(prod_id, {})
            cat_name = p_info.get("categ_id", ["", "Sin Categoría"])[1]
            prod_name = p_info.get("name", "N/A")
            
            # Heurística de condición (repetida, idealmente refactorizar)
            condition = "Orgánico" if "org" in prod_name.lower() else "Convencional"
            species_condition = f"{cat_name} - {condition}"
            
            # Filtro
            if category and category != species_condition:
                continue
            
            # Procesar fecha de entrada
            in_date = q.get("in_date")
            in_date_str = ""
            days_old = 0
            if in_date:
                try:
                    if isinstance(in_date, str):
                        dt = datetime.fromisoformat(in_date.replace('Z', '+00:00'))
                    else:
                        dt = in_date
                    in_date_str = dt.strftime("%Y-%m-%d")
                    days_old = (datetime.now() - dt.replace(tzinfo=None)).days
                except:
                    pass
                
            pallets.append({
                "pallet": q["package_id"][1] if q["package_id"] else "Sin Pallet",
                "product": prod_name,
                "lot": q["lot_id"][1] if q["lot_id"] else "N/A",
                "quantity": q["quantity"],
                "category": cat_name,
                "condition": condition,
                "species_condition": species_condition,
                "location": q["location_id"][1],
                "in_date": in_date_str,
                "days_old": days_old
            })
            
        return pallets

    def get_lots_by_category(self, category: str, location_ids: Optional[List[int]] = None) -> List[Dict]:
        """
        Obtiene lotes agrupados por categoría con información de antigüedad.
        category: Especie - Condición (ej: "PRODUCTOS / PTT - Convencional")
        """
        uid, models = odoo.connect()
        
        # Parsear categoría y condición
        parts = category.rsplit(" - ", 1)
        cat_name = parts[0] if len(parts) > 0 else category
        condition_filter = parts[1] if len(parts) > 1 else None
        
        # Dominio base
        domain = [
            ("quantity", ">", 0),
            ("lot_id", "!=", False)
        ]
        
        if location_ids:
            domain.append(("location_id", "in", location_ids))
        
        fields = [
            "lot_id", "product_id", "quantity", "in_date", 
            "location_id", "package_id"
        ]
        
        try:
            quant_ids = odoo.execute_kw("stock.quant", "search", [domain], {"limit": 50000})
            quants = odoo.execute_kw("stock.quant", "read", [quant_ids], {"fields": fields})
        except Exception as e:
            print(f"Error fetching lots: {e}")
            return []
        
        # Obtener info de productos
        product_ids = set(q["product_id"][0] for q in quants if q.get("product_id"))
        products_map = {}
        if product_ids:
            try:
                p_data = odoo.execute_kw("product.product", "read", [list(product_ids)], {"fields": ["categ_id", "name"]})
                for p in p_data:
                    products_map[p["id"]] = p
            except:
                pass
        
        # Agrupar por lote
        lots_data = {}
        
        for q in quants:
            prod_id = q["product_id"][0] if q.get("product_id") else None
            lot_id = q["lot_id"][0] if q.get("lot_id") else None
            
            if not prod_id or not lot_id:
                continue
            
            p_info = products_map.get(prod_id, {})
            p_cat = p_info.get("categ_id", ["", ""])[1] if p_info.get("categ_id") else ""
            p_name = p_info.get("name", "")
            p_condition = "Orgánico" if "org" in p_name.lower() else "Convencional"
            p_species_condition = f"{p_cat} - {p_condition}"
            
            # Filtrar por categoría
            if p_species_condition != category:
                continue
            
            lot_name = q["lot_id"][1]
            
            # Procesar fecha
            in_date = q.get("in_date")
            in_date_str = ""
            days_old = 0
            if in_date:
                try:
                    if isinstance(in_date, str):
                        dt = datetime.fromisoformat(in_date.replace('Z', '+00:00'))
                    else:
                        dt = in_date
                    in_date_str = dt.strftime("%Y-%m-%d")
                    days_old = (datetime.now() - dt.replace(tzinfo=None)).days
                except:
                    pass
            
            # Agrupar
            if lot_name not in lots_data:
                lots_data[lot_name] = {
                    "lot": lot_name,
                    "product": p_name,
                    "category": p_cat,
                    "condition": p_condition,
                    "quantity": 0,
                    "pallets": 0,
                    "in_date": in_date_str,
                    "days_old": days_old,
                    "locations": set()
                }
            
            lots_data[lot_name]["quantity"] += q["quantity"]
            if q.get("package_id"):
                lots_data[lot_name]["pallets"] += 1
            if q.get("location_id"):
                lots_data[lot_name]["locations"].add(q["location_id"][1])
        
        # Formatear resultado
        result = []
        for lot_name, data in lots_data.items():
            data["locations"] = list(data["locations"])
            result.append(data)
        
        # Ordenar por antigüedad (más viejo primero)
        result.sort(key=lambda x: x["days_old"], reverse=True)
        
        return result

stock_service = StockService()

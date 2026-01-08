# =====================================================
# MÓDULO ADMIN - Exportaciones Públicas
# =====================================================
"""
Módulos de administración para el panel de admin.
Cada módulo contiene funciones render_* que muestran
las diferentes secciones del panel.
"""

from .data_upload import render_data_upload_tab
from .users import render_users_tab
from .companies import render_companies_tab
from .logs import render_logs_tab

__all__ = [
    'render_data_upload_tab',
    'render_users_tab',
    'render_companies_tab',
    'render_logs_tab',
]

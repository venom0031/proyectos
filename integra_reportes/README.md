# Sistema Integra SpA - Gestión de Datos Ganaderos

Sistema de visualización y gestión de datos de producción lechera con Row-Level Security (RLS).

## 🚀 Inicio Rápido

### Requisitos
- Python 3.12+
- PostgreSQL 16+
- Docker (opcional, para producción)

### Instalación Local

```bash
# 1. Clonar repositorio
git clone <repo-url>
cd streamlit_app

# 2. Crear entorno virtual
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
copy .env.example .env
# Editar .env con tus credenciales

# 5. Inicializar base de datos
cd scripts
.\init.ps1  # Windows
./init.sh   # Linux/Mac

# 6. Ejecutar aplicación
streamlit run app.py

# 7. Panel de administración (solo admin)
streamlit run admin_panel.py
```

## 📁 Estructura del Proyecto

```
streamlit_app/
├── app.py                  # Aplicación principal (usuarios)
├── admin_panel.py          # Panel de administración
├── requirements.txt
├── .env.example
├── README.md
├── docker-compose.yml
│
├── modules/               # Módulos Python
│   ├── auth.py           # Autenticación
│   ├── config.py         # Configuración
│   ├── db_connection.py  # Conexión BD
│   ├── etl.py            # Procesamiento datos
│   ├── matrix_builder.py # Construcción matriz
│   └── concept_engine.py # Mapeo conceptos
│
├── db/                   # Scripts SQL
│   ├── schema.sql       # Esquema completo
│   ├── init_db.sql      # Inicialización
│   └── load_sample.sql  # Datos de prueba
│
├── data/                # Templates Excel
│   ├── template_semanal.xlsx
│   └── template_historico.xlsx
│
└── scripts/             # Scripts utilidad
    ├── init.ps1        # Inicializar BD
    └── backup.sh       # Backup automático
```

## 👥 Usuarios

### Desarrollo
- **Admin**: `admin` / `admin123`
- **Usuario 1**: `user_eduvigis` / `test123`
- **Usuario 2**: `user_lagos` / `test123`

### Producción
Crear usuarios desde el panel de administración.

## 🔐 Row-Level Security (RLS)

### Tablas SIN RLS (públicas)
- `datos_semanales` - Ranking visible para todos

### Tablas CON RLS (filtradas)
- `datos_diarios` - Solo datos de empresas asignadas
- `establecimientos` - Solo establecimientos de sus empresas
- `historico_mdat` - Solo histórico de sus empresas

## 📊 Panel de Administración

### Funciones
1. **Carga de Datos**
   - Upload de Reporte Semanal (Excel)
   - Upload de Histórico MDAT
   - Validación automática de estructura

2. **Gestión de Usuarios**
   - Crear/editar usuarios
   - Asignar empresas (RLS)
   - Gestión de permisos

3. **Gestión de Empresas**
   - Crear/editar empresas
   - Asignar establecimientos

4. **Logs**
   - Historial de cargas
   - Cambios en permisos

## 📤 Carga de Datos

### Reporte Semanal

**Estructura esperada:**
```
Empresa | Empresa_COD | Establecimiento | CATEGORIA | CONCEPTO | 27-09-2025 | 28-09-2025 | ...
```

**Proceso:**
1. Ir a Panel Admin
2. Sección "Carga de Datos"
3. Upload archivo Excel
4. Seleccionar tipo "Reporte Semanal"
5. Click "Procesar"
6. Verificar log de carga

### Histórico MDAT

**Estructura esperada:**
```
Establecimiento | N° Semana | Año | MDAT | Vacas en ordeña
```

**Nota:** Solo se carga una vez al inicio.

## 🐳 Despliegue con Docker

```bash
# Construir y levantar servicios
docker-compose up -d

# Ver logs
docker-compose logs -f

# Detener
docker-compose down
```

**Acceso:**
- App principal: http://localhost:8501
- Panel admin: http://localhost:8502

## 🔧 Configuración

### Variables de Entorno (`.env`)

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=integra_rls
DB_USER=postgres
DB_PASSWORD=tu_password

DB_POOL_MIN=1
DB_POOL_MAX=10

SESSION_TIMEOUT=60
```

## 🛠️ Desarrollo

### Ejecutar tests
```bash
python -m pytest tests/
```

### Linting
```bash
flake8 modules/
```

## 📝 Notas de Producción

1. **Backups**: Configurar backup automático diario
2. **SSL**: Usar certificado Let's Encrypt
3. **Firewall**: Solo puertos 80, 443, 5432 (interno)
4. **Monitoring**: Configurar logs y alertas
5. **Updates**: Probar en staging primero

## 🐛 Troubleshooting

### Error de conexión PostgreSQL
- Verificar que PostgreSQL está corriendo
- Checar credenciales en `.env`
- Verificar firewall

### Error de encoding UTF-8
- Ver `INSTALACION.md` para soluciones Windows

### RLS no filtra correctamente
- Verificar asignación usuario-empresa en BD
- Checar que `is_admin` está correcto

## 📞 Soporte

Para issues y preguntas: [GitHub Issues]

## 📄 Licencia

Proprietary - Integra SpA © 2024

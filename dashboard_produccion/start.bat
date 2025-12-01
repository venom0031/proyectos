@echo off
REM Script de inicio para desarrollo (Windows)
REM Este script inicia tanto el backend como el frontend

echo [+] Iniciando Dashboard de Produccion Odoo...
echo.

REM Activar entorno virtual si existe
if exist "venv\Scripts\activate.bat" (
    echo [+] Activando entorno virtual...
    call venv\Scripts\activate.bat
)

REM Instalar/actualizar dependencias
echo [+] Verificando dependencias...
pip install -r requirements.txt --quiet

REM Crear directorio de logs si no existe
if not exist "logs" mkdir logs

REM Iniciar backend en una nueva ventana
echo [+] Iniciando backend API...
start "Odoo API Backend" cmd /k "uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000"

REM Esperar a que el backend esté listo
timeout /t 3 /nobreak >nul

REM Iniciar frontend en una nueva ventana
echo [+] Iniciando dashboard frontend...
start "Odoo Dashboard" cmd /k "streamlit run dashboard.py"

echo.
echo [OK] Servicios iniciados!
echo.
echo API: http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo Dashboard: http://localhost:8501
echo.
echo Presiona cualquier tecla para salir...
pause >nul

# Multi-stage build para reducir tamaño
FROM python:3.11-slim-bookworm as builder

WORKDIR /app

# Instalar dependencias del sistema para compilar paquetes Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements y compilar wheels
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage final
FROM python:3.11-slim-bookworm

WORKDIR /app

# Instalar wkhtmltopdf, curl y dependencias runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    wkhtmltopdf \
    curl \
    fontconfig \
    libfontconfig1 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Copiar Python packages compilados desde builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copiar código de la aplicación
COPY . .

# Crear directorios necesarios
RUN mkdir -p /app/logs /app/data

# Exponer puerto de Streamlit
EXPOSE 8501

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Comando de inicio
CMD ["streamlit", "run", "modules/app_rls.py", "--server.port=8501", "--server.address=0.0.0.0"]

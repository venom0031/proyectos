# Multi-stage build para reducir tamaño
FROM python:3.12-slim as builder

WORKDIR /app

# Instalar dependencias del sistema para compilar paquetes Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements y compilar wheels
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# =====================================================
# Stage final
# =====================================================
FROM python:3.12-slim

WORKDIR /app

# Instalar wkhtmltopdf, curl y dependencias runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    wkhtmltopdf \
    curl \
    xfonts-75dpi \
    xfonts-96dpi \
    xfonts-base \
    xfonts-encodings \
    libfontconfig1 \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

# =====================================================
# SEGURIDAD: Crear usuario non-root
# =====================================================
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Copiar Python packages compilados desde builder
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

# Copiar código de la aplicación
COPY --chown=appuser:appgroup . .

# Crear directorios necesarios con permisos correctos
RUN mkdir -p /app/logs /app/data && \
    chown -R appuser:appgroup /app/logs /app/data

# Cambiar a usuario non-root
USER appuser

# Exponer puerto de Streamlit
EXPOSE 8501

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Comando de inicio
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]

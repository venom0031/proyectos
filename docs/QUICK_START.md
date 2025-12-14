# 🚀 Quick Start - Iniciar en 5 Minutos

## Opción 1: Desarrollo Local (Windows/Mac/Linux)

```bash
# 1. Clonar y entrar
git clone <url-repo> && cd integra_reportes

# 2. Crear entorno virtual
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar
cp .env.example .env
# Editar .env con credenciales

# 5. Ejecutar (2 terminales)
streamlit run app.py            # Terminal 1
streamlit run admin_panel.py    # Terminal 2

# Acceso: http://localhost:8501
```

**Nota sobre PDF:** Para PDF en desarrollo, instala wkhtmltopdf:
- **Windows:** `choco install wkhtmltopdf`
- **Linux:** `apt-get install wkhtmltopdf`
- **Mac:** `brew install wkhtmltopdf`

---

## Opción 2: Producción con Docker (RECOMENDADO)

### Requisitos
- Docker y Docker Compose instalados
- Linux/Mac o Windows (WSL2 recomendado)

### 3 comandos para empezar

```bash
# 1. Clonar
git clone <url-repo> && cd integra_reportes

# 2. Configurar
cp .env.example .env
# Editar .env (DB_PASSWORD importante)

# 3. Desplegar
docker-compose up -d

# ✅ Listo! Acceso: http://localhost:8501
```

### Ver logs en vivo
```bash
docker-compose logs -f app
```

### Detener
```bash
docker-compose down
```

---

## Opción 3: Deploy a Servidor (Producción)

Ver: **[DEPLOYMENT.md](./DEPLOYMENT.md)**

Resumen:
1. VPS con Linux (Ubuntu 20.04+)
2. Instalar Docker
3. Clonar repo y ejecutar `docker-compose up -d`
4. Configurar Nginx + SSL
5. ¡Listo en servidor!

---

## Verificación Rápida

```bash
# ✅ Acceso local
http://localhost:8501      # App principal
http://localhost:8502      # Admin (si está levantado)

# ✅ Usuarios de prueba
Usuario: admin / admin123
Usuario: user_eduvigis / test123

# ✅ Verificar PDF (debe mostrar botón de descarga)
1. Ir a "Matriz Semanal"
2. Buscar botón "Descargar matriz en PDF"
3. Click → descarga automática
```

---

## Troubleshooting Rápido

### "ModuleNotFoundError: No module named 'streamlit'"
```bash
pip install -r requirements.txt
```

### "FATAL: role 'postgres' does not exist"
```bash
# Ver INSTALACION.md para setup de BD
```

### "wkhtmltopdf not found"
```bash
# En Docker: ✅ Ya incluido
# En local: Ver sección "Nota sobre PDF" arriba
```

### "Port 8501 is already in use"
```bash
# Cambiar puerto en Streamlit:
streamlit run app.py -- --server.port=8503
```

---

## Documentación Completa

- **[README.md](./README.md)** - Documentación principal
- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Guía de servidor
- **[INSTALACION.md](./INSTALACION.md)** - Setup local
- **[CHANGELOG_ESCALABILIDAD.md](./CHANGELOG_ESCALABILIDAD.md)** - Cambios recientes

---

## ¿Necesitas ayuda?

1. **Desarrollo local** → Ver [INSTALACION.md](./INSTALACION.md)
2. **Docker** → Ver [DEPLOYMENT.md](./DEPLOYMENT.md) sección 1-3
3. **Servidor** → Ver [DEPLOYMENT.md](./DEPLOYMENT.md) sección completa

---

**¡Eso es todo!** 🎉

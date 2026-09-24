# ==========================================
# Dockerfile para Google Cloud Run
# UTP Assistant (Streamlit)
# ==========================================

# 1. Imagen base oficial de Python ligera
FROM python:3.11-slim

# 2. Configuración de variables de entorno de Python
# - PYTHONUNBUFFERED: Envía logs inmediatamente a Cloud Logging sin buffering
# - PYTHONDONTWRITEBYTECODE: Evita generación de archivos .pyc innecesarios
# - PORT: Puerto por defecto asignado (Google Cloud Run inyecta $PORT en ejecución)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# 3. Directorio de trabajo de la aplicación
WORKDIR /app

# 4. Copiar requerimientos e instalar dependencias con caché optimizada
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiar el código fuente del proyecto
COPY . .

# 6. Exponer el puerto por defecto (informativo para documentación y Docker)
EXPOSE 8080

# 7. Ejecutar Streamlit adaptándose dinámicamente al puerto inyectado por Cloud Run
# Cloud Run inyecta la variable de entorno $PORT (habitualmente 8080)
CMD ["sh", "-c", "streamlit run app.py --server.port=${PORT} --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false"]

FROM python:3.11-slim

# Sistema mínimo para lxml y beautifulsoup
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependencias primero (capa cacheable)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código del backend
COPY . .

# Copiar el paquete scraping (está en ../scraping relativo al backend)
# En build de Docker se copia desde el root del proyecto
COPY ../scraping /scraping

ENV PYTHONPATH=/app:/scraping
ENV ENVIRONMENT=production
ENV PORT=8000

EXPOSE 8000

# Usar gunicorn con uvicorn workers en producción
# Si el servicio no soporta gunicorn, usar uvicorn directamente
CMD ["uvicorn", "main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--log-level", "info"]

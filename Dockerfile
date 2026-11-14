# Etapa 1: compila el cliente React (Vite + TypeScript + Tailwind).
FROM node:22-alpine AS frontend
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# Etapa 2: servidor Django con la API y el cliente ya compilado.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# El conector de MySQL se compila al instalarlo y necesita estas librerias.
RUN apt-get update \
    && apt-get install -y --no-install-recommends default-libmysqlclient-dev build-essential pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

# Se copia fuera de /app para que el volumen de desarrollo no lo reemplace,
# y se normalizan los finales de linea por si Windows los convirtio a CRLF.
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/entrypoint.sh && chmod +x /usr/local/bin/entrypoint.sh

COPY . .
COPY --from=frontend /web/dist /app/frontend/dist

RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/staticfiles \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
ENTRYPOINT ["entrypoint.sh"]
# Render indica el puerto en PORT. Dos workers por la memoria limitada del plan gratis.
# 120 s de espera: leer un contrato largo con IA puede tardar cerca de un minuto.
CMD ["sh", "-c", "exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120"]

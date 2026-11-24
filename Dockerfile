# Single-service image: builds the website, then serves it and the API from FastAPI.
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
# Empty base URL = call the API on the same origin.
ENV VITE_API_BASE_URL=""
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=10000 FRONTEND_DIST=/app/web FIXSAATHI_DATA_DIR=/app/data
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY data/ /app/data/
COPY --from=web /web/dist /app/web
RUN useradd -m app && mkdir -p /app/uploads && chown -R app /app
USER app
EXPOSE 10000
CMD ["sh", "-c", "alembic upgrade head && python scripts/ingest_knowledge.py --if-present && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]

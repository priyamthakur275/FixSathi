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
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080 FRONTEND_DIST=/app/web FIXSAATHI_DATA_DIR=/app/data
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY data/ /app/data/
COPY docs/EVALUATION_RESULTS.json /app/docs/EVALUATION_RESULTS.json
COPY --from=web /web/dist /app/web
RUN useradd -m app && mkdir -p /app/uploads && chown -R app /app
USER app
EXPOSE 8080
# Migrations, the repair records, the embedding index in the background (when a Gemini key is set), then the server on $PORT.
CMD ["sh", "scripts/render_start.sh"]

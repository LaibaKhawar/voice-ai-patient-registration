# Single deployable image: builds the dashboard (static export) and serves it
# from the FastAPI backend, so the API, webhook and dashboard share one origin.

FROM node:22-alpine AS dashboard
WORKDIR /dashboard
COPY dashboard/package.json dashboard/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY dashboard/ ./
RUN npm run build

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install -r requirements.txt
COPY backend/ ./
COPY --from=dashboard /dashboard/out ./dashboard_build
RUN useradd --create-home appuser && chmod +x start.sh
USER appuser
ENV PORT=8000
EXPOSE 8000
CMD ["./start.sh"]

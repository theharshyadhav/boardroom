# Multi-stage build for the BoardMind FastAPI + ADK agent backend.
# Runs unchanged on Cloud Run (reads GOOGLE_CLOUD_PROJECT / credentials from
# the environment and the attached service account) and locally via
# `docker compose up` (see docker-compose.yml at repo root).

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for duckdb/pandas/scikit-learn wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/app ./app

# Cloud Run injects $PORT; default to 8080 (Cloud Run's convention) for
# local/docker-compose use so the same image needs no CMD override.
ENV PORT=8080
EXPOSE 8080

# --workers 1: agents hold in-memory ADK Runner/session-service state per
# process. Scale via Cloud Run instance concurrency + multiple instances,
# not multiple uvicorn workers in one container, so every agent's identity
# maps cleanly to one process for observability purposes.
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1

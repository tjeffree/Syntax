# Host-agnostic container for the Syntax API (GDD §6: plain container, config
# via env vars — runs on Cloud Run, Fly.io, Railway, etc.).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

# Firebase deps are needed in production (AUTH_MODE=firebase / STORE_MODE=firestore).
COPY requirements-firebase.txt requirements.txt ./
RUN pip install -r requirements-firebase.txt

COPY app ./app
COPY content ./content
COPY schema ./schema

# Cloud Run injects $PORT; default to 8080 locally.
ENV PORT=8080
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]

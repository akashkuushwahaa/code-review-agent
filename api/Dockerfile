# Dashboard API image. Reads the shared findings volume + a baked eval snapshot.
# Build context is the repo root (so the `api` package keeps its structure).
FROM python:3.12-slim

WORKDIR /app

COPY api/requirements.txt ./api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt

COPY api ./api

# findings.db comes from the shared volume; eval snapshot is baked in.
ENV REVIEW_DB_PATH=/data/findings.db
EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

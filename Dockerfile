# Container image for the security review agent.
#
# The agent is an on-demand CLI, not a long-running service — you invoke it
# with a PR URL and it exits. So this image's ENTRYPOINT is `review.py` and
# arguments are passed at run time:
#
#   docker compose run --rm agent https://github.com/owner/repo/pull/123
#
# Secrets are never baked in: they come from the environment at run time
# (docker-compose reads them from .env). The findings database lives on a
# mounted volume so dedup survives container restarts.

FROM python:3.12-slim

# Some Python wheels fall back to a source build; give pip a compiler so the
# image builds even if a prebuilt wheel is unavailable for a dependency.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first so this layer is cached unless requirements change.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the agent source. .dockerignore keeps secrets, the local DB, git, and
# caches out of the image.
COPY . .

# SQLite findings DB on a volume-backed path — persists across container runs
# so dedup works between invocations (the gap Phase 4 flagged for ephemeral
# environments). Chroma is in-process and rebuilt per run (Phase 3 decision),
# so it needs no persistent volume.
ENV REVIEW_DB_PATH=/data/findings.db
VOLUME ["/data"]

# With no arguments, review.py prints usage and exits — a friendly default for
# a bare `docker run` / `docker compose up`.
ENTRYPOINT ["python", "review.py"]

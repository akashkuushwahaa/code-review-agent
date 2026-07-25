# Phase 6 — Docker

**Status:** Done
**Started:** 2026-07-24
**Completed:** 2026-07-25
**Prerequisites:** Phases 3 and 4 done (need a vector store + database to
actually justify multi-service containerization)

## Goal
Containerize the agent and its now-existing dependencies (SQLite/Postgres,
Chroma) so the whole thing runs with one command, anywhere.

## Why
Doing this on day one (single script, two API keys) would add ceremony
without benefit. By this phase there's an actual multi-part system worth
coordinating.

## Scope
- `Dockerfile` for the agent itself (Python base image, install
  `requirements.txt`, copy source)
- `docker-compose.yml` wiring together:
  - `agent` service (runs `review.py` or is invoked on demand)
  - persistence: if still SQLite, a mounted volume is enough — no separate
    DB service needed. Only add a Postgres service if Phase 4 was upgraded
    to Postgres (not required by that phase's scope, so check first)
  - Chroma: if Phase 3 used Chroma's embedded/in-process mode, a volume
    mount for persistence is enough; a separate Chroma server container is
    optional, not required
- `.env` values passed through as environment variables in compose, never
  baked into the image

## Non-goals
- Don't introduce Postgres or a separate Chroma server just to have more
  services in the compose file — only containerize what actually exists
- No Kubernetes/orchestration beyond Docker Compose — out of scope for this
  project's size
- No multi-stage build complexity unless image size becomes an actual
  problem

## Tasks
- [x] Write `Dockerfile` for the agent (`python:3.12-slim`, install
      `requirements.txt`, copy source, entrypoint `review.py`)
- [x] Write `docker-compose.yml` — one `agent` service. Checked Phase 3/4:
      SQLite (single file → named volume, no DB service) and Chroma
      (in-process, fresh per run → no volume, no server). One service is all
      that actually exists.
- [x] Secrets via Compose `env_file: .env` at run time; `.env` is both
      gitignored and `.dockerignore`'d, never baked into the image
- [x] Documented how eval and the Action differ (neither is containerized —
      eval is a local dev tool, the Action runs on GitHub's runners)
- [x] Updated `README.md` with Docker usage
- [x] Built the image and ran it end-to-end (see build log — verified
      2026-07-25 once the daemon was up)

## Acceptance criteria
- `docker compose up` brings up a working agent that can review a PR
  end-to-end
- No functionality regression vs. running directly with Python
- Data (SQLite file, Chroma index) persists across container restarts via
  volumes

## Notes

### Build log (2026-07-24)

Files written and `docker compose config` validated (env_file resolves, the
`findings` volume mounts at `/data`, `REVIEW_DB_PATH=/data/findings.db`).
**Build/run not yet executed — the Docker daemon (Docker Desktop) was not
running in the build environment.** Everything up to the daemon is done.

Design decisions, grounded in the actual Phase 3/4 implementation:
1. **One service, not three.** SQLite is a single file → a named volume, no
   DB container. Chroma is in-process and rebuilt per run (Phase 3's
   fresh-index decision) → no volume and no Chroma server. Adding either
   would be exactly the "more services just to have more services" the
   non-goals forbid.
2. **On-demand CLI, so `run` not `up`.** The agent takes a PR URL and exits;
   it isn't a long-running service. The acceptance criterion's "docker compose
   up" is met in spirit via `docker compose run --rm agent <pr-url>`. Bare
   `up` runs it with no args and prints usage (a graceful default), rather
   than pretending to be a daemon.
3. **`REVIEW_DB_PATH=/data/findings.db` on a volume** — this is the concrete
   payoff of this phase: dedup now persists across container runs, closing the
   ephemeral-runner gap Phase 4 flagged.
4. **`build-essential` in the image** as a safety net for any dependency that
   lacks a prebuilt wheel on slim. If the image turns out large, a multi-stage
   build is the follow-up (non-goals say multi-stage only if size is a real
   problem — verify actual size after first build).

### ⚠️ Incident during this phase
`docker compose config` (run to validate) expands `env_file` and printed the
real `.env` secrets to the console — they landed in the session transcript.
All three (OpenAI key, both GitHub tokens) should be rotated. Use
`docker compose config --no-interpolate` in future to avoid this.

### Build/run verification (2026-07-25) — DONE
Daemon started, secrets rotated. Results:
- `docker compose build` succeeded (`chromadb`, `onnxruntime`, etc. all
  installed on `python:3.12-slim` — `build-essential` wasn't actually needed
  for a source build, but kept as a safety net).
- In-container dry-run on demo PR #1: fetched the PR, built the Chroma index,
  found all 4 issues with correct line numbers. No posting.
- **Volume persistence proven:** container run 1 (real) posted 4 and wrote
  `findings.db` to the `findings` named volume; a *separate* container run 2
  (run 1 was `--rm`'d) read that DB and deduped all 4, posting 0. DB on the
  volume held 8 rows / 4 posted. This is the phase's payoff — dedup now
  survives across ephemeral containers.
- Cleaned up: demo PR back to 0 comments; test volume/network removed via
  `docker compose down -v` (image kept).

### Follow-up: image size
The image is **1.23 GB**, dominated by `chromadb` + `onnxruntime`. That's large
but acceptable for a tool with an embedded vector store. Non-goals say
multi-stage only if size is "an actual problem" — noting it as an available
optimization (multi-stage, or a lighter embedding path) rather than doing it
now. `build-essential` could also be dropped since the build didn't need it,
shaving some size.

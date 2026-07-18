# Phase 6 — Docker

**Status:** Not Started
**Started:**
**Completed:**
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
- [ ] Write `Dockerfile` for the agent
- [ ] Write `docker-compose.yml` with the services that actually exist by
      this point (check Phases 3 and 4's final implementation before
      assuming what's needed)
- [ ] Confirm secrets are passed via environment/compose `.env`, not
      hardcoded or committed
- [ ] Confirm the eval harness (Phase 2) and GitHub Action (Phase 1) still
      work with the containerized setup, or document how they differ
- [ ] Update root `README.md` with `docker compose up` instructions

## Acceptance criteria
- `docker compose up` brings up a working agent that can review a PR
  end-to-end
- No functionality regression vs. running directly with Python
- Data (SQLite file, Chroma index) persists across container restarts via
  volumes

## Notes
_(Coding agent: log any deviations or follow-ups here as you build.)_

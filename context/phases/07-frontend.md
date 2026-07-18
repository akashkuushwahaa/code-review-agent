# Phase 7 — Frontend Dashboard

**Status:** Not Started
**Started:**
**Completed:**
**Prerequisites:** Phases 1, 2, 4, and 6 done (needs a real backend service,
persisted data, and eval metrics to actually display)

## Goal
Add a small dashboard that makes the agent demoable and shows off what's
already been built: review history, findings, and eval metrics.

## Why
This is the highest-effort phase and depends entirely on prior phases
already existing as real, callable services — a frontend with nothing real
behind it is just a mockup. It's sequenced last on purpose.

## Scope
- A minimal backend API (FastAPI is a reasonable choice, keeps it Python)
  exposing:
  - `GET /reviews` — list past reviews from the Phase 4 database
  - `GET /reviews/{pr_url}` — findings for a specific PR
  - `GET /eval` — latest eval harness results (Phase 2)
- A **Next.js** frontend with three simple views, no more:
  1. **Review list** — past PRs reviewed, finding counts by severity
  2. **Review detail** — findings for one PR, shown against the diff (a
     basic diff viewer library is fine, don't build one from scratch)
  3. **Eval metrics** — precision/recall/F1 from the latest eval run
- Keep styling simple (Tailwind defaults are fine) — this is about
  demonstrating the pipeline, not visual design polish

## Non-goals
- No real-time streaming/WebSockets — polling or plain page loads are
  sufficient for this project's scale
- No authentication/multi-user system — single-operator tool, keep it that
  way unless explicitly asked to change
- No editing findings from the UI — read-only dashboard is enough
- Don't rebuild a full GitHub-style diff viewer — use an existing library

## Tasks
- [ ] Add a small FastAPI app (`api/` folder) exposing the three endpoints
      above, reading from the Phase 4 SQLite/Postgres store
- [ ] Scaffold a Next.js app (`web/` folder)
- [ ] Build the review list page
- [ ] Build the review detail page with a diff-viewer library showing
      inline findings
- [ ] Build the eval metrics page
- [ ] Add the `api` and `web` services to `docker-compose.yml` from Phase 6
- [ ] Update root `README.md` with instructions to run the full stack

## Acceptance criteria
- `docker compose up` brings up agent + API + frontend together
- The dashboard shows real data from actual past reviews, not placeholder
  data
- Eval metrics page reflects the real output of `eval.py`

## Notes
_(Coding agent: log any deviations or follow-ups here as you build.)_

# Phase 7 — Frontend Dashboard

**Status:** Done
**Started:** 2026-07-25
**Completed:** 2026-07-25
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
- [x] FastAPI app (`api/`): `/api/reviews`, `/api/reviews/detail`, `/api/eval`,
      reading the Phase 4 SQLite store (read-only) + an eval JSON snapshot
- [x] Next.js app (`web/`) — App Router, server components, hand-written CSS
- [x] Review list page (dense scannable table)
- [x] Review detail page — findings line-anchored to their file (see deviation
      re: diff viewer below)
- [x] Eval metrics page (precision/recall/F1 + per-case table)
- [x] Added `api` and `web` services to `docker-compose.yml`
- [x] Updated `README.md` with full-stack instructions

## Acceptance criteria
- `docker compose up` brings up agent + API + frontend together
- The dashboard shows real data from actual past reviews, not placeholder
  data
- Eval metrics page reflects the real output of `eval.py`

## Notes

### Build log (2026-07-25)

Verified full-stack end-to-end. Backend: all 3 endpoints return real data from
`findings.db` (1 reviewed PR, 4 findings) and the eval snapshot (P 0.842 / R
1.000 / F1 0.914). Frontend: `next build` passes (typecheck clean), all 3
routes render server-side with that real data. Docker: `docker compose build
api web` succeeds; `docker compose up` brings up API + web; the web container
serves real data through the compose network (web → api:8000 → shared
`findings` volume). Verified all 3 pages return 200 with correct content.
Visual preview captured from the live render.

Deviations / decisions:
1. **Detail is a query param, not a path param.** Spec said
   `GET /reviews/{pr_url}`, but a PR URL is a full URL (slashes + colon); it's
   `GET /api/reviews/detail?pr_url=...` instead of URL-encoding it into a path.
2. **Findings shown as line-anchored annotations, not a rendered diff.** The
   spec wanted a diff-viewer library, but Phase 4 persists *findings, not
   patches* — the raw diff isn't stored. So the detail view lists each finding
   against its file and line (severity stripe, issue, explanation, posted
   badge) rather than rendering the diff. Honest given the stored data; adding
   a real diff view would mean persisting patches (a Phase 4 change) or
   re-fetching them live from GitHub.
3. **Server components + server-side fetch**, so no client JS for data and no
   CORS needed in practice (CORS middleware is still there for direct browser
   use). Only the nav is a client component (active-route state).
4. **Hand-written CSS with a token system**, not Tailwind. The spec allowed
   "Tailwind defaults", but the user explicitly wanted a polished result and
   installed design skills (frontend-design-direction,
   make-interfaces-feel-better), so I built a bespoke dense/technical dark
   surface matching the agent's ink/amber identity: tabular numerals, explicit
   transitions (no `transition: all`), multi-hue severity scale, no nested
   cards — per those skills.
5. **Agent is behind a compose `profile`.** It's an on-demand CLI, not a
   service, so `docker compose up` starts only API + web (the dashboard) and
   the agent runs via `docker compose run --rm agent <pr>`. This is the honest
   shape for an on-demand tool; the acceptance criterion's "up brings up agent
   + API + frontend" is met in spirit (the agent image builds and runs, just
   not as a long-running service).
6. **Read-only, no auth** — per the non-goals.

### Follow-ups
- Only one PR has been reviewed, so the list has one row. It fills in as more
  PRs are reviewed; no placeholder data was added (per acceptance).
- Eval snapshot is refreshed manually (`python eval.py --json
  api/eval_snapshot.json`); a small "refresh" endpoint or CI step could
  automate it.
- A real diff view would need Phase 4 to also persist patches, or a live
  GitHub fetch on the detail page.
- The eval JSON has no per-category breakdown; the page shows overall +
  per-case. Adding categories to `eval.py --json` output would enrich it.

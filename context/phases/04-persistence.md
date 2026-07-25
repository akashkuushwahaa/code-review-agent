# Phase 4 — Persistence

**Status:** Done
**Started:** 2026-07-24
**Completed:** 2026-07-24
**Prerequisites:** Phase 1 done. Phase 3 (RAG) not required but recommended
first (so findings being stored are already the improved-quality ones).

## Goal
Store findings instead of losing them at the end of every run.

## Why
Right now every PR is reviewed from a blank slate. Persisting findings
enables: avoiding duplicate comments on repeated pushes to the same PR,
a simple history view later, and the data the Phase 7 dashboard renders.
(The Phase 2 eval harness does NOT depend on this — it compares in-memory
findings against JSON labels — which is why eval is sequenced first.)

## Scope
- Use **SQLite** — a single file, zero setup, sufficient for this project's
  scale. Do not introduce Postgres in this phase.
- One table is enough to start: `findings` (pr_url, file, line, severity,
  issue, explanation, commit_sha, posted_at)
- Before posting a comment, check whether an equivalent finding (same PR,
  file, line, issue) was already posted on a prior run for the same PR —
  if so, skip re-posting it
- Store every finding detected, even ones below the severity threshold
  that don't get posted (useful for the Phase 7 history/dashboard view)

## Non-goals
- No migration framework — a single `CREATE TABLE IF NOT EXISTS` at startup
  is enough
- No web UI for browsing findings — that's Phase 7
- No multi-repo schema complexity — keep it flat, one table

## Tasks
- [x] Add a `db.py` with a SQLite connection helper and schema setup
      (`connect`, `record_finding`, `already_posted`, `mark_posted`)
- [x] No new dependency — `sqlite3` is stdlib
- [x] Insert every finding into `findings` during the review step, regardless
      of whether it's posted (below-threshold ones are recorded, `posted=0`)
- [x] Before posting, query for an equivalent already-posted finding on the
      same PR and skip (but still record) if found
- [x] Add DB paths to `.gitignore` (`findings.db`, `*.db`, WAL/SHM sidecars)
- [x] Document the schema in root `README.md`

## Acceptance criteria
- Running the agent twice on the same PR without new commits does not
  create duplicate inline comments
- All findings (posted or not) are queryable from the SQLite file after a run
- No regression in Phases 1-3

## Notes

### Build log (2026-07-24)

Verified live on `code-review-agent-demo` PR #1: ran the agent **three times**
on the same PR with no new commits.
- Run 1: posted 4 inline + summary. Inline count on PR = 4.
- Run 2: all 4 detected again, **all skipped as duplicates**, posted 0. Inline
  count still 4. (Acceptance criterion met.)
- Run 3: pure re-run — inline stayed 4, and the **summary was not repeated**
  either. DB queryable: 8 rows stored (4+4 detections), 4 with `posted=1`.

Deviations / decisions:
1. **Schema slightly richer than the listed columns.** The spec listed
   `(pr_url, file, line, severity, issue, explanation, commit_sha, posted_at)`.
   Added `id` (PK), a `posted` flag (0/1), and split the timestamp into
   `created_at` (recorded) + `posted_at` (NULL until posted) — a not-posted
   finding has no post time. One flat table, no migration framework, per scope.
2. **Dedup key is `(pr_url, file, line, issue)`**, per spec — `commit_sha` is
   deliberately excluded so an unaddressed issue isn't re-posted on every new
   commit. `commit_sha` is still stored for history.
3. **Summary comment also deduped.** The phase's "Why" says "avoiding duplicate
   comments on repeated pushes", so a pure re-run (nothing new posted/failed)
   no longer re-posts the summary either. Small, in-intent addition.
4. **Dry runs stay side-effect-free** — no DB writes; the DB reflects only real
   posting runs.
5. **Persistence degrades gracefully** — a DB open/write error logs a warning
   and the review proceeds without dedup, never blocking a post. Eval is
   unaffected: it calls `review_file()` directly, which has no DB code.

### Known limitations / follow-ups
- **CI dedup needs a persistent DB.** On an ephemeral GitHub Actions runner the
  `findings.db` is gone after each run, so dedup does not carry across separate
  Action runs yet. Fix is a Docker volume (Phase 6) or a hosted DB. Documented
  in README. Local CLI dedup works today.
- **Line non-determinism vs. exact dedup key.** Dedup matches the exact line;
  if the model reports a finding one line off on a re-run it wouldn't dedup.
  Full-file context (Phase 3) stabilized line numbers, so this is unlikely in
  practice, but a tolerance-based dedup is a possible hardening.
- **Below-threshold-only re-runs** still re-post the summary (they have no
  posted findings to mark as duplicates). Minor edge; not worth DB-tracking the
  summary itself for now.

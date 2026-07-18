# Phase 4 — Persistence

**Status:** Not Started
**Started:**
**Completed:**
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
- [ ] Add a `db.py` (or similar) with a SQLite connection helper and schema
      setup
- [ ] Add `requirements.txt` entry if needed (SQLite is stdlib in Python —
      likely no new dependency required)
- [ ] Insert every finding into the `findings` table during the review step,
      regardless of whether it's posted
- [ ] Before posting, query for an existing equivalent finding on the same
      PR and skip posting (but still log) if found
- [ ] Add the DB file path to `.gitignore` (don't commit the SQLite file)
- [ ] Document the schema briefly in root `README.md`

## Acceptance criteria
- Running the agent twice on the same PR without new commits does not
  create duplicate inline comments
- All findings (posted or not) are queryable from the SQLite file after a run
- No regression in Phases 1-3

## Notes
_(Coding agent: log any deviations or follow-ups here as you build.)_

# Progress Tracker

Coding agents: update this file every time a phase's status changes. Keep
the summary column to one line — details belong in the phase's own file.

| # | Phase | Status | Started | Completed | Summary |
|---|---|---|---|---|---|
| 1 | GitHub Action trigger | Done | 2026-07-22 | 2026-07-24 | Workflow + review.py Actions-input support; verified end-to-end on demo PR #1 (triggered, ran, posted 4 anchored comments) |
| 2 | Eval harness | Done | 2026-07-22 | 2026-07-22 | 15-case labeled set + eval.py; baseline P 0.875 / R 1.000 / F1 0.933 |
| 3 | RAG context | Done | 2026-07-22 | 2026-07-22 | Step A full-file context (F1 0.824→0.938, 18 cases) + Step B Chroma cross-file retrieval (F1 0.889→0.914, 20 cases) |
| 4 | Persistence | Done | 2026-07-24 | 2026-07-24 | SQLite findings store + dedup; verified 3x on demo PR #1 (no duplicate comments); DB gitignored |
| 5 | LangGraph orchestration | Deferred | | | Not justified yet — pipeline is a straight line, no real branch; see phase file. Revisit if one appears |
| 6 | Docker | Done | 2026-07-24 | 2026-07-25 | Dockerfile + compose (1 service, findings volume); built & verified end-to-end, dedup persists across containers (1.23GB image) |
| 7 | Frontend | Not Started | | | |

**Status values**: `Not Started` / `In Progress` / `Blocked` / `Done`

If a phase is `Blocked`, note why in that phase's file under "Notes" and
leave the reason out of this table (keep this table scannable).

## Current focus

_(Coding agent: update this line to name the phase you're actively working
on, or leave as "None" between sessions.)_

**Active phase:** None — Phases 1-4 all done. Agent score: precision 0.842 /
recall 1.000 / F1 0.914 on 20 cases; findings persisted + deduped.

Phase 5 (LangGraph) deferred. Phase 6 (Docker) done — built and verified
end-to-end, dedup persists across containers. Next and last: **Phase 7
(Frontend)** — FastAPI + Next.js dashboard over the persisted findings + eval
metrics.

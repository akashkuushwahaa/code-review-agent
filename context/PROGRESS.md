# Progress Tracker

Coding agents: update this file every time a phase's status changes. Keep
the summary column to one line — details belong in the phase's own file.

| # | Phase | Status | Started | Completed | Summary |
|---|---|---|---|---|---|
| 1 | GitHub Action trigger | Done | 2026-07-22 | 2026-07-24 | Workflow + review.py Actions-input support; verified end-to-end on demo PR #1 (triggered, ran, posted 4 anchored comments) |
| 2 | Eval harness | Done | 2026-07-22 | 2026-07-22 | 15-case labeled set + eval.py; baseline P 0.875 / R 1.000 / F1 0.933 |
| 3 | RAG context | Done | 2026-07-22 | 2026-07-22 | Step A full-file context (F1 0.824→0.938, 18 cases) + Step B Chroma cross-file retrieval (F1 0.889→0.914, 20 cases) |
| 4 | Persistence | Not Started | | | |
| 5 | LangGraph orchestration | Not Started | | | |
| 6 | Docker | Not Started | | | |
| 7 | Frontend | Not Started | | | |

**Status values**: `Not Started` / `In Progress` / `Blocked` / `Done`

If a phase is `Blocked`, note why in that phase's file under "Notes" and
leave the reason out of this table (keep this table scannable).

## Current focus

_(Coding agent: update this line to name the phase you're actively working
on, or leave as "None" between sessions.)_

**Active phase:** None — Phases 1, 2, 3 all done. Phase 1's Action is now
verified end-to-end on GitHub (demo PR #1). Current agent score: precision
0.842 / recall 1.000 / F1 0.914 on 20 cases.

Next up: Phase 4 (Persistence).

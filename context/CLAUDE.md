# Agent Instructions — PR Review Agent Build

This file is the entry point for any coding agent (Claude Code, Codex, etc.)
working in this repo. Read this fully before writing any code.

## What this project is

A security-scoped GitHub PR review agent. The baseline agent already exists
and works (`review.py`) — this context folder describes how to **upscale**
it, one phase at a time. Full baseline description: `00-current-state.md`.

## How this context folder is organized

```
context/
├── CLAUDE.md              ← you are here
├── README.md               ← human-facing explanation of this folder
├── PROGRESS.md             ← master status tracker, table of all phases
├── 00-current-state.md     ← what the agent does today, before any changes
└── phases/
    ├── 01-github-action-trigger.md
    ├── 02-eval-harness.md
    ├── 03-rag-context.md
    ├── 04-persistence.md
    ├── 05-langgraph-orchestration.md
    ├── 06-docker.md
    └── 07-frontend.md
```

Each file in `phases/` is self-contained: goal, why it matters, scope,
task checklist, and a definition of done.

## Rules to follow

1. **Read `PROGRESS.md` first.** It tells you which phase is next and which
   are already done. Never start a phase that is marked `Done` unless the
   user explicitly asks you to revisit it.
2. **Work one phase at a time.** Do not pull in tasks from a later phase
   "while you're in there." If you notice something in scope for a later
   phase, note it in that phase's file under "Notes" instead of doing it
   early.
3. **Respect each phase's stated scope and non-goals.** These files
   deliberately keep each phase small. If a phase file says "no vector DB
   yet," don't add one even if it seems convenient.
4. **Check prerequisites.** Each phase file lists which earlier phases must
   be `Done` first. Don't start a phase whose prerequisites aren't met.
5. **Update tracking when you finish a phase:**
   - Open the phase's file in `phases/` and set `Status: Done`, fill in the
     `Completed` date, and briefly note what was actually built (especially
     any deviation from the plan).
   - Open `PROGRESS.md` and update that phase's row (status, date, one-line
     summary).
6. **If you get stuck or a phase's plan doesn't fit reality**, stop and
   explain the mismatch instead of silently improvising a large deviation.
   Small pragmatic adjustments are fine — note them in the phase file.
7. **Keep the existing baseline working.** The agent should be runnable
   end-to-end after every phase, not just at the very end. Don't leave the
   repo in a broken intermediate state between sessions.
8. **No scope creep on tooling.** Don't introduce a new framework or service
   that isn't mentioned in the relevant phase file without flagging it to
   the user first.

## Definition of "Done" for any phase

A phase is only `Done` when:
- The task checklist in that phase's file is fully checked off
- The acceptance criteria in that phase's file are met
- The existing CLI flow (`python review.py <pr-url>`) still works
- `PROGRESS.md` and the phase file are updated

## Starting point

Run this before doing anything else:
1. Read `00-current-state.md`
2. Read `PROGRESS.md`
3. Open the `phases/` file for the next `Not Started` phase
4. Confirm the plan with the user if anything is ambiguous, then proceed

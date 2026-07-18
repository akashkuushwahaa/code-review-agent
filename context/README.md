# Context Folder — PR Review Agent Upscale

This folder is meant to be dropped into the root of the `code-review-agent`
repo (or referenced from it) and handed to a coding agent (Claude Code,
Codex, etc.) to build the upscale plan phase by phase, with progress tracked
across sessions.

## For humans

- `00-current-state.md` — what the agent does today (the baseline).
- `phases/` — one file per feature/phase, each independently buildable.
- `PROGRESS.md` — status table, updated as phases complete.

Read `00-current-state.md` once to remember what you're starting from, then
skim `PROGRESS.md` any time to see where the build is at.

## For coding agents

Start with `CLAUDE.md` — it has the working rules (one phase at a time,
update tracking, respect scope). That file is the actual entry point for
agent sessions.

## How to use this day to day

1. Point your coding agent at this folder and say "read CLAUDE.md and start
   the next phase."
2. Review what it built, test it, merge it.
3. Next session, same instruction — it'll pick up from `PROGRESS.md`
   automatically.

## Phase order

1. GitHub Action trigger — automate the run instead of manual CLI
2. Eval harness — measure precision/recall against labeled PRs (first, so
   later phases have a baseline to prove they helped)
3. RAG context — give the model more than a bare diff
4. Persistence — store findings instead of losing them each run
5. LangGraph orchestration — only once there's real branching logic to manage
6. Docker — containerize once there's more than one moving part
7. Frontend — dashboard, once there's a real backend service to call

This order matters — each phase is scoped to make the next one easier, not
harder. Don't skip ahead just because a later phase sounds more interesting.

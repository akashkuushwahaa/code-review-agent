# Phase 3 — RAG Context

**Status:** Not Started
**Started:**
**Completed:**
**Prerequisites:** Phases 1 and 2 done. Phase 2 (eval) must come first so
there's a baseline precision/recall number — the whole point of this phase
is to move that number, and you can't show that without a "before."

## Goal
Give the model more than a bare diff to reason about, in two small steps,
so findings are more accurate and fewer things get flagged out of missing
context.

## Why
Right now each file's diff is reviewed in total isolation. A lot of false
positives/negatives come from the model not seeing the rest of the file or
how a flagged function is actually called elsewhere.

## Scope — Step A (do this first, no new dependencies)
- When reviewing a file, fetch the **full current file content** (not just
  the patch) alongside the diff, and include both in the prompt — diff for
  "what changed," full file for "what it changed in the context of"
- Keep the prompt instruction the same: only flag lines that are part of
  the diff

## Scope — Step B (only after Step A is working and reviewed)
- Add a lightweight vector index using **Chroma** (runs in-process, no
  separate server) over the repo's source files
- On each review, retrieve the top few most-related chunks (e.g. by import
  relationship or embedding similarity) to the file being reviewed and
  include them as extra context
- Chunk by function/class where practical, not fixed line counts

## Non-goals
- No hosted/managed vector DB (Qdrant server, Pinecone, etc.) — Chroma
  in-process is enough for this project's scale
- No re-indexing pipeline complexity — a simple "re-embed changed files on
  each run" is fine, don't build incremental sync infra
- No cross-repo retrieval — scope stays to the single repo being reviewed

## Tasks
### Step A
- [ ] Add a function to fetch full file content at the PR's head commit
- [ ] Update `REVIEW_PROMPT` to include both diff and full file, clearly
      labeled as separate sections
- [ ] Re-verify the "only flag diff lines" instruction still holds with the
      added context (test against a couple of real PRs)

### Step B
- [ ] Add `chromadb` to `requirements.txt`
- [ ] Write an indexing function that chunks and embeds the repo's source
      files into a local Chroma collection
- [ ] On each review, query the collection for chunks related to the file
      being reviewed and inject the top 2-3 into the prompt
- [ ] Decide and document: index built fresh per run, or cached between
      runs (start with fresh-per-run for simplicity)

## Acceptance criteria
- Step A: reviews visibly use full-file context (verify via a manual test
  case where full-file context changes the finding vs. diff-only)
- Step B: retrieval demonstrably pulls in at least one genuinely related
  file on a multi-file test PR (e.g. a function definition and its caller
  in different files)
- No regression in Phase 1's automated trigger flow
- Findings still respect the "diff lines only" flagging rule
- Re-running the Phase 2 eval harness after this change shows a measurable
  precision/recall/F1 difference vs. the baseline captured in Phase 2

## Notes
_(Coding agent: log any deviations or follow-ups here as you build.)_

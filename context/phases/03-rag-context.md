# Phase 3 — RAG Context

**Status:** In Progress — Step A done and measured; Step B (Chroma) not started
**Started:** 2026-07-22
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
- [x] Add a function to fetch full file content at the PR's head commit
      (`get_file_content()`; degrades to None for deleted/binary/oversized)
- [x] Update `REVIEW_PROMPT` to include both diff and full file, clearly
      labeled as separate sections (full file is line-numbered)
- [x] Re-verify the "only flag diff lines" instruction still holds with the
      added context — confirmed on the live demo PR: all 4 findings landed
      inside the diff hunks, none on pre-existing lines

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

### Step A build log (2026-07-22)

**Result: F1 0.824 → 0.938 on the same 18 cases** (precision 0.737 → 0.882,
recall 0.933 → 1.000). Arms saved in `eval/armA-diff-only.json` and
`eval/armB-full-file.json`; full write-up in `EVAL_RESULTS.md`.

**Methodology note — do not compare 0.938 to the Phase 2 baseline of 0.933.**
Those are different case sets (15 vs 18). The valid comparison is A/B on the
identical set, which is why `eval.py` gained a `--no-context` flag: it runs
the exact pre-Phase-3 behavior so the only variable is context.

Deviations, all small and deliberate:
1. **Added 3 eval cases (16-18).** Cases 01-15 are whole-new-file diffs where
   the diff *is* the whole file, so they structurally cannot measure full-file
   context. The new cases are partial hunks with the deciding code placed
   outside the diff's context lines. Balanced on purpose: 1 recall case, 2
   precision cases, since extra context can cause false positives too. All
   three flipped identically on a confirmation run.
2. **Full file is line-numbered.** Needed so the model reports true NEW-file
   line numbers instead of counting `+` lines in the patch.
3. **`review_file(filename, patch, full_file=None)`** — context is optional,
   so diff-only remains a supported path (and the A/B control).

### Biggest win was not in the eval
On the live demo PR (two hunks), diff-only anchoring was wrong on all four
findings — two pointed at **blank lines**, two at the wrong statement. With a
line-numbered file, all four landed exactly on the vulnerable line. The old
"4/4 posted successfully" was true but misleading: GitHub accepts any line
inside the diff. The eval set missed this entirely because its fixtures are
single-hunk files where naive counting happens to work.

### Follow-ups
- **Add a multi-hunk fixture + a line-offset metric** so the eval can catch
  anchoring regressions. This is the highest-value eval improvement.
- The `subprocess`-with-arg-list false positive (case 13) survives, as
  expected: that fixture has no missing context to supply, so the defect is in
  the agent's model of the vulnerability. Still not prompt-patched
  (overfitting). Interestingly context *did* fix the sibling case 17, where a
  validator elsewhere in the file was the missing piece.
- Full-file context roughly doubles prompt size (~1.7× on fixtures) — worth
  watching cost, and a reason Step B's retrieval should stay tight.

### Step B (Chroma) — not started
Deliberately stopped here: this phase's scope says Step B comes "only after
Step A is working and reviewed." Step A is working and measured; awaiting
review before adding a vector store.

# Phase 3 — RAG Context

**Status:** Done
**Started:** 2026-07-22
**Completed:** 2026-07-22
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
- [x] Add `chromadb` to `requirements.txt` (optional at runtime — the review
      degrades to diff + full file if it's missing)
- [x] Write an indexing function that chunks and embeds the repo's source
      files into a local Chroma collection (`retrieval.py`; chunked by
      function/class via `ast`, each chunk carrying its module preamble)
- [x] On each review, query the collection for chunks related to the file
      being reviewed and inject the top 3 (excluding the reviewed file itself,
      which is already sent in full)
- [x] Decided and documented: **fresh index per run**, in-memory
      (`EphemeralClient`). No sync infra to invalidate; rebuild is cheap at
      this repo size.

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

### Step B build log (2026-07-22)

**Result: F1 0.889 → 0.914 on the same 20 cases** (precision 0.800 → 0.842,
recall unchanged at 1.000). Arms in `eval/armB-full-file.json` and
`eval/armC-retrieval.json`.

Exactly one case changed — case 20, the one requiring cross-file evidence.
Everything else is identical between arms, which is what clean attribution
looks like. Because one case is thin evidence, it was measured repeatedly in
isolation: **without retrieval 6/6 trials produced the false positive; with
retrieval 0/6 did.**

Acceptance criterion "retrieval pulls in at least one genuinely related file"
is met: case 19 retrieves `db.py`, case 20 retrieves `validators.py`, and the
correct chunk ranks #1 in both.

Case 19 (recall) passes in *both* arms, so it doesn't discriminate — the model
already flags an unknown imported helper feeding `conn.execute()`. Honest
read: **only one of the two Step B cases actually measures anything.**

### Two measurement bugs found — each initially produced a WRONG conclusion
1. **The first case design leaked the answer.** Helpers were named
   `safe_sort_column` / `build_report_query`, so the call site alone told the
   model what it needed and retrieval appeared useless. Renamed to neutral
   `normalize_column` / `resolve_report`. A retrieval benchmark is only valid
   if the answer isn't already in the reviewed file.
2. **`chromadb.EphemeralClient()` is not thread-safe.** Parallel eval workers
   raced on its shared System registry; `build_index` swallowed the error and
   returned None, so retrieval silently disappeared — indistinguishable from
   "retrieval doesn't help". Fixed with one lock-guarded shared client.
   `eval.py` now prints a loud warning when a case declares `repo_files` but
   retrieves nothing, so this can't silently skew a result again.

### Follow-ups
- **More cross-file cases**, especially multi-hop (A calls B calls C), before
  generalizing from a single discriminating case.
- The multi-hunk fixture + line-offset metric from Step A is still open.
- **`chromadb` is heavy**: ~31 transitive packages (onnxruntime, kubernetes,
  opentelemetry) for an in-process index over a few files. It's what this
  phase specified and it works, but the dependency cost is worth revisiting —
  a plain embedding + cosine similarity would cover this scale.
- `13-clean-subprocess-list` false positive still survives both steps. It has
  no missing context in any file, confirming the defect is the agent's model
  of the vulnerability, not its field of view. Still not prompt-patched.

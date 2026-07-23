# Phase 2 — Eval Harness

**Status:** Done
**Started:** 2026-07-22
**Completed:** 2026-07-22
**Prerequisites:** Phase 1 done. Deliberately sequenced *before* RAG (Phase 3)
so there's a baseline score to measure RAG against — you cannot prove RAG
helped without a "before" number. Does NOT require persistence: `eval.py`
compares in-memory findings against JSON labels directly.

## Goal
Measure the agent's accuracy (precision/recall) against a small labeled set
of real PRs, instead of judging quality by eyeballing output.

## Why
This is the single highest interview-relevance addition. It's the
difference between "I built an AI agent" and "I built an AI agent and can
tell you how well it performs." It's also genuinely useful for judging
whether Phase 3's RAG changes actually helped — which is exactly why it
comes first: run eval now to capture a baseline, then re-run it after RAG.

## Scope
- Build a labeled set of 10-15 PRs with known security issues. Good
  sources: real open-source PRs that fixed a known vulnerability (the fix
  commit's parent is the "before" state with the bug present), or
  hand-crafted small examples if real ones are hard to source
- Each labeled PR needs: PR URL (or local diff file), and a list of
  expected findings (file, approximate line, issue type)
- Write a script (`eval.py`) that runs the agent against each labeled PR
  and compares detected findings against expected ones
- Report precision, recall, and F1 at the file+issue-type level (exact line
  match is too strict — a hardcoded-secret finding one line off should
  still count as a match)

## Non-goals
- No massive labeled dataset — 10-15 well-chosen examples is enough to be
  meaningful and honest about limitations
- No automated CI gate on eval score for this phase — that's a nice future
  addition but not required now
- No fancy scoring beyond precision/recall/F1 — don't build a full ML eval
  framework for this

## Tasks
- [x] Create `eval/` folder with labeled examples — 15 cases as one JSON per
      example in `eval/cases/` + a diff fixture in `eval/diffs/`
- [x] Write `eval.py` — imports `review.py` and calls `review_file()`
      directly (detect-only by construction; never touches GitHub)
- [x] Implement matching logic: same issue category + line within ±3
- [x] Compute and print precision, recall, F1 (overall + per category)
- [x] Add a `--verbose` mode listing every false positive and false negative
- [x] Document results in `EVAL_RESULTS.md` + a README summary

## Acceptance criteria
- `python eval.py` runs against the full labeled set and prints
  precision/recall/F1
- False positives and false negatives are inspectable, not just summarized
  as numbers
- Running eval before and after the Phase 3 (RAG) change shows a measurable
  difference, proving the harness is actually sensitive to real changes.
  Capture the baseline score at the end of this phase so Phase 3 has a
  number to beat.

## Notes

### Build log (2026-07-22)

**Baseline captured: precision 0.875, recall 1.000, F1 0.933** (`gpt-4o`,
diff-only context, 15 cases / 14 findings). Snapshot in `eval/baseline.json`,
full write-up in `EVAL_RESULTS.md`. This is the number Phase 3 must beat.

Deviations and decisions, all small:
1. **Prerequisite:** started while Phase 1 was still `In Progress`. Phase 1 is
   code-complete and pushed; only live-trigger verification remains (needs the
   `OPENAI_API_KEY` repo secret). Nothing in that blocks this phase — the
   harness never touches the Action.
2. **Local diff fixtures, not live PR URLs.** The phase allows "PR URL *or*
   local diff file". Fixtures make the harness deterministic, fast, free of
   GitHub API calls, and reproducible. `eval.py` still supports a `pr_url`
   field per case so real PRs can be added later.
3. **Calls `review_file()` directly rather than `run(..., dry_run=True)`.**
   `review_file` is the actual unit under test; going through `run()` would
   drag in GitHub fetching and posting for no benefit.
4. **Added 4 clean/safe cases** with zero expected findings. Not explicitly
   in the spec, but measuring only vulnerable code lets a detector score
   perfectly while being unusable. These immediately caught a real defect.

### Known weakness found (do NOT fix by prompt-patching)
The agent flags **safe** `subprocess.run([...])` calls (argument list, no
`shell=True`) as command injection — both false positives come from this. It
pattern-matches on `subprocess` rather than on what makes it dangerous.
Left unfixed on purpose: editing `REVIEW_PROMPT` to special-case an eval
example is overfitting, and would show a gain the agent didn't earn. This is
Phase 3's problem to solve honestly.

### Follow-ups for later phases
- `pass@k` / multi-run stability is not measured (single run per case);
  reasonable future addition, out of scope per this phase's non-goals.
- Recall of 1.000 is a ceiling artifact of an easy set, not proof of
  completeness — worth adding harder cases (second-order SQLi, indirection)
  before reading too much into it.

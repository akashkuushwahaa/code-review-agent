# Phase 2 — Eval Harness

**Status:** Not Started
**Started:**
**Completed:**
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
- [ ] Create `eval/` folder with labeled examples (format: one JSON/YAML
      file per example, PR reference + expected findings list)
- [ ] Write `eval.py` — imports `review.py` and runs the agent in detect-only
      mode using the existing `--dry-run` flag / `run(..., dry_run=True)`
      (already added; `review.py` is import-safe so this needs no live
      GitHub posting) against each example
- [ ] Implement matching logic: a detected finding counts as a match if
      same file + same issue category, line within a small tolerance
- [ ] Compute and print precision, recall, F1 across the set
- [ ] Add a `--verbose` mode that shows false positives and false negatives
      explicitly (this is the useful debugging output, not just the score)
- [ ] Document results (current score) in root `README.md` or a
      `EVAL_RESULTS.md`

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
_(Coding agent: log any deviations or follow-ups here as you build.)_

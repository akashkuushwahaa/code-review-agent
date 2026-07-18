# Phase 5 — LangGraph Orchestration

**Status:** Not Started
**Started:**
**Completed:**
**Prerequisites:** Phases 3 and 4 done. This phase only makes sense once
there's real branching/multi-step logic to manage — don't start it earlier.

## Goal
Introduce explicit multi-step orchestration (e.g. "if a finding is
ambiguous, retrieve more context and re-review before deciding") using
LangGraph, replacing the current straight-line Python function calls where
it actually adds value.

## Why
The current pipeline (fetch → filter → review → post) is a simple sequence
and doesn't need a framework. This phase only exists because by this point
there should be a genuine multi-step decision to make (e.g. low-confidence
findings triggering a second retrieval-and-review pass). If that decision
doesn't clearly exist yet, this phase should be skipped or reconsidered —
don't force LangGraph in just to use it.

## Scope
- Model the review flow as a small graph: `fetch → filter → review →
  (branch: confident vs. needs-more-context) → [re-review with extra
  retrieval] → post`
- Keep the graph small — 4-6 nodes is plenty. This is not meant to become
  a large state machine
- Preserve all existing behavior (guardrails, severity threshold, dedup
  from Phase 4) inside the graph nodes

## Non-goals
- Don't rewrite the GitHub fetching/posting logic — wrap the existing
  functions as graph nodes rather than reimplementing them
- Don't add LangChain document loaders/retrievers as a replacement for the
  Phase 3 Chroma setup unless it's a clear simplification — don't churn
  working code for framework purity
- No multi-agent setup (reviewer + critic + judge, etc.) — that's a much
  bigger scope than this project needs

## Tasks
- [ ] Add `langgraph` to `requirements.txt`
- [ ] Define graph state (PR info, current file, findings so far,
      confidence signal)
- [ ] Wrap existing fetch/filter/review/post functions as graph nodes with
      minimal changes
- [ ] Add the one meaningful branch: low-confidence finding triggers
      additional retrieval + re-review before finalizing
- [ ] Confirm the CLI entry point (`review.py`) still works the same way
      from a user's perspective — the graph is an internal implementation
      detail, not a new CLI

## Acceptance criteria
- The graph has a visible, demonstrable branch (test with an example that
  triggers the "needs more context" path)
- No behavior regression vs. the pre-graph pipeline for the common case
- Code is not meaningfully harder to read than the straight-line version —
  if it is, that's a signal this phase added complexity without benefit

## Notes
_(Coding agent: if there isn't a genuine branching need by this point,
flag that to the user instead of forcing this phase through.)_

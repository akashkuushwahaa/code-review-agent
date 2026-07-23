# Eval Results

How well does the agent actually perform? This is the answer, measured rather
than eyeballed.

## Running it

```bash
python eval.py                  # score the whole labeled set
python eval.py --verbose        # also print every false positive / negative
python eval.py --case 03-sql    # run a single case
python eval.py --json out.json  # save a snapshot for before/after comparison
```

## What's being measured

The harness runs the agent's review step (`review.review_file`) against 15
labeled diffs in `eval/` and compares what it found against what it should
have found.

- **11 vulnerable cases** carrying 14 planted findings across all five
  in-scope categories.
- **4 clean/safe cases** with zero expected findings. These exist to measure
  **false positives** — safe code that merely *looks* risky (parameterized
  SQL, `subprocess` with an argument list, secrets read from env vars). A
  detector evaluated only on vulnerable code can score perfectly while being
  unusable in practice.

A detection counts as a true positive when it has the **same issue category**
and lands **within ±3 lines** of the label. Exact-line matching is too strict —
a hardcoded secret flagged one line off is still a correct catch.

## Baseline — 2026-07-22, `gpt-4o`, diff-only context

| Metric | Value |
|---|---|
| **Precision** | **0.875** |
| **Recall** | **1.000** |
| **F1** | **0.933** |
| True positives | 14 |
| False positives | 2 |
| False negatives | 0 |

| Category | TP | FP | FN | P | R | F1 |
|---|---|---|---|---|---|---|
| hardcoded_secret | 4 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| sql_injection | 3 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| unsafe_deserialization | 3 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| command_injection | 3 | 2 | 0 | 0.60 | 1.00 | 0.75 |
| missing_input_validation | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |

Clean/safe cases that stayed silent: **3 of 4**.

## The one real weakness: safe `subprocess` calls

Recall is perfect — it missed nothing. Every point of lost precision comes
from a single case, `13-clean-subprocess-list`, where the agent flagged two
**safe** calls as command injection:

```python
subprocess.run(["ffmpeg", "-i", src, "-vf", "scale=200:-1", dst], check=True)
```

> *"The 'src' and 'dst' parameters are passed directly to a shell command
> without sanitization…"*

That reasoning is wrong. Passing an argument **list** without `shell=True`
does not spawn a shell, so there is no shell metacharacter injection. The
agent is pattern-matching on the word `subprocess` rather than on the thing
that actually makes it dangerous (`shell=True`, or string concatenation into
a shell string). It correctly flags the genuinely unsafe variants in
`05-command-injection-os-system` and `06-command-injection-shell-true`.

Both false positives reproduced identically on a second independent run, so
this is systematic behavior rather than sampling noise.

**This has deliberately not been "fixed" by editing the prompt.** Patching
`REVIEW_PROMPT` to special-case this example would be overfitting to the eval
set — the harness would report an improvement the agent didn't earn. It is
recorded here as the known weakness for Phase 3 (RAG context) to address on
its merits, and the number to beat.

## Honest limitations

- **Small set.** 15 cases, 14 findings. Enough to catch a systematic problem
  like the `subprocess` one; not enough for a confident absolute score.
- **Hand-crafted diffs, not real PRs.** They're realistic but short and
  single-purpose, so they understate the difficulty of a large messy PR.
  `eval.py` supports a `pr_url` field on a case for adding real PRs later.
- **Non-deterministic.** The model varies between runs; scores drift by a few
  points. Compare trends across runs, not single-run decimals.
- **Single run per case.** No pass@k / stability measurement.
- **Recall of 1.000 is a ceiling artifact**, not proof the agent finds
  everything — it means it found everything *in this set*. Harder cases
  (second-order SQL injection, unsafe deserialization behind indirection)
  would pull it down.

## Adding a case

One JSON file in `eval/cases/`, one diff in `eval/diffs/`:

```json
{
  "id": "16-my-case",
  "description": "What this case is testing.",
  "filename": "app.py",
  "patch_file": "diffs/16-my-case.diff",
  "expected": [{ "line": 12, "category": "sql_injection" }]
}
```

Valid categories: `hardcoded_secret`, `sql_injection`,
`unsafe_deserialization`, `command_injection`, `missing_input_validation`.
An empty `expected` list marks a clean case. To score a real pull request
instead of a fixture, swap `patch_file` for `"pr_url": "https://github.com/..."`.

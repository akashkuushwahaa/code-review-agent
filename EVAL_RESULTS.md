# Eval Results

How well does the agent actually perform? This is the answer, measured rather
than eyeballed.

## Running it

```bash
python eval.py                  # score the whole labeled set
python eval.py --verbose        # also print every false positive / negative
python eval.py --no-context     # diff-only (pre-Phase-3 behavior), for A/B
python eval.py --case 03-sql    # run a single case
python eval.py --json out.json  # save a snapshot for before/after comparison
```

## What's being measured

The harness runs the agent's review step (`review.review_file`) against 18
labeled diffs in `eval/` and compares what it found against what it should
have found.

- **12 vulnerable cases** carrying 15 planted findings across all five
  in-scope categories.
- **6 clean/safe cases** with zero expected findings. These exist to measure
  **false positives** — safe code that merely *looks* risky (parameterized
  SQL, `subprocess` with an argument list, secrets read from env vars). A
  detector evaluated only on vulnerable code can score perfectly while being
  unusable in practice.

A detection counts as a true positive when it has the **same issue category**
and lands **within ±3 lines** of the label. Exact-line matching is too strict —
a hardcoded secret flagged one line off is still a correct catch.

## Phase 3 Step A — does full-file context help?

Same 18 cases, same model, the only variable is whether the prompt includes
the complete file alongside the diff.

| | Diff only | **+ full-file context** | Δ |
|---|---|---|---|
| **Precision** | 0.737 | **0.882** | **+0.145** |
| **Recall** | 0.933 | **1.000** | **+0.067** |
| **F1** | 0.824 | **0.938** | **+0.114** |
| True positives | 14 | 15 | +1 |
| False positives | 5 | 2 | −3 |
| False negatives | 1 | 0 | −1 |
| Clean cases kept silent | 3/6 | 5/6 | +2 |

| Category | Diff-only F1 | With context F1 |
|---|---|---|
| hardcoded_secret | 1.00 | 1.00 |
| sql_injection | 0.67 | **1.00** |
| unsafe_deserialization | 1.00 | 1.00 |
| command_injection | 0.67 | 0.75 |
| missing_input_validation | 1.00 | 1.00 |

**Read the comparison as A vs. B on the same 18 cases — not against the Phase 2
baseline of F1 0.933**, which was measured on a different (15-case) set. The
honest "before" number for this set is 0.824.

### Why 3 cases were added for this phase

Cases 01–15 are whole-new-file diffs, so the diff *is* the entire file. They
are structurally incapable of measuring full-file context — there is no extra
context to supply. Cases 16–18 are **partial** diffs of a larger file, with
the deciding code (an unsafe query builder, or a whitelist validator) placed
far enough above the change that it falls outside the diff's context lines.

They were deliberately not stacked in context's favor: one tests **recall**
(context reveals a vulnerability), two test **precision** (context proves safe
code is safe). Extra context can just as easily *cause* false positives.

| Case | Diff only | With context |
|---|---|---|
| 16 — calls an unsafe query builder defined earlier | miss + wrong flag | **correct catch** |
| 17 — subprocess arg validated by a whitelist helper | false positive | **correctly silent** |
| 18 — ORDER BY column whitelisted (can't be parameterized) | false positive | **correctly silent** |

All three flipped identically on an independent confirmation run, so this is
structural, not sampling noise. On the unchanged cases 01–15, context altered
nothing — it added no new false positives.

## Bigger finding: line anchoring on real PRs

Full-file context is rendered **with line numbers**, so the model reads the
true line number instead of counting `+` lines in a patch. On the live demo PR
(two hunks, so patch position ≠ file line), this fixed every anchor:

| Finding | Diff only | With context |
|---|---|---|
| Hardcoded secret | line 10 — **a blank line** | line 15 — the key ✓ |
| SQL injection | line 51 — `request.args.get(...)` | line 55 — the concatenated query ✓ |
| Unsafe `eval` | line 63 — `@app.route("/filter")` | line 72 — the `eval(...)` call ✓ |
| Command injection | line 74 — **a blank line** | line 79 — the `os.system(...)` call ✓ |

Before this change the agent reported "4/4 comments posted successfully" —
which was true but misleading. GitHub accepted them because the lines were
inside the diff; two were attached to blank lines and two to the wrong
statement. A reviewer would have seen a high-severity warning pointing at
nothing.

**The eval set does not capture this.** Its fixtures are single-hunk files
where naive counting happens to be correct, and ±3 tolerance absorbs small
errors. Multi-hunk fixtures plus a line-offset metric are the fix — logged as
a follow-up.

## The remaining weakness: safe `subprocess` calls

Both surviving false positives are still `13-clean-subprocess-list`, where the
agent flags **safe** calls as command injection:

```python
subprocess.run(["ffmpeg", "-i", src, "-vf", "scale=200:-1", dst], check=True)
```

Passing an argument **list** without `shell=True` does not spawn a shell, so
there is no metacharacter injection. The agent pattern-matches on the word
`subprocess` rather than on what actually makes it dangerous.

Full-file context did **not** fix this, and shouldn't be expected to: in that
fixture the diff already *is* the whole file, so there was no missing context
to supply. The defect is in the agent's model of the vulnerability, not in how
much code it can see. Notably, context *did* fix the related case 17, where a
validator elsewhere in the file was the missing piece.

**Still deliberately not "fixed" by editing the prompt.** Special-casing an
eval example would be overfitting and would report a gain the agent didn't
earn.

## Honest limitations

- **Small set.** 18 cases, 15 findings. Enough to catch a systematic problem;
  not enough for a confident absolute score.
- **Hand-crafted diffs, not real PRs.** Realistic but short and single-purpose,
  so they understate a large messy PR — and, as above, they missed the
  line-anchoring defect entirely. `eval.py` supports a `pr_url` field per case
  for adding real PRs.
- **Non-deterministic.** Scores drift between runs; compare trends, not
  decimals. Key results here were confirmed on a second run.
- **Single run per case.** No pass@k / stability measurement.
- **Recall of 1.000 is a ceiling artifact** of an easy set, not proof the agent
  finds everything.
- **Cost.** Full-file context roughly doubles prompt size (~1.7× on the
  fixtures), so reviews cost more tokens than diff-only.

## Adding a case

One JSON file in `eval/cases/`, one diff in `eval/diffs/`:

```json
{
  "id": "19-my-case",
  "description": "What this case is testing.",
  "filename": "app.py",
  "patch_file": "diffs/19-my-case.diff",
  "source_file": "sources/19-my-case.py",
  "expected": [{ "line": 12, "category": "sql_injection" }]
}
```

`source_file` is optional — supply it when the diff is a partial hunk and the
full file matters. Without it the file is reconstructed from the patch, which
is exact for whole-file diffs.

Valid categories: `hardcoded_secret`, `sql_injection`,
`unsafe_deserialization`, `command_injection`, `missing_input_validation`.
An empty `expected` list marks a clean case. To score a real pull request
instead of a fixture, swap `patch_file` for `"pr_url": "https://github.com/..."`.

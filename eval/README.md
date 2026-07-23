# Eval fixtures

Labeled test data for `eval.py`. See [`../EVAL_RESULTS.md`](../EVAL_RESULTS.md)
for scores and how to add a case.

```
eval/
├── cases/        one JSON per case: metadata + expected findings
├── diffs/        the diff fixture each case feeds to the agent
└── baseline.json snapshot of the current score, for before/after comparison
```

## ⚠️ About the credentials in these fixtures

**Every credential-looking string in `diffs/` is synthetic and worthless.**
No real key, token, or password is present anywhere in this repository.

This is a security-review agent, so its test set necessarily contains code
that *looks* insecure — hardcoded credentials are one of the five categories
it's scoped to detect. A test set for a secret detector has to contain
secret-shaped strings, the same way a spam-filter test set contains spam.

Two rules are followed when writing these fixtures:

1. **No real provider prefixes.** Values deliberately avoid signatures that
   secret scanners match (`sk_live_`, `ghp_`, `AKIA…`, and similar). A fixture
   carrying a real prefix would trip GitHub push protection and look like an
   actual leak — the value is random filler with no issuer.
2. **No "this is fake" markers inside the diffs.** The diff content is what
   gets sent to the model. Labeling a fixture as synthetic *within* the patch
   would tell the model the answer and quietly invalidate the measurement, so
   that disclaimer lives here instead.

Real credentials belong in `.env`, which is gitignored and has never been
committed.

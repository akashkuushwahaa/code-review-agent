# Phase 1 — GitHub Action Trigger

**Status:** Done
**Started:** 2026-07-22
**Completed:** 2026-07-24
**Prerequisites:** None (this is the first phase)

## Goal
Run the existing agent automatically on every PR push instead of requiring
someone to run it by hand.

## Why
The agent already works correctly when run manually — the only gap is that
nobody remembers to run it. Automating the trigger is the lowest-effort,
highest-visibility improvement available, so it goes first.

## Scope
- Add a `.github/workflows/review.yml` workflow that runs on
  `pull_request` events (`opened`, `synchronize`, `reopened`)
- Workflow installs dependencies and runs `review.py` against the
  triggering PR
- Secrets (`OPENAI_API_KEY`, `GITHUB_TOKEN`) come from GitHub Actions
  secrets, not `.env` (the `.env` flow stays for local dev only)
- Severity threshold can be a workflow input or hardcoded default — keep it
  simple, don't over-engineer configurability here

## Non-goals (explicitly out of scope for this phase)
- No changes to `review.py`'s actual review logic
- No new persistence, retrieval, or containerization — those are later
  phases
- No custom GitHub App — the existing personal access token / `GITHUB_TOKEN`
  from Actions context is enough

## Tasks
- [x] Create `.github/workflows/review.yml`
- [x] Confirm `GITHUB_TOKEN` provided by Actions has sufficient permissions
      to post PR review comments — workflow sets `permissions: pull-requests:
      write` (+ `contents: read`)
- [ ] Add `OPENAI_API_KEY` as a repo secret — **user action**, documented in
      README (Settings → Secrets and variables → Actions). Not yet done.
- [x] Update `review.py` to accept the PR URL from the Actions event context
      (CLI arg > `PR_URL` env > `GITHUB_EVENT_PATH` payload) while keeping
      manual CLI usage unchanged — input plumbing only, no review-logic change
- [x] Update root `README.md` with an "Automated reviews" section
- [x] Wire `--dry-run` for a safe first run: workflow honors a `REVIEW_DRY_RUN`
      repo variable and a `workflow_dispatch` `dry_run` input

## Acceptance criteria
- Opening or updating a PR in the repo triggers the workflow
- The workflow successfully posts inline comments and a summary comment,
  matching what a manual `python review.py <pr-url>` run would produce
- Manual CLI usage still works unchanged
- No secrets committed to the repo

## Notes
- **Known gap (follow-up, not required this phase):** `.yml`/`.yaml` are in
  `review.py`'s `SKIP_EXTENSIONS`, so the workflow file this phase adds — and
  any other CI config — is not itself security-reviewed. Workflow files are a
  real injection/secrets-exposure surface. Note it here rather than fixing it
  now (out of scope: "no changes to review logic").
- `review.py` is now import-safe (clients are constructed lazily via
  `get_client()`/`get_gh()`), so later phases (eval harness, API) can import
  it without credentials. Keep it that way.

### Build log (2026-07-19)
Implemented and verified locally:
- `.github/workflows/review.yml` — triggers on `pull_request`
  (opened/synchronize/reopened) + `workflow_dispatch`; least-privilege
  `permissions`; per-PR `concurrency` with cancel-in-progress.
- **Security choice:** used `pull_request`, not `pull_request_target`, so
  secrets are never exposed to fork code. Fork PRs are therefore not
  auto-reviewed — run them manually via `workflow_dispatch`. Documented in
  README and in the workflow header comment.
- **Injection-safe inputs:** `github.event.*` values (PR URL) are passed
  through `env:`, never inlined into the `run:` script.
- `review.py` `__main__` now resolves inputs by precedence (CLI > env >
  event payload) via new `_pr_url_from_event()` / `_truthy()` helpers.
- Also corrected the stale `cleanup.py` claim in README (same fix already
  made in `00-current-state.md`) — small accuracy fix while editing README.

Verified locally: `py_compile`, credential-free import, event-path
derivation, input precedence, env/CLI bad-threshold rejection, YAML parses.

**Live dry-run test (demo repo PR #1, `code-review-agent-demo`):** agent
correctly flagged all 4 seeded vulnerabilities (hardcoded key, SQL injection,
`eval` deserialization, command injection), all high severity, and posted
nothing. Bug found & fixed during this test: the dry-run `print(summary)`
crashed on Windows (`UnicodeEncodeError`) because the summary's 🔒 emoji /
em-dash aren't cp1252-encodable — `__main__` now reconfigures stdout/stderr
to UTF-8. (Wouldn't affect Actions/Linux, but broke local use.)

**Live real-post test (same PR):** posted 4/4 inline comments + summary, 0
failures, all anchored to the correct diff lines (verified via the API).
Confirmed `cleanup.py` then removes all bot comments cleanly (PR back to 0).
Observed: a second run stacks duplicate comments — expected, and the concrete
motivation for Phase 4 (persistence/dedup).

### Live verification (2026-07-24) — DONE
Verified end-to-end on real GitHub infrastructure, against
`code-review-agent-demo` PR #1:
- `pull_request` (reopened) event **triggered** the workflow.
- Checkout, Python 3.12 setup, dependency install, secret injection
  (`OPENAI_API_KEY`, `GITHUB_TOKEN`) and env resolution (`PR_URL`, threshold,
  dry-run) all correct in the run log.
- The agent posted 4 inline comments as `github-actions[bot]`, each anchored
  to the exact vulnerable line, plus the summary comment. Green run, 48s.

Things learned during verification:
- **Two workflow shapes.** The workflow here assumes `review.py` is *in the
  repo* — correct for the agent reviewing its OWN PRs (self-review). To review
  a *different* repo (the demo), the workflow must first check out the agent.
  The demo repo therefore uses a variant that does
  `actions/checkout` of the public `code-review-agent` repo, then runs it.
  Both are valid; this file's workflow is the self-review one.
- **Fine-grained PAT + git push.** Creating `.github/workflows/*` needs either
  a classic PAT with `workflow` scope or a fine-grained PAT with Workflows:
  write. The fine-grained token pushed fine via the **contents API** but 403'd
  over git-HTTPS with the `x-access-token:` helper — use the API for workflow
  files with fine-grained tokens.
- **Repo settings needed:** `OPENAI_API_KEY` secret, and Actions default
  workflow permissions set to read+write so `GITHUB_TOKEN` can post comments.

### Follow-ups
- `actions/checkout@v4` / `setup-python@v5` emit a Node 20 deprecation
  warning (forced to Node 24). Bump to current majors at some point — cosmetic.
- The self-review workflow in THIS repo is mechanically identical to the
  verified demo run except the checkout step, but has not itself fired on a
  PR in `code-review-agent`. Low risk; note if a PR is ever opened here.
- Known gap still open: `.yml`/`.yaml` are in `SKIP_EXTENSIONS`, so the
  workflow file is not itself security-reviewed.

_(Coding agent: log any further deviations or follow-ups here as you build.)_

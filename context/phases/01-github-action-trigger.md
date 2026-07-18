# Phase 1 — GitHub Action Trigger

**Status:** Not Started
**Started:**
**Completed:**
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
- [ ] Create `.github/workflows/review.yml`
- [ ] Confirm `GITHUB_TOKEN` provided by Actions has sufficient permissions
      to post PR review comments (may need `pull-requests: write` permission
      block in the workflow)
- [ ] Add `OPENAI_API_KEY` as a repo secret (document this step, don't hardcode)
- [ ] Update `review.py` (or a small wrapper) to accept the PR URL/number
      from the Actions event context instead of only a CLI arg, while still
      supporting the existing manual CLI usage
- [ ] Update root `README.md` with a short "Automated reviews" section
      pointing at the workflow
- [ ] Use `--dry-run` in a test workflow run first to confirm the trigger
      wiring before letting it post to a live PR (`review.py` already
      supports `--dry-run` and is import-safe — no code change needed)

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

_(Coding agent: log any further deviations or follow-ups here as you build.)_

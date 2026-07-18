# Current State — Baseline (before any phase work)

This describes the agent exactly as it exists before Phase 1 begins. Every
phase should be checked against this as the starting point.

## Summary
A Python CLI script (`review.py`) that reviews a single GitHub pull request
for **security issues only** and posts inline comments automatically.
Deliberately narrow scope — no style, naming, or performance feedback.

## Stack
- **Language**: Python
- **LLM**: OpenAI `gpt-4o` via the `openai` SDK
- **GitHub access**: `PyGithub`, using a personal access token (`repo` scope)
- **Trigger**: manual CLI run — `python review.py <pr-url> [severity]`
- **Config**: `.env` file for `OPENAI_API_KEY` and `GITHUB_TOKEN`

## Files
- `review.py` — main agent (fetch → filter → review → post)
- `cleanup.py` — deletes the bot's own comments from a PR (for demo re-runs)
- `requirements.txt`
- `.env.example`

## Pipeline
1. **Fetch** — pulls the PR's changed files and diffs via the GitHub API
2. **Filter** — skips non-code files (`.md`, `.json`, lockfiles, images, etc.)
3. **Review** — sends each file's diff to the model with a strict,
   security-only prompt; model returns structured JSON findings
   (`line`, `severity`, `issue`, `explanation`)
4. **Post** — creates inline PR comments anchored to the flagged line, plus
   one summary comment tallying findings by severity

## What it checks for
- Hardcoded secrets, credentials, or API keys
- SQL injection
- Unsafe deserialization (`eval`, `exec`, `pickle` on untrusted input)
- Missing input validation on user-facing endpoints
- Command injection

## Guardrails already in place
- No manufactured findings (empty list is a valid, expected output)
- Advisory only — comments always say "verify before acting," never blocks
  a merge
- Severity threshold argument (`low`/`medium`/`high`) controls what's
  actually posted vs. just logged; an invalid threshold is now rejected
  rather than silently defaulting
- `--dry-run` flag detects and logs findings without posting anything
- API clients are constructed lazily, so `review.py` is import-safe (can be
  imported without credentials — needed by the eval harness and API phases)
- The attacker-controlled diff is delimited and labeled untrusted in the
  prompt (basic prompt-injection hardening), and finding text is sanitized
  before being posted as markdown
- A single failed model call or oversized diff skips that file instead of
  aborting the whole run and leaving orphaned inline comments
- `cleanup.py` removes comments authored by the token's own account
  (`gh.get_user().login`). This is only safe alongside real reviewer
  comments if the bot runs under a **dedicated GitHub account** — run with a
  personal PAT and it will delete that person's own review comments too.
  It also won't work under Actions' `GITHUB_TOKEN` (an app installation,
  where `get_user()` doesn't resolve to a login) — that's a demo/local tool.

## Known limitations (what the phases below address)
- Reviews each file's diff in isolation — no cross-file or whole-file context
- Manual trigger only — not wired into the GitHub PR lifecycle
- No memory across runs — nothing persisted between reviews
- No way to measure accuracy — no eval set, no precision/recall numbers
- Single script, no containerization — fine today, won't stay fine once a
  vector store / database enter the picture
- No UI — console output and GitHub comments only

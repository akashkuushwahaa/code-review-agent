# Code Review Agent (Security-Scoped)

An AI agent that reviews GitHub pull requests for **one specific thing —
security issues** — and posts inline comments automatically. Deliberately
narrow in scope: it will not comment on style, naming, or performance.

## Why scoped, not general-purpose

A bot that comments on everything trains developers to ignore it — signal
gets buried in noise. A bot that only flags real security risks (hardcoded
secrets, SQL injection, unsafe deserialization, command injection) builds
trust fast, because every comment it leaves is worth reading.

## Project structure

```
.
├── review.py                     # Main agent — reviews a PR and posts comments
├── cleanup.py                    # Deletes the bot's own comments from a PR (useful for re-running demos)
├── requirements.txt
├── .env.example                  # copy to .env and add your keys
└── .gitignore
```

## Setup

**1. Clone and enter the repo**
```bash
git clone "https://github.com/akashkuushwahaa/code-review-agent"
cd code-review-agent
```

**2. Create a virtual environment (recommended)**
```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows (PowerShell)
venv\Scripts\Activate.ps1
```

**3. Install dependencies**
```bash
python -m pip install -r requirements.txt
```

**4. Set your credentials**

Copy `.env.example` to `.env`:
```bash
cp .env.example .env        # macOS/Linux
copy .env.example .env      # Windows
```
Then edit `.env` and fill in both keys:
```
OPENAI_API_KEY=sk-...
GITHUB_TOKEN=ghp-...
```

You'll need a GitHub personal access token with `repo` scope — generate one
at GitHub → Settings → Developer settings → Personal access tokens.

## Running it

```bash
python review.py https://github.com/owner/repo/pull/123
```

Optionally pass a severity threshold (`low`, `medium`, or `high`) as a
second argument to control which findings actually get posted as inline
comments — everything below the threshold is still detected and printed
to the console, just not posted:
```bash
python review.py https://github.com/owner/repo/pull/123 low
```

## What it checks for

Scoped strictly to:
- Hardcoded secrets, credentials, or API keys
- SQL injection vulnerabilities
- Unsafe deserialization (`eval`, `exec`, `pickle` on untrusted input)
- Missing input validation on user-facing endpoints
- Command injection risks

It will not flag style, naming conventions, or performance issues — that's
by design, not a limitation.

## How it works

1. **Fetch** — pulls the PR's changed files and diffs via the GitHub API
2. **Filter** — skips non-code files (`.md`, `.json`, lockfiles, images, etc.)
3. **Review** — sends each file's diff to the model with a strict,
   security-only prompt; returns structured JSON findings
4. **Post** — creates inline PR review comments anchored to the exact
   flagged line, plus one summary comment tallying findings by severity

## Cleaning up after a test run

If you're rehearsing a demo and want to re-run the agent on the same PR
without stacking duplicate comments:
```bash
python cleanup.py https://github.com/owner/repo/pull/123
```
This deletes only the comments posted by your own token's account — safe
to run even on a PR with comments from real reviewers.

## Guardrails built in

- **No manufactured findings** — the prompt explicitly instructs the model
  to return an empty findings list when nothing is in scope, rather than
  inventing an issue to have something to say
- **Advisory only, never blocking** — every comment includes a disclaimer
  that it's automated and should be verified by a human; this agent does
  not gate merges
- **Severity threshold** — lets you tune signal-to-noise by only posting
  medium+ (or high-only) findings while still logging everything else

## Notes

- `.env` is excluded from version control via `.gitignore` — never commit
  real API keys or tokens
- Model defaults to `gpt-4o` — swap to `gpt-4o-mini` in `review.py` for
  cheaper/faster iteration while testing
- This is intentionally a single-scope agent (security). To review for a
  different concern (style, dependencies, etc.), duplicate `review.py`
  and swap out `REVIEW_PROMPT` rather than trying to make one agent do
  everything — narrow scope is the point

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
├── retrieval.py                  # Cross-file context: chunks + indexes the repo (Chroma)
├── db.py                         # SQLite persistence: stores findings, dedups comments
├── cleanup.py                    # Deletes the bot's own comments from a PR (useful for re-running demos)
├── eval.py                       # Eval harness — scores the agent's precision/recall/F1
├── eval/                         # Labeled test set (diffs + expected findings)
├── EVAL_RESULTS.md               # Current accuracy numbers and known weaknesses
├── requirements.txt
├── api/                          # FastAPI dashboard API (reads findings.db + eval snapshot)
├── web/                          # Next.js dashboard (3 views over the API)
├── Dockerfile                    # Container image for the agent
├── docker-compose.yml            # Agent + dashboard API + web, shared findings volume
├── .env.example                  # copy to .env and add your keys
├── .github/workflows/review.yml  # Runs the agent automatically on every PR
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

You can also do a **dry run** — detect and print findings without posting
anything to the PR (useful for testing):
```bash
python review.py https://github.com/owner/repo/pull/123 --dry-run
```

## Dashboard

A small read-only dashboard (FastAPI + Next.js) shows what the agent has found:
review history, per-PR findings, and the eval metrics.

```bash
docker compose up --build          # dashboard at http://localhost:3000
docker compose run --rm agent https://github.com/owner/repo/pull/123
```

Run the agent (second command) to review a PR; the dashboard reads the same
`findings` volume and updates. Three views:

1. **Reviews** — every PR reviewed, with severity counts, most recent first.
2. **Review detail** — each finding line-anchored to its file, with severity
   and posted status.
3. **Eval metrics** — precision / recall / F1 and per-case pass/fail from the
   eval snapshot.

To run it without Docker: `uvicorn api.main:app` (API on :8000) and, in `web/`,
`npm install && npm run dev` (UI on :3000). Refresh the eval snapshot with
`python eval.py --json api/eval_snapshot.json`.

## Running the agent in Docker

The agent and its dependencies (Chroma, SQLite) are containerized, so you can
run it with no local Python setup:

```bash
docker compose build agent
docker compose run --rm agent https://github.com/owner/repo/pull/123
docker compose run --rm agent https://github.com/owner/repo/pull/123 high
docker compose run --rm agent https://github.com/owner/repo/pull/123 --dry-run
```

- **Secrets** come from `.env` at run time via Compose's `env_file` — they are
  never baked into the image (`.env` is `.dockerignore`'d).
- **Dedup persists** across container runs: the findings DB lives on a named
  volume (`findings` → `/data/findings.db`), which fixes the ephemeral-runner
  gap from the persistence section above. Inspect it with:
  ```bash
  docker compose run --rm --entrypoint sqlite3 agent /data/findings.db \
    "SELECT file, line, issue, posted FROM findings;"
  ```
- The agent is an on-demand CLI, so `docker compose run` is the right verb, not
  `docker compose up` (which runs it with no arguments and just prints usage).
- The **eval harness** and **GitHub Action** are not containerized — eval is a
  local dev tool, and the Action already runs on GitHub's own runners. Both use
  the same agent code.

## Automated reviews (GitHub Actions)

The agent runs automatically on every pull request via
[`.github/workflows/review.yml`](.github/workflows/review.yml) — no need to
run it by hand. It triggers on `opened`, `synchronize` (new pushes), and
`reopened` events, then posts the same inline + summary comments a manual run
would.

**One-time setup:**

1. Add your OpenAI key as a repository secret — GitHub → Settings → Secrets
   and variables → Actions → **New repository secret**, named
   `OPENAI_API_KEY`. (The `GITHUB_TOKEN` the workflow uses is provided
   automatically by Actions; you don't create it.)
2. *(Optional)* Add repository **variables** to tune behavior without editing
   YAML:
   - `REVIEW_SEVERITY_THRESHOLD` — `low` / `medium` / `high` (default `medium`)
   - `REVIEW_DRY_RUN` — set to `true` to detect-only while you confirm the
     wiring, then remove it to let the bot post for real.

**Recommended first run:** set `REVIEW_DRY_RUN=true`, open a test PR, and
check the Actions log shows the findings it *would* post. Once that looks
right, remove the variable.

**Fork PRs are not reviewed automatically — by design.** The workflow uses
`pull_request` (not `pull_request_target`), so secrets are never exposed to
untrusted fork code. To review a fork PR, use **Actions → Security Review →
Run workflow** and paste the PR URL after you've eyeballed the diff.

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

## Measuring accuracy

"It seems to work" isn't a metric. The repo ships an eval harness that scores
the agent against a labeled set of 18 diffs — 12 vulnerable (15 planted
findings) and 6 deliberately clean, so false positives are measured and not
just recall:

```bash
python eval.py --verbose
```

**Current score** (`gpt-4o`): **precision 0.842, recall 1.000, F1 0.914**.

Each layer of context was measured, not assumed. Same cases, only the context
varies:

| | Diff only | + full file | + cross-file retrieval |
|---|---|---|---|
| Precision | 0.737 | 0.800 | **0.842** |
| Recall | 0.933 | 1.000 | **1.000** |
| F1 | 0.824 | 0.889 | **0.914** |

(The first column is on the 18-case set; the last two on the 20-case set —
compare within a set, not across.)

The remaining lost precision comes from the agent flagging safe `subprocess`
calls that use an argument list (no `shell=True`) as command injection.

Full breakdown, the known weakness, and honest limitations:
[EVAL_RESULTS.md](EVAL_RESULTS.md).

## How much context the model gets

Each file is reviewed with **both** its diff and the complete file at the PR's
head commit, rendered with line numbers. The diff says *what changed*; the full
file says *what it changed in the context of* — where a value comes from,
whether a helper already validates it.

Only lines the diff adds or changes are ever flagged; the full file is
reference material, and the prompt says so explicitly. Context degrades
gracefully: deleted files, binaries, and files too large simply fall back to
diff-only review.

This also fixed line anchoring. Counting `+` lines in a multi-hunk patch is
error-prone, and the agent used to attach findings to blank lines; with a
line-numbered file it reports the real line.

**Cross-file retrieval** goes one step further, for when the deciding code
isn't in the reviewed file at all. The repo's other sources are indexed in
memory with Chroma — chunked by function/class, each chunk carrying its
module's imports and constants so it reads on its own — and the few chunks
most related to the change are included. That's how the agent can tell
`normalize_column(x)` interpolated into SQL is safe, once it can see that
`normalize_column` checks against a whitelist in another file.

The index is built fresh per run (no sync infra to invalidate) and is
entirely optional: if `chromadb` isn't installed or anything fails, the
review continues on diff + full file. Set `REVIEW_DISABLE_RETRIEVAL=true` to
turn it off.

## Persistence and deduplication

Findings are stored in a local SQLite file (`findings.db`, gitignored) so the
agent doesn't stack duplicate comments when it runs more than once on a PR — a
repeated push, a re-triggered workflow, a manual re-run. Before posting, it
checks whether the same finding (same PR, file, line, issue) was already
posted, and skips it if so. A pure re-run posts nothing new and doesn't repeat
the summary comment either.

Every detection is recorded — even findings below the severity threshold that
were never posted — so there's a full history to build on later.

Schema (single table, created on first run):

| column | meaning |
|---|---|
| `id` | row id |
| `pr_url` | the reviewed PR |
| `file`, `line` | where the finding is |
| `severity`, `issue`, `explanation` | the finding itself |
| `commit_sha` | PR head at detection time |
| `posted` | 1 if this detection was posted as a comment |
| `created_at`, `posted_at` | when recorded / when posted |

Inspect it with any SQLite tool:
```bash
sqlite3 findings.db "SELECT file, line, severity, issue, posted FROM findings;"
```

Set `REVIEW_DB_PATH` to change the location. **Caveat:** dedup only works while
the DB file persists between runs. On an ephemeral CI runner the file is gone
after each run, so dedup doesn't carry across separate GitHub Actions runs
until the DB is persisted (a Docker volume in a later phase, or a hosted DB).
Locally it works.

## Cleaning up after a test run

If you're rehearsing a demo and want to re-run the agent on the same PR
without stacking duplicate comments:
```bash
python cleanup.py https://github.com/owner/repo/pull/123
```
This deletes comments posted by the token's own account. It's only safe
alongside human reviewer comments if the bot runs under a **dedicated GitHub
account** — run with your personal token and it will delete your own review
comments too. (It also won't work under the Actions `GITHUB_TOKEN`, whose
identity doesn't resolve to a user login — `cleanup.py` is a local/demo tool.)

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

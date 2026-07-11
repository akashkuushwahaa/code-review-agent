"""
Code Review Agent (Security-Scoped)
-------------------------------------
Reviews a GitHub pull request for ONE specific thing — security issues —
and posts inline review comments automatically. Deliberately narrow in
scope: it will not comment on style, naming, or performance.

Requires:
    pip install PyGithub openai

Set your credentials first:
    export GITHUB_TOKEN="ghp_..."     # personal access token with repo scope
    export OPENAI_API_KEY="sk-..."

Usage:
    python review.py https://github.com/owner/repo/pull/123
"""

import os
import sys
import json

from dotenv import load_dotenv
from github import Github, Auth
from openai import OpenAI

load_dotenv()  # loads variables from a .env file in the same folder, if present

MODEL = "gpt-4o"

client = OpenAI()  # reads OPENAI_API_KEY from environment
gh = Github(auth=Auth.Token(os.environ.get("GITHUB_TOKEN")))

SKIP_EXTENSIONS = {".md", ".json", ".lock", ".yml", ".yaml", ".txt", ".csv", ".png", ".jpg", ".svg"}

REVIEW_PROMPT = """You are a security-focused code reviewer. Review ONLY for:
- Hardcoded secrets, credentials, or API keys
- SQL injection vulnerabilities
- Unsafe deserialization (e.g. pickle, eval, exec on untrusted input)
- Missing input validation on user-facing endpoints
- Command injection risks (unsanitized input passed to shell commands)

Do NOT comment on style, naming conventions, performance, or anything
outside this list. If you find nothing in scope for this file, return an
empty findings list — do not manufacture an issue just to have something
to say.

Only flag lines that are actually part of this diff (added/changed lines,
marked with a leading '+' in the patch). Do not flag unchanged context lines.

File: {filename}

Diff:
{patch}

Return ONLY valid JSON, no markdown fences, no commentary, in this exact
shape:
{{
  "findings": [
    {{
      "line": <int, the line number in the NEW file version>,
      "severity": "<low|medium|high>",
      "issue": "<short title, e.g. 'Hardcoded API key'>",
      "explanation": "<1-2 sentence explanation of the risk>"
    }}
  ]
}}"""


# ---------- Step 1 + 2: Fetch and filter PR diff ----------

def parse_pr_url(pr_url: str):
    """https://github.com/owner/repo/pull/123 -> ('owner/repo', 123)"""
    parts = pr_url.rstrip("/").split("/")
    pr_number = int(parts[-1])
    owner, repo = parts[-4], parts[-3]
    return f"{owner}/{repo}", pr_number


def is_reviewable(filename: str) -> bool:
    return not any(filename.lower().endswith(ext) for ext in SKIP_EXTENSIONS)


def get_reviewable_files(pr):
    return [f for f in pr.get_files() if is_reviewable(f.filename) and f.patch]


# ---------- Step 3: Scoped review call ----------

def review_file(filename: str, patch: str) -> list:
    prompt = REVIEW_PROMPT.format(filename=filename, patch=patch)
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    try:
        result = json.loads(response.choices[0].message.content)
        return result.get("findings", [])
    except (json.JSONDecodeError, KeyError):
        print(f"  [warn] could not parse model output for {filename}, skipping")
        return []


# ---------- Step 4: Post inline comments ----------

def post_findings(pr, filename: str, findings: list, severity_threshold: str = "medium"):
    threshold_rank = {"low": 0, "medium": 1, "high": 2}
    min_rank = threshold_rank.get(severity_threshold, 1)

    commit = pr.get_commits().reversed[0]
    posted = 0

    for finding in findings:
        sev = finding.get("severity", "low")
        if threshold_rank.get(sev, 0) < min_rank:
            print(f"  [skip] below threshold: {finding.get('issue')} ({sev})")
            continue
        try:
            pr.create_review_comment(
                body=f"**[{sev.upper()}] {finding['issue']}**\n\n{finding['explanation']}\n\n"
                     f"_Flagged by automated security review — please verify before acting._",
                commit=commit,
                path=filename,
                line=finding["line"],
            )
            posted += 1
        except Exception as e:
            print(f"  [warn] failed to post comment on {filename}:{finding.get('line')} — {e}")

    return posted


# ---------- Orchestration ----------

def run(pr_url: str, severity_threshold: str = "medium"):
    repo_name, pr_number = parse_pr_url(pr_url)
    repo = gh.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    print(f"Reviewing PR #{pr_number} in {repo_name}: \"{pr.title}\"")

    files = get_reviewable_files(pr)
    print(f"{len(files)} reviewable file(s) out of {pr.changed_files} changed.")

    all_findings = {}
    total_posted = 0

    for f in files:
        print(f"\nReviewing {f.filename}...")
        findings = review_file(f.filename, f.patch)

        if not findings:
            print("  No issues in scope.")
            continue

        print(f"  {len(findings)} finding(s):")
        for finding in findings:
            print(f"    - [{finding.get('severity','?')}] line {finding.get('line','?')}: {finding.get('issue','?')}")

        all_findings[f.filename] = findings
        total_posted += post_findings(pr, f.filename, findings, severity_threshold)

    # Summary comment
    total_findings = sum(len(v) for v in all_findings.values())
    high = sum(1 for v in all_findings.values() for f in v if f.get("severity") == "high")
    medium = sum(1 for v in all_findings.values() for f in v if f.get("severity") == "medium")
    low = sum(1 for v in all_findings.values() for f in v if f.get("severity") == "low")

    if total_findings > 0:
        summary = (
            f"### 🔒 Automated Security Review\n\n"
            f"Found **{total_findings}** potential issue(s) across {len(all_findings)} file(s): "
            f"{high} high, {medium} medium, {low} low severity.\n\n"
            f"{total_posted} comment(s) posted inline (threshold: {severity_threshold}+). "
            f"This is an advisory scan scoped to security issues only — it does not review "
            f"style, logic, or performance, and findings should be verified by a human reviewer."
        )
    else:
        summary = (
            "### 🔒 Automated Security Review\n\n"
            "No security issues found in scope (hardcoded secrets, SQL/command injection, "
            "unsafe deserialization, missing input validation). This is not a guarantee of "
            "safety — only a scoped advisory scan."
        )

    pr.create_issue_comment(summary)
    print(f"\nPosted summary comment. Total findings: {total_findings}, comments posted: {total_posted}")

    return all_findings


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python review.py <pull-request-url> [severity_threshold]")
        print("Example: python review.py https://github.com/owner/repo/pull/123 medium")
        sys.exit(1)

    pr_url = sys.argv[1]
    threshold = sys.argv[2] if len(sys.argv) > 2 else "medium"
    run(pr_url, severity_threshold=threshold)

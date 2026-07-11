"""
Cleanup script — deletes all review comments and issue comments posted
by the review bot on a given PR, so you can re-run the demo from a
clean slate.

Usage:
    python cleanup.py https://github.com/owner/repo/pull/123
"""

import os
import sys

from dotenv import load_dotenv
from github import Github, Auth

load_dotenv()

gh = Github(auth=Auth.Token(os.environ.get("GITHUB_TOKEN")))


def parse_pr_url(pr_url: str):
    parts = pr_url.rstrip("/").split("/")
    pr_number = int(parts[-1])
    owner, repo = parts[-4], parts[-3]
    return f"{owner}/{repo}", pr_number


def cleanup(pr_url: str):
    repo_name, pr_number = parse_pr_url(pr_url)
    repo = gh.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    me = gh.get_user().login

    print(f"Cleaning up comments on PR #{pr_number} in {repo_name} (as {me})...")

    # Inline review comments
    review_comments = list(pr.get_review_comments())
    deleted_inline = 0
    for c in review_comments:
        if c.user.login == me:
            c.delete()
            deleted_inline += 1
    print(f"Deleted {deleted_inline} inline review comment(s) out of {len(review_comments)} total.")

    # Top-level issue comments (the summary comment lives here)
    issue_comments = list(pr.get_issue_comments())
    deleted_summary = 0
    for c in issue_comments:
        if c.user.login == me:
            c.delete()
            deleted_summary += 1
    print(f"Deleted {deleted_summary} summary/issue comment(s) out of {len(issue_comments)} total.")

    print("Done. PR is clean and ready to re-run.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python cleanup.py <pull-request-url>")
        sys.exit(1)
    cleanup(sys.argv[1])

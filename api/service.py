"""Read-only data access for the dashboard.

Reads the agent's findings.db (opened read-only) and an eval JSON snapshot.
The findings table stores every detection, including re-detections from repeated
runs, so every query collapses (pr_url, file, line, issue) to one logical
finding first — otherwise a PR reviewed twice would look like it has twice the
findings.
"""

import json
import sqlite3
from pathlib import Path

from api.config import settings

# One logical finding per (pr_url, file, line, issue); a re-detected finding
# folds into the same row, preferring the posted copy and earliest sighting.
_DEDUPED = """
WITH deduped AS (
    SELECT pr_url, file, line, issue,
           MIN(id)          AS id,
           MAX(severity)    AS severity,
           MAX(explanation) AS explanation,
           MAX(commit_sha)  AS commit_sha,
           MAX(posted)      AS posted,
           MIN(created_at)  AS created_at
    FROM findings
    GROUP BY pr_url, file, line, issue
)
"""


def _parse_pr(pr_url: str):
    """'https://github.com/owner/repo/pull/123' -> ('owner/repo', 123)."""
    parts = pr_url.rstrip("/").split("/")
    try:
        return f"{parts[-4]}/{parts[-3]}", int(parts[-1])
    except (IndexError, ValueError):
        return pr_url, None


def _connect():
    """Open the findings DB read-only, or None if it doesn't exist yet."""
    path = Path(settings.review_db_path)
    if not path.exists():
        return None
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def list_reviews() -> list[dict]:
    conn = _connect()
    if conn is None:
        return []
    try:
        rows = conn.execute(
            _DEDUPED + """
            SELECT pr_url,
                   COUNT(DISTINCT file)              AS files,
                   COUNT(*)                          AS total_findings,
                   SUM(severity = 'high')            AS high,
                   SUM(severity = 'medium')          AS medium,
                   SUM(severity = 'low')             AS low,
                   SUM(posted)                       AS posted,
                   MAX(created_at)                   AS last_reviewed
            FROM deduped
            GROUP BY pr_url
            ORDER BY last_reviewed DESC
            """
        ).fetchall()
    finally:
        conn.close()

    items = []
    for r in rows:
        repo, num = _parse_pr(r["pr_url"])
        items.append({
            "pr_url": r["pr_url"], "repo": repo, "pr_number": num,
            "files": r["files"], "total_findings": r["total_findings"],
            "high": r["high"] or 0, "medium": r["medium"] or 0, "low": r["low"] or 0,
            "posted": r["posted"] or 0, "last_reviewed": r["last_reviewed"],
        })
    return items


def review_detail(pr_url: str) -> dict | None:
    conn = _connect()
    if conn is None:
        return None
    try:
        rows = conn.execute(
            _DEDUPED + """
            SELECT id, file, line, severity, issue, explanation,
                   commit_sha, posted, created_at
            FROM deduped
            WHERE pr_url = ?
            ORDER BY file,
                     CASE severity WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
                     line
            """,
            (pr_url,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return None

    findings = [{
        "id": r["id"], "file": r["file"], "line": r["line"],
        "severity": r["severity"], "issue": r["issue"],
        "explanation": r["explanation"], "commit_sha": r["commit_sha"],
        "posted": bool(r["posted"]), "created_at": r["created_at"],
    } for r in rows]

    repo, num = _parse_pr(pr_url)
    sev = lambda s: sum(1 for f in findings if f["severity"] == s)
    return {
        "pr_url": pr_url, "repo": repo, "pr_number": num,
        "total_findings": len(findings),
        "high": sev("high"), "medium": sev("medium"), "low": sev("low"),
        "findings": findings,
    }


def load_eval() -> dict | None:
    path = Path(settings.eval_path)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

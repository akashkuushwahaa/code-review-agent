"""
Persistence for the review agent (Phase 4)
-------------------------------------------
A single SQLite file holding every finding the agent has ever detected. Two
jobs:

1. **Dedup** — before posting a comment, check whether the same finding was
   already posted on a prior run for the same PR, and skip re-posting it. This
   stops the agent stacking duplicate comments when it runs more than once on
   a PR (a repeated push, a re-triggered workflow, a manual re-run).
2. **History** — keep every detection, including ones below the severity
   threshold that were never posted, as the data the Phase 7 dashboard renders.

SQLite is stdlib, single-file, zero-setup. No ORM, no migration framework — a
`CREATE TABLE IF NOT EXISTS` at startup is the whole schema story.

Important operational caveat: dedup only works when the database file persists
between runs. On an ephemeral CI runner (GitHub Actions) the file is gone after
each run, so dedup does not carry across separate Action runs until the DB is
persisted (a Docker volume in Phase 6, or a hosted DB). Locally it works.
"""

import datetime
import os
import sqlite3

DEFAULT_DB_PATH = os.environ.get("REVIEW_DB_PATH", "findings.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS findings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pr_url      TEXT    NOT NULL,
    file        TEXT    NOT NULL,
    line        INTEGER,
    severity    TEXT,
    issue       TEXT,
    explanation TEXT,
    commit_sha  TEXT,
    posted      INTEGER NOT NULL DEFAULT 0,   -- 1 if this detection was posted
    created_at  TEXT    NOT NULL,             -- when the finding was recorded
    posted_at   TEXT                          -- when it was posted (NULL if not)
);
CREATE INDEX IF NOT EXISTS idx_findings_dedup
    ON findings (pr_url, file, line, issue, posted);
"""


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def connect(path: str = None):
    """Open the DB and ensure the schema exists.

    Returns a connection, or None if the DB can't be opened — persistence is
    an enhancement and must never stop a review from running.
    """
    try:
        conn = sqlite3.connect(path or DEFAULT_DB_PATH)
        conn.executescript(SCHEMA)
        conn.commit()
        return conn
    except sqlite3.Error as e:
        print(f"  [warn] could not open findings DB ({e}) — running without persistence")
        return None


def record_finding(conn, pr_url: str, filename: str, finding: dict,
                   commit_sha: str, posted: bool = False):
    """Insert one detected finding. Returns the new row id, or None on failure."""
    if conn is None:
        return None
    now = _now()
    try:
        cur = conn.execute(
            "INSERT INTO findings "
            "(pr_url, file, line, severity, issue, explanation, commit_sha, posted, created_at, posted_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                pr_url, filename, finding.get("line"), finding.get("severity"),
                finding.get("issue"), finding.get("explanation"), commit_sha,
                1 if posted else 0, now, now if posted else None,
            ),
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.Error as e:
        print(f"  [warn] could not record finding ({e})")
        return None


def already_posted(conn, pr_url: str, filename: str, line, issue: str) -> bool:
    """True if an equivalent finding was already posted on a prior run.

    Dedup key is (pr_url, file, line, issue) per the phase spec — commit_sha is
    intentionally NOT part of it, so an unaddressed issue isn't re-posted every
    time a new commit lands on the PR.
    """
    if conn is None:
        return False
    try:
        row = conn.execute(
            "SELECT 1 FROM findings "
            "WHERE pr_url=? AND file=? AND line IS ? AND issue IS ? AND posted=1 LIMIT 1",
            (pr_url, filename, line, issue),
        ).fetchone()
        return row is not None
    except sqlite3.Error as e:
        print(f"  [warn] dedup check failed ({e}) — not skipping")
        return False


def mark_posted(conn, row_id):
    """Flip a recorded finding to posted=1 once its comment is up."""
    if conn is None or row_id is None:
        return
    try:
        conn.execute(
            "UPDATE findings SET posted=1, posted_at=? WHERE id=?",
            (_now(), row_id),
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"  [warn] could not mark finding posted ({e})")

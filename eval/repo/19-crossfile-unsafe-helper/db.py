import sqlite3

DB_PATH = "app.db"

def connect():
    return sqlite3.connect(DB_PATH)

def resolve_report(report_type):
    """Build the query for a report type."""
    return "SELECT * FROM reports WHERE type = '" + report_type + "'"

def close(conn):
    conn.close()

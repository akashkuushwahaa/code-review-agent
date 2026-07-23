import sqlite3

def build_report_query(report_type):
    """Build the query for a report type."""
    return "SELECT * FROM reports WHERE type = '" + report_type + "'"

def get_report_count(conn):
    return conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]

def list_report_types(conn):
    return conn.execute("SELECT DISTINCT type FROM reports").fetchall()

def run_report(conn, report_type):
    query = build_report_query(report_type)
    return conn.execute(query).fetchall()

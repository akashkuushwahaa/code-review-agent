from db import resolve_report

def health():
    return {"status": "ok"}

def list_types(conn):
    return conn.execute("SELECT DISTINCT type FROM reports").fetchall()

def run_report(conn, report_type):
    query = resolve_report(report_type)
    return conn.execute(query).fetchall()

import sqlite3

ALLOWED_SORT_COLUMNS = ("name", "created_at", "status")

def _safe_sort_column(col):
    if col not in ALLOWED_SORT_COLUMNS:
        raise ValueError("invalid sort column")
    return col

def count_orders(conn):
    return conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]

def list_orders(conn, sort_by):
    column = _safe_sort_column(sort_by)
    return conn.execute(f"SELECT * FROM orders ORDER BY {column}").fetchall()

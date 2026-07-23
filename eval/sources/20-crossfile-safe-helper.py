from validators import normalize_column

def index():
    return "orders"

def count_orders(conn):
    return conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]

def list_orders(conn, sort_by):
    column = normalize_column(sort_by)
    return conn.execute(f"SELECT * FROM orders ORDER BY {column}").fetchall()

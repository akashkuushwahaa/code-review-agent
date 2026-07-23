ALLOWED_SORT_COLUMNS = ("name", "created_at", "status")
ALLOWED_FILTERS = ("open", "closed")

def normalize_column(col):
    """Whitelist the ORDER BY column; it cannot be parameterized."""
    if col not in ALLOWED_SORT_COLUMNS:
        raise ValueError("invalid sort column")
    return col

def safe_filter(value):
    if value not in ALLOWED_FILTERS:
        raise ValueError("invalid filter")
    return value

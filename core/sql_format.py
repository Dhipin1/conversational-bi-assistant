import sqlglot

def format_sql_pretty(sql: str) -> str:
    """Pretty-format SQL for display. If formatting fails, return original."""
    if not sql:
        return ""
    try:
        return sqlglot.transpile(sql, read="sqlite", pretty=True)[0]
    except Exception:
        return sql
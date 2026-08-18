# core/sql_format.py
from __future__ import annotations

def format_sql_pretty(sql: str | None) -> str:
    """
    Pretty-format SQL for display in the UI.

    Uses sqlparse if available; otherwise falls back to a simple cleanup.
    This function should NEVER change query meaning (display-only).
    """
    if not sql:
        return ""

    sql = str(sql).strip()

    try:
        import sqlparse  # type: ignore

        return sqlparse.format(
            sql,
            reindent=True,
            keyword_case="upper",
            strip_comments=False,
        ).strip()

    except Exception:
        # Fallback formatting if sqlparse isn't installed
        # (keep it simple so it never breaks)
        return sql.replace("\t", "    ").strip()
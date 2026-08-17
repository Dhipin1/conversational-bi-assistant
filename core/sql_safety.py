import re
import sqlglot
from sqlglot import exp

DISALLOWED = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "REPLACE",
    "TRUNCATE", "ATTACH", "DETACH", "PRAGMA", "VACUUM"
}

# Aggregate function keywords used for scalar-aggregate detection
AGGREGATE_FUNCS = (exp.Count, exp.Sum, exp.Avg, exp.Min, exp.Max)


def normalize_sql(sql: str) -> str:
    sql = (sql or "").strip()

    # Remove markdown fences
    sql = re.sub(r"```sql\s*", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"```", "", sql)
    sql = sql.strip()

    # Remove accidental prefixes
    prefixes = ["SQL:", "Query:", "Here is the SQL:"]
    for p in prefixes:
        if sql.lower().startswith(p.lower()):
            sql = sql[len(p):].strip()

    # Single statement only
    sql = sql.split(";")[0].strip()
    return sql


def is_read_only_select(sql: str) -> bool:
    try:
        parsed = sqlglot.parse_one(sql)
        if parsed is None:
            return False

        if parsed.key.upper() != "SELECT":
            return False

        upper = sql.upper()
        if any(k in upper for k in DISALLOWED):
            return False

        return True

    except Exception:
        return False


def _is_pure_scalar_aggregate(sql: str) -> bool:
    """
    Returns True if the query is guaranteed to return exactly ONE row,
    i.e. every selected expression is an aggregate function (COUNT/SUM/AVG/MIN/MAX)
    AND there is no GROUP BY clause.

    In that case, appending a LIMIT clause is meaningless and confusing
    (e.g. "SELECT COUNT(*) FROM Products LIMIT 200").
    """
    try:
        parsed = sqlglot.parse_one(sql)
    except Exception:
        parsed = None

    if isinstance(parsed, exp.Select):
        # If there's a GROUP BY, multiple rows can be returned -> not scalar
        if parsed.args.get("group"):
            return False

        expressions = parsed.expressions
        if not expressions:
            return False

        for e in expressions:
            inner = e.this if isinstance(e, exp.Alias) else e
            if not isinstance(inner, AGGREGATE_FUNCS):
                return False

        return True

    # --- Fallback (regex-based) if sqlglot parsing fails ---
    upper = sql.upper()
    if "GROUP BY" in upper:
        return False

    m = re.match(
        r"^\s*SELECT\s+(COUNT|SUM|AVG|MIN|MAX)\s*\(",
        sql,
        flags=re.IGNORECASE,
    )
    return bool(m)


def enforce_limit(sql: str, default_limit: int, max_limit: int) -> str:
    if not sql:
        return sql

    safe_limit = min(default_limit, max_limit)

    # Scalar aggregate queries (e.g. SELECT COUNT(*) FROM Products)
    # always return exactly one row -> LIMIT is meaningless, strip/skip it.
    if _is_pure_scalar_aggregate(sql):
        # Remove an existing LIMIT clause if the model added one anyway
        return re.sub(r"\s*\bLIMIT\s+\d+\b\s*$", "", sql, flags=re.IGNORECASE).strip()

    if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
        return f"{sql}\nLIMIT {safe_limit}"

    m = re.search(r"\bLIMIT\s+(\d+)\b", sql, re.IGNORECASE)
    if not m:
        return sql

    requested = int(m.group(1))
    if requested <= max_limit:
        return sql

    return re.sub(
        r"\bLIMIT\s+\d+\b",
        f"LIMIT {max_limit}",
        sql,
        flags=re.IGNORECASE,
    )
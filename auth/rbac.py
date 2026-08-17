import sqlglot
from sqlglot import exp

# --- Configure governance here ---
ROLE_CONFIG = {
    "admin": {
        "max_limit": 2000,
        "blocked_tables": set(),
        "blocked_columns": set(),  # admin can see everything
    },
    "analyst": {
        "max_limit": 1000,
        "blocked_tables": set(),
        # Example: block sensitive/PII-like columns (customize as you want)
        "blocked_columns": {
            "homephone",
            "address",
            "postalcode",
            "region",
        },
    },
    "executive": {
        "max_limit": 300,
        # Example: restrict executives from "raw" operational tables if you want
        "blocked_tables": {
            # Add tables you want to block for exec (optional)
            # "employees",
        },
        "blocked_columns": {
            "homephone",
            "address",
            "postalcode",
            "region",
        },
    },
}

DEFAULT_ROLE = "executive"


def get_role_config(role: str) -> dict:
    return ROLE_CONFIG.get(role, ROLE_CONFIG[DEFAULT_ROLE])


def get_max_limit(role: str) -> int:
    return int(get_role_config(role)["max_limit"])


def _parse_sql(sql: str):
    """
    Parse SQL into AST. Returns parsed expression or None.
    """
    try:
        return sqlglot.parse_one(sql, read="sqlite")
    except Exception:
        return None


def extract_tables_from_sql(sql: str) -> set[str]:
    parsed = _parse_sql(sql)
    if parsed is None:
        return set()

    tables = set()
    for t in parsed.find_all(exp.Table):
        if t.name:
            tables.add(t.name.lower())
    return tables


def extract_columns_from_sql(sql: str) -> set[str]:
    """
    Extract column names referenced in SQL.
    Only extracts the 'column' portion (not table qualifier).
    """
    parsed = _parse_sql(sql)
    if parsed is None:
        return set()

    cols = set()
    for c in parsed.find_all(exp.Column):
        # Column.name returns the column identifier (without table part)
        if c.name:
            cols.add(c.name.lower())
    return cols


def validate_sql_for_role(sql: str, role: str) -> tuple[bool, str | None]:
    """
    Enforce governance:
    - block certain tables
    - block certain columns
    """
    cfg = get_role_config(role)
    blocked_tables = {t.lower() for t in cfg.get("blocked_tables", set())}
    blocked_columns = {c.lower() for c in cfg.get("blocked_columns", set())}

    used_tables = extract_tables_from_sql(sql)
    used_columns = extract_columns_from_sql(sql)

    denied_tables = sorted(used_tables.intersection(blocked_tables))
    denied_columns = sorted(used_columns.intersection(blocked_columns))

    if denied_tables and denied_columns:
        return (
            False,
            "Access denied. Your role cannot query these tables: "
            f"{', '.join(denied_tables)} "
            "and cannot use these columns: "
            f"{', '.join(denied_columns)}"
        )

    if denied_tables:
        return (
            False,
            "Access denied. Your role cannot query these tables: "
            f"{', '.join(denied_tables)}"
        )

    if denied_columns:
        return (
            False,
            "Access denied. Your role cannot use these columns: "
            f"{', '.join(denied_columns)}"
        )

    return True, None
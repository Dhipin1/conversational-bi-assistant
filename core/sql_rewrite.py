import re
import difflib
from sqlglot import parse_one, exp


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (name or "").lower())


def _variants(n: str) -> set[str]:
    """
    Generate simple singular/plural variants:
    orderdetails <-> orderdetail
    categories <-> category
    employees <-> employee
    """
    v = {n}
    if n.endswith("ies"):
        v.add(n[:-3] + "y")          # categories -> category
    if n.endswith("y"):
        v.add(n[:-1] + "ies")        # category -> categories
    if n.endswith("ses"):
        v.add(n[:-2])                # (rare)
    if n.endswith("es"):
        v.add(n[:-2])                # shippers -> shipper (approx)
    if n.endswith("s") and len(n) > 3:
        v.add(n[:-1])                # details -> detail
    if not n.endswith("s"):
        v.add(n + "s")               # detail -> details
    return v


def _build_norm_map(available_tables: list[str]) -> dict[str, str]:
    """
    Build normalized-key -> real-table-name mapping, including variants.
    """
    m: dict[str, str] = {}
    for t in available_tables:
        key = _norm(t)
        for k in _variants(key):
            # don't overwrite existing keys; keep first seen mapping
            m.setdefault(k, t)
    return m


def _best_fuzzy_match(key: str, candidates: list[str], cutoff: float = 0.88) -> str | None:
    """
    Fuzzy match normalized keys when no direct variant match exists.
    """
    if not candidates:
        return None
    best = difflib.get_close_matches(key, candidates, n=1, cutoff=cutoff)
    return best[0] if best else None


def fix_table_and_column_qualifiers(sql: str, available_tables: list[str]) -> str:
    """
    Fixes table identifiers AND column qualifiers to match actual DB table names.

    Examples:
      OrderDetails -> "Order Details"
      OrderDetail  -> "Order Details"
      Order Detail -> "Order Details"
      OrderDetail.UnitPrice -> "Order Details".UnitPrice

    Skips rewriting when the qualifier is a real alias.
    """
    if not sql or not available_tables:
        return sql

    norm_map = _build_norm_map(available_tables)
    norm_keys = list(norm_map.keys())

    try:
        tree = parse_one(sql, read="sqlite")
    except Exception:
        return sql

    # Collect aliases so we don't rewrite them
    alias_names = set()
    for t in tree.find_all(exp.Table):
        alias = t.args.get("alias")
        if alias and alias.this:
            alias_names.add(alias.this.name)

    def resolve_real_table(used_name: str) -> str | None:
        used_norm = _norm(used_name)
        if used_norm in norm_map:
            return norm_map[used_norm]
        # fuzzy fallback
        best = _best_fuzzy_match(used_norm, norm_keys, cutoff=0.88)
        if best:
            return norm_map[best]
        return None

    # 1) Rewrite table nodes
    for t in tree.find_all(exp.Table):
        used = t.name
        real = resolve_real_table(used)
        if real:
            t.set("this", exp.to_identifier(real))

    # 2) Rewrite column qualifiers (skip aliases)
    for c in tree.find_all(exp.Column):
        tbl = c.table
        if not tbl:
            continue
        if tbl in alias_names:
            continue

        real = resolve_real_table(tbl)
        if real:
            c.set("table", exp.to_identifier(real))

    return tree.sql(dialect="sqlite")
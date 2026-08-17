import re
from dataclasses import dataclass
from typing import Optional


# Detect intent words
RANK_WORDS = r"\b(top|best|highest|lowest|worst|leading)\b"
RECENT_WORDS = r"\b(recent|latest|current|performance)\b"
ACTION_VERBS = r"\b(show|list|display|get|find|fetch|give me|return|print)\b"

# Follow-up-only answers (should be merged with previous question)
FOLLOWUP_ONLY = r"^(yes|ok|okay|sure|revenue|sales|orders|order count|count|quantity|units|customers|products)$"

METRIC_PATTERNS = {
    "revenue": r"\b(revenue|sales|turnover)\b",
    "order_count": r"\b(order count|number of orders|count)\b",
    "units": r"\b(units|quantity|qty|units sold)\b",
}

ENTITY_PATTERNS = {
    "customers": r"\b(customer|customers|client|clients)\b",
    "products": r"\b(product|products|item|items)\b",
    "countries": r"\b(country|countries|region|regions)\b",
    "categories": r"\b(category|categories)\b",
    "employees": r"\b(employee|employees|staff)\b",
    "orders": r"\b(order|orders)\b",
}

TIME_PAT = r"\b(19\d{2}|20\d{2}|q[1-4]|quarter|month|monthly|year|yearly|week|daily|today|yesterday|last year|this year)\b"


@dataclass
class AmbiguityDecision:
    needs_clarification: bool
    message: Optional[str]
    resolved_question: str


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _has(pattern: str, text: str) -> bool:
    return bool(re.search(pattern, text, flags=re.IGNORECASE))


def _has_number(text: str) -> bool:
    return bool(re.search(r"\b\d+\b", text))


def _detect_metric(text: str) -> Optional[str]:
    for name, pat in METRIC_PATTERNS.items():
        if _has(pat, text):
            return name
    return None


def _detect_entity(text: str) -> Optional[str]:
    for name, pat in ENTITY_PATTERNS.items():
        if _has(pat, text):
            return name
    return None


def _previous_user_messages(chat_messages: list) -> list[str]:
    msgs = []
    for m in chat_messages or []:
        if m.get("role") == "user" and m.get("content"):
            msgs.append(str(m["content"]))
    return msgs


def _find_anchor_question(prev_users: list[str]) -> str:
    """
    Anchor = last meaningful user question (not a single word follow-up).
    Prefer the latest question that contains ranking/recent/compare terms.
    """
    if not prev_users:
        return ""

    for q in reversed(prev_users):
        t = _norm(q)
        if len(t.split()) >= 3 and (_has(RANK_WORDS, t) or _has(RECENT_WORDS, t) or _has("compare", t)):
            return q

    for q in reversed(prev_users):
        t = _norm(q)
        if not _has(FOLLOWUP_ONLY, t) and len(t.split()) >= 2:
            return q

    return prev_users[-1]


def _is_complete_standalone_question(text: str) -> bool:
    """
    A message is considered "complete" (i.e., NOT a follow-up fragment)
    if it already contains its own entity/table reference AND either
    an action verb or an explicit number.

    Examples that ARE standalone (must NOT be merged with prior anchor):
      - "Show 10 orders"
      - "List 5 customers"
      - "Display 20 products"

    Examples that are NOT standalone (should be merged):
      - "revenue"
      - "by country"
      - "yes"
      - "top 5" (no entity yet)
    """
    t = _norm(text)
    has_entity = _detect_entity(t) is not None
    has_verb = _has(ACTION_VERBS, t)
    has_number = _has_number(t)
    return has_entity and (has_verb or has_number)


def _combine(anchor: str, current: str) -> str:
    """
    Combine short follow-ups with anchor, but NEVER merge a message
    that is already a complete, self-sufficient request.
    """
    a = _norm(anchor)
    c = _norm(current)

    if not a:
        return current
    if not c:
        return anchor

    # 1) HARD GUARD: if current already stands on its own, use it as-is.
    #    This fixes: anchor="List 5 customers", current="Show 10 orders"
    #    -> must resolve to "Show 10 orders", NOT a merged string.
    if _is_complete_standalone_question(current):
        return current

    # 2) True short follow-up fragments (bare words like "revenue", "yes")
    if _has(FOLLOWUP_ONLY, c):
        if c in a:
            return anchor
        metric = _detect_metric(c)
        if metric and " by " not in a.lower():
            return f"{anchor} by {current}".strip()
        return f"{anchor} {current}".strip()

    # 3) Very short fragments with no entity/number of their own
    #    are still treated as modifiers of the anchor (e.g., "by month").
    has_entity = _detect_entity(c) is not None
    has_number = _has_number(c)
    if len(c.split()) <= 3 and not has_entity and not has_number:
        return f"{anchor} {current}".strip()

    # 4) Otherwise, it's a brand-new, full question.
    return current


def resolve_question(user_question: str, chat_messages: list) -> AmbiguityDecision:
    """
    Context-aware ambiguity resolution:
    - Merge short follow-ups into the prior meaningful user query
    - Ask targeted clarification only if still ambiguous
    - NEVER merge a message that is already self-sufficient
    """
    prev_users = _previous_user_messages(chat_messages)

    if prev_users and _norm(prev_users[-1]) == _norm(user_question):
        prev_users = prev_users[:-1]

    anchor = _find_anchor_question(prev_users)
    combined = _combine(anchor, user_question)
    text = _norm(combined)

    metric = _detect_metric(text)
    entity = _detect_entity(text)
    is_rank = _has(RANK_WORDS, text)
    is_recent = _has(RECENT_WORDS, text)
    has_time = _has(TIME_PAT, text)

    if is_rank:
        if entity and metric:
            return AmbiguityDecision(False, None, combined)
        if entity and not metric:
            return AmbiguityDecision(
                True,
                f"Do you want the top **{entity}** by **revenue**, **order count**, or **units sold**?",
                combined,
            )
        if metric and not entity:
            return AmbiguityDecision(
                True,
                f"Should I rank **customers**, **products**, **countries**, **categories**, or **employees** by **{metric}**?",
                combined,
            )
        return AmbiguityDecision(
            True,
            "Please clarify what to rank and by which metric. Example: **top 5 customers by revenue**.",
            combined,
        )

    if is_recent and not metric:
        return AmbiguityDecision(
            True,
            "For recent performance, what metric do you want: **revenue**, **order count**, or **units sold**?",
            combined,
        )

    if len(text.split()) <= 2 and not anchor:
        return AmbiguityDecision(
            True,
            "Can you be more specific? Example: **revenue by country** or **top 5 customers by revenue**.",
            combined,
        )

    return AmbiguityDecision(False, None, combined)


def ambiguity_message_if_needed(question: str, chat_messages: list | None = None) -> str | None:
    d = resolve_question(question, chat_messages or [])
    return d.message if d.needs_clarification else None
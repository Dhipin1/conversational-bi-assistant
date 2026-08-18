import re


def extract_sql(text: str) -> str:
    """
    Extract one SQL query from an LLM response.

    Removes Markdown fences and leading labels, while preserving
    SELECT and WITH queries.
    """
    if not text:
        return ""

    value = text.strip()

    # Prefer content inside a fenced SQL block.
    fenced_match = re.search(
        r"```(?:sql)?\s*(.*?)```",
        value,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if fenced_match:
        value = fenced_match.group(1).strip()

    # Find the beginning of a SELECT or WITH query.
    query_start = re.search(
        r"\b(SELECT|WITH)\b",
        value,
        flags=re.IGNORECASE,
    )
    if query_start:
        value = value[query_start.start():]

    # Remove a trailing Markdown fence, if present.
    value = value.replace("```sql", "").replace("```SQL", "")
    value = value.replace("```", "").strip()

    # Allow one trailing semicolon, but no additional statement.
    value = value.rstrip(";").strip()

    return value
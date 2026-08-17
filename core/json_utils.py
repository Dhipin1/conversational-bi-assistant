import json
import re

def extract_json_object(text: str):
    """
    Extract first JSON object from text and parse it.
    Returns dict or None.
    """
    if not text:
        return None
    # Try direct parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # Find first {...}
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        return None
    snippet = m.group(0)
    try:
        return json.loads(snippet)
    except Exception:
        return None
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
FAV_PATH = ROOT / "logs" / "favorites.json"


def _load_all() -> dict:
    if not FAV_PATH.exists():
        return {}
    try:
        return json.loads(FAV_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_all(data: dict) -> None:
    FAV_PATH.parent.mkdir(parents=True, exist_ok=True)
    FAV_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def list_favorites(username: str) -> list[dict]:
    data = _load_all()
    return data.get(username, [])


def add_favorite(username: str, name: str, question: str) -> None:
    data = _load_all()
    data.setdefault(username, [])
    data[username].append({
        "name": name,
        "question": question,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    _save_all(data)


def delete_favorite(username: str, index: int) -> None:
    data = _load_all()
    items = data.get(username, [])
    if 0 <= index < len(items):
        items.pop(index)
    data[username] = items
    _save_all(data)
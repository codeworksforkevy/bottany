import json
import time
from pathlib import Path
from typing import Dict, List


# -----------------------------
# CACHE
# -----------------------------
_CACHE = {
    "data": {},
    "last_load": 0
}

CACHE_TTL = 300  # seconds


# -----------------------------
# LOAD FROM DISK
# -----------------------------
def _load_from_disk(base_path: Path) -> Dict[str, Dict]:

    trivia_dir = base_path / "academic-trivia" / "academic-trivia"

    if not trivia_dir.exists():
        return {}

    all_entries = {}
    seen_texts = set()

    for file in trivia_dir.glob("*.json"):
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)

        metadata = data.get("metadata", {})
        author = metadata.get("author", "Unknown Author")

        for idx, entry in enumerate(data.get("entries", [])):
            text = (entry.get("text") or "").strip()
            if not text:
                continue

            norm = text.lower()
            if norm in seen_texts:
                continue
            seen_texts.add(norm)

            entry_id = entry.get("id") or f"{file.stem}_{idx}"

            all_entries[entry_id] = {
                "id": entry_id,
                "text": text,
                "field": entry.get("field"),
                "author": author
            }

    return all_entries


# -----------------------------
# PUBLIC LOADER (CACHED)
# -----------------------------
def load_academic_directory(base_path: Path) -> Dict[str, Dict]:

    now = time.time()

    if (
        _CACHE["data"]
        and (now - _CACHE["last_load"] < CACHE_TTL)
    ):
        return _CACHE["data"]

    data = _load_from_disk(base_path)

    _CACHE["data"] = data
    _CACHE["last_load"] = now

    return data


# -----------------------------
# MAIN ENTRY FOR COMMAND
# -----------------------------
def get_weighted_batch(
    base_path: Path,
    user_id: int,
    size: int = 25,
    author_filter: str | None = None
) -> List[Dict]:

    # 🔥 Lazy import to avoid circular dependency
    from services.trivia_memory_pg import weighted_select

    entries = load_academic_directory(base_path)
    items = list(entries.values())

    if author_filter:
        items = [
            i for i in items
            if author_filter.lower() in (i.get("author") or "").lower()
        ]

    if not items:
        return []

    payload = [
        {
            "id": i["id"],
            "field": i.get("field")
        }
        for i in items
    ]

    selected_ids = weighted_select(
        payload,
        user_id=user_id,
        k=size
    )

    return [
        entries[eid]
        for eid in selected_ids
        if eid in entries
    ]

import json
import random
import time
from pathlib import Path
from typing import List, Dict

from services.trivia_memory import (
    get_global_count,
    increment_global,
    user_has_seen,
    mark_user_seen
)

_CACHE = {"data": [], "last_load": 0}
CACHE_TTL = 300


def _load_from_disk(base_path: Path) -> List[Dict]:
    trivia_dir = base_path / "academic-trivia" / "academic-trivia"

    if not trivia_dir.exists():
        return []

    all_items = []
    seen_texts = set()

    for file in trivia_dir.glob("*.json"):
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)

        metadata = data.get("metadata", {})
        author = metadata.get("author", "Unknown Author")

        for idx, entry in enumerate(data.get("entries", [])):
            text = entry.get("text", "").strip()
            if not text:
                continue

            norm = text.lower()
            if norm in seen_texts:
                continue
            seen_texts.add(norm)

            entry_id = entry.get("id") or f"{file.stem}_{idx}"

            all_items.append({
                "id": entry_id,
                "text": text,
                "field": entry.get("field"),
                "author": author
            })

    return all_items


def load_academic_directory(base_path: Path):
    now = time.time()
    if _CACHE["data"] and (now - _CACHE["last_load"] < CACHE_TTL):
        return _CACHE["data"]

    data = _load_from_disk(base_path)
    _CACHE["data"] = data
    _CACHE["last_load"] = now
    return data


def weighted_sample(items: List[Dict], user_id: int, k=25):

    weights = []

    for item in items:
        global_count = get_global_count(item["id"])

        weight = 1 / (1 + global_count)

        if user_has_seen(user_id, item["id"]):
            weight *= 0.3

        weights.append(weight)

    selected = random.choices(
        items,
        weights=weights,
        k=min(k, len(items))
    )

    for item in selected:
        increment_global(item["id"])
        mark_user_seen(user_id, item["id"])

    return selected


def get_random_batch(base_path: Path, user_id: int, author_filter=None, size=25):

    items = load_academic_directory(base_path)

    if author_filter:
        items = [
            i for i in items
            if author_filter.lower() in i["author"].lower()
        ]

    if not items:
        return []

    return weighted_sample(items, user_id=user_id, k=size)

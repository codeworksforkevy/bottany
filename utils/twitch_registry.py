from __future__ import annotations
import os
import json
from typing import Any, Dict, List

REGISTRY_FILE = "twitch_badges_and_drops_registry.json"

def load_curated_items(data_dir: str) -> List[Dict[str, Any]]:
    path = os.path.join(data_dir, REGISTRY_FILE)
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    if isinstance(obj, dict):
        return list(obj.get("items", []) or [])
    if isinstance(obj, list):
        return obj
    return []

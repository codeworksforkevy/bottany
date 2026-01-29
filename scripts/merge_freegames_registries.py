"""
Merge accidental duplicate registries:
- data/freegames_registry.json
- data/free_games_registry.json

Keeps the richer one (more keys), writes to data/freegames_registry.json.
Does NOT delete files (safe by default). You can delete the duplicate manually.

Run:
  python -m scripts.merge_freegames_registries
"""
from __future__ import annotations
import json, os
from typing import Any, Dict

def load(p: str) -> Any:
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def save(p: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def main():
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    p1 = os.path.abspath(os.path.join(data_dir, "freegames_registry.json"))
    p2 = os.path.abspath(os.path.join(data_dir, "free_games_registry.json"))

    a = load(p1) or {}
    b = load(p2) or {}
    # pick richer
    out: Dict[str, Any] = a if len(json.dumps(a)) >= len(json.dumps(b)) else b
    save(p1, out)
    print("Wrote:", p1)
    if os.path.exists(p2):
        print("Note: duplicate still exists (delete manually if desired):", p2)

if __name__ == "__main__":
    main()

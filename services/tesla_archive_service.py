import os
import json

CACHE = None

def load_archive(data_dir):
    global CACHE

    if CACHE:
        return CACHE

    path = os.path.join(data_dir, "tesla_academic_archive.json")

    if not os.path.exists(path):
        return {"items": [], "count": 0}

    with open(path, "r", encoding="utf-8") as f:
        items = json.load(f)

    CACHE = {
        "items": items,
        "count": len(items)
    }

    return CACHE

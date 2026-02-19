import os
import json


async def get_tesla_catalog(DATA_DIR):

    path = os.path.join(DATA_DIR, "tesla_catalog.json")

    if not os.path.exists(path):
        return {"items": [], "count": 0}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        items = data.get("items", [])
        return {
            "items": items,
            "count": len(items)
        }

    except Exception:
        return {"items": [], "count": 0}



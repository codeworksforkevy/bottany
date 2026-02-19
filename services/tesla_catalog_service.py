import os
import json

CATALOG_FILE = "tesla_catalog.json"

async def get_tesla_catalog(DATA_DIR):

    path = os.path.join(DATA_DIR, CATALOG_FILE)

    if not os.path.exists(path):
        return {"items": [], "count": 0}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {
                "items": data.get("items", []),
                "count": len(data.get("items", []))
            }
    except Exception:
        return {"items": [], "count": 0}


import json
import os
from datetime import datetime, timedelta

def load_cache(path):
    if not os.path.exists(path):
        return None

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_cache(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def refresh_needed(cache_data, refresh_days):
    if not cache_data:
        return True

    meta = cache_data.get("meta", {})
    last = meta.get("last_refresh_utc")

    if not last:
        return True

    last_dt = datetime.fromisoformat(last)
    return datetime.utcnow() - last_dt > timedelta(days=refresh_days)

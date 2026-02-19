from __future__ import annotations

import os
import json
import requests
from datetime import datetime, timedelta


PATENTSVIEW_URL = "https://api.patentsview.org/patents/query"
CACHE_FILE = "tesla_cache.json"
REFRESH_DAYS = 30


# -------------------------------------------------
# CATEGORY CLASSIFIER
# -------------------------------------------------

def _classify(title: str) -> str:
    t = (title or "").lower()

    if "alternating" in t:
        return "alternating_current"
    if "wireless" in t:
        return "wireless_power"
    if "radio" in t:
        return "radio"
    if "motor" in t:
        return "electric_motor"
    if "turbine" in t:
        return "turbine"
    return "electrical_general"


# -------------------------------------------------
# FETCH FROM PATENTSVIEW
# -------------------------------------------------

def _fetch_from_api():

    payload = {
        "q": {
            "_and": [
                {"inventor_first_name": "Nikola"},
                {"inventor_last_name": "Tesla"}
            ]
        },
        "f": [
            "patent_number",
            "patent_title",
            "patent_date",
            "patent_abstract"
        ],
        "o": {"per_page": 200}
    }

    response = requests.post(PATENTSVIEW_URL, json=payload, timeout=20)
    response.raise_for_status()

    data = response.json()
    patents = data.get("patents", [])

    items = []

    for p in patents:
        items.append({
            "patent_number": p.get("patent_number"),
            "title": p.get("patent_title"),
            "year": (p.get("patent_date") or "")[:4],
            "category": _classify(p.get("patent_title")),
            "abstract": p.get("patent_abstract"),
            "source_url": f"https://ppubs.uspto.gov/dirsearch-public/print/downloadPdf/{p.get('patent_number')}"
        })

    return items


# -------------------------------------------------
# CACHE HANDLING
# -------------------------------------------------

def _load_cache(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_cache(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _needs_refresh(cache):
    if not cache:
        return True

    meta = cache.get("meta", {})
    last = meta.get("last_refresh_utc")

    if not last:
        return True

    last_dt = datetime.fromisoformat(last)
    return datetime.utcnow() - last_dt > timedelta(days=REFRESH_DAYS)


# -------------------------------------------------
# PUBLIC SERVICE
# -------------------------------------------------

async def get_tesla_catalog(DATA_DIR):

    cache_path = os.path.join(DATA_DIR, CACHE_FILE)
    cache = _load_cache(cache_path)

    if _needs_refresh(cache):

        try:
            items = _fetch_from_api()

            cache = {
                "meta": {
                    "last_refresh_utc": datetime.utcnow().isoformat(),
                    "count": len(items),
                    "source": "USPTO PatentsView API"
                },
                "items": items
            }

            _save_cache(cache_path, cache)

        except Exception:
            # API fail ederse eski cache'i kullan
            if cache:
                return cache
            return {"items": [], "count": 0}

    return cache or {"items": [], "count": 0}

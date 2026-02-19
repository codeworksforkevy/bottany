from __future__ import annotations

import os
import json
import aiohttp
import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("bottany.tesla")

PATENTSVIEW_URL = "https://api.patentsview.org/patents/query"
CACHE_FILE = "tesla_cache.json"
REFRESH_DAYS = 30


# -------------------------------------------------
# CATEGORY CLASSIFIER
# -------------------------------------------------

def _classify(title: str | None) -> str:
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
# FETCH FROM PATENTSVIEW (ASYNC SAFE)
# -------------------------------------------------

async def _fetch_from_api() -> list[dict]:

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

    timeout = aiohttp.ClientTimeout(total=20)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(PATENTSVIEW_URL, json=payload) as resp:

            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(
                    f"PatentsView API error {resp.status}: {text[:500]}"
                )

            data = await resp.json()

    patents = data.get("patents", [])

    items: list[dict] = []

    for p in patents:
        patent_number = p.get("patent_number")
        if not patent_number:
            continue

        items.append({
            "patent_number": patent_number,
            "title": p.get("patent_title"),
            "year": (p.get("patent_date") or "")[:4],
            "category": _classify(p.get("patent_title")),
            "abstract": p.get("patent_abstract"),
            "source_url": f"https://ppubs.uspto.gov/dirsearch-public/print/downloadPdf/{patent_number}"
        })

    logger.info("Tesla API fetched %s patents", len(items))

    return items


# -------------------------------------------------
# CACHE HANDLING
# -------------------------------------------------

def _load_cache(path: str):
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Tesla cache read failed: %s", e)
        return None


def _save_cache(path: str, data: dict):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)

        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        os.replace(tmp, path)

        logger.info("Tesla cache written: %s", path)

    except Exception as e:
        logger.error("Tesla cache write failed: %s", e)


def _needs_refresh(cache: dict | None) -> bool:

    if not cache:
        return True

    meta = cache.get("meta", {})
    last = meta.get("last_refresh_utc")

    if not last:
        return True

    try:
        last_dt = datetime.fromisoformat(last)
    except Exception:
        return True

    return datetime.utcnow() - last_dt > timedelta(days=REFRESH_DAYS)


# -------------------------------------------------
# PUBLIC SERVICE
# -------------------------------------------------

async def get_tesla_catalog(DATA_DIR: str | os.PathLike):

    cache_path = os.path.join(DATA_DIR, CACHE_FILE)

    cache = _load_cache(cache_path)

    if _needs_refresh(cache):

        logger.info("Refreshing Tesla catalog from API...")

        try:
            items = await _fetch_from_api()

            cache = {
                "meta": {
                    "last_refresh_utc": datetime.utcnow().isoformat(),
                    "count": len(items),
                    "source": "USPTO PatentsView API"
                },
                "items": items
            }

            _save_cache(cache_path, cache)

        except Exception as e:
            logger.error("Tesla API fetch failed: %s", e)

            # If API fails but cache exists → fallback
            if cache:
                logger.warning("Using stale Tesla cache")
                return cache

            return {"items": [], "count": 0}

    return cache or {"items": [], "count": 0}


from __future__ import annotations

import urllib.parse
import datetime as dt
from typing import Any, Dict, List

import aiohttp


def _parse_iso(date_str: str) -> dt.datetime | None:
    try:
        return dt.datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except Exception:
        return None


def _is_active_offer(offer: dict) -> bool:
    start = _parse_iso(offer.get("startDate", ""))
    end = _parse_iso(offer.get("endDate", ""))
    if not start or not end:
        return False
    now = dt.datetime.now(dt.timezone.utc)
    return start <= now <= end


async def fetch_epic_offers(
    session: aiohttp.ClientSession,
    endpoint: str,
    timeout_s: int = 20
) -> List[Dict[str, Any]]:
    '''
    Production-ready Epic Games free-to-keep fetcher (2026 stable version)

    Returns list of:
    {
        "title": str,
        "url": str,
        "kind": "free_to_keep",
        "note": str
    }
    '''

    params = {
        "locale": "en-US",
        "country": "US",
        "allowCountries": "US"
    }

    url = endpoint
    if "?" not in url:
        url = url + "?" + urllib.parse.urlencode(params)

    async with session.get(url, timeout=timeout_s) as r:
        r.raise_for_status()
        data = await r.json()

    elements = (
        data.get("data", {})
            .get("Catalog", {})
            .get("searchStore", {})
            .get("elements", [])
    )

    results: List[Dict[str, Any]] = []

    for el in elements:
        promotions = el.get("promotions") or {}

        promo_groups = promotions.get("promotionalOffers") or []

        active = False

        for group in promo_groups:
            for offer in group.get("promotionalOffers", []):
                if _is_active_offer(offer):
                    active = True
                    break
            if active:
                break

        if not active:
            continue

        title = el.get("title") or el.get("productSlug") or "Epic offer"

        slug = (
            el.get("productSlug")
            or el.get("urlSlug")
            or ""
        )

        if slug:
            page = f"https://store.epicgames.com/en-US/p/{slug}"
        else:
            page = "https://store.epicgames.com/"

        results.append({
            "title": title.strip(),
            "url": page,
            "kind": "free_to_keep",
            "note": ""
        })

    return results

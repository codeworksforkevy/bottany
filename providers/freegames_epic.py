from __future__ import annotations

import urllib.parse
from typing import Any, Dict, List

import aiohttp


async def fetch_epic_offers(session: aiohttp.ClientSession, endpoint: str, timeout_s: int = 20) -> List[Dict[str, Any]]:
    """
    Fetch Epic free-to-keep promotions from Epic's public backend endpoint.
    Returns dicts: {title,url,kind,note}
    """
    params = {"locale": "en-US", "country": "US", "allowCountries": "US"}
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

    out: List[Dict[str, Any]] = []
    for el in elements:
        promos = (el.get("promotions") or {}).get("promotionalOffers") or []
        if not promos:
            continue
        title = el.get("title") or el.get("productSlug") or "Epic offer"
        slug = el.get("productSlug") or el.get("urlSlug") or ""
        page = f"https://store.epicgames.com/en-US/p/{slug}" if slug else "https://store.epicgames.com/"
        out.append({"title": title, "url": page, "kind": "free_to_keep", "note": ""})
    return out

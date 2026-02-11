
from __future__ import annotations

import urllib.parse
import datetime as dt
from typing import Any, Dict, List

import aiohttp


def _parse_iso(date_str: str):
    try:
        return dt.datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except Exception:
        return None


def _is_active(start: str, end: str):
    start_dt = _parse_iso(start)
    end_dt = _parse_iso(end)
    if not start_dt or not end_dt:
        return False, None

    now = dt.datetime.now(dt.timezone.utc)
    return start_dt <= now <= end_dt, end_dt


def _get_thumbnail(el: Dict[str, Any]) -> str | None:
    images = el.get("keyImages") or []
    for img in images:
        if img.get("type") in ("OfferImageWide", "DieselStoreFrontWide"):
            return img.get("url")
    if images:
        return images[0].get("url")
    return None


async def fetch_epic_offers(
    session: aiohttp.ClientSession,
    endpoint: str,
    timeout_s: int = 20
) -> List[Dict[str, Any]]:

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

        for group in promo_groups:
            for offer in group.get("promotionalOffers", []):

                active, end_dt = _is_active(
                    offer.get("startDate", ""),
                    offer.get("endDate", "")
                )

                if not active:
                    continue

                price = el.get("price", {})
                total = price.get("totalPrice", {})
                if total.get("discountPrice") != 0:
                    continue

                title = el.get("title") or el.get("productSlug") or "Epic offer"
                slug = el.get("productSlug") or el.get("urlSlug") or ""
                page = f"https://store.epicgames.com/en-US/p/{slug}" if slug else "https://store.epicgames.com/"

                results.append({
                    "title": title.strip(),
                    "url": page,
                    "kind": "free_to_keep",
                    "platform": "epic",
                    "thumbnail": _get_thumbnail(el),
                    "expires_at": end_dt
                })

    return results


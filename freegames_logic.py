"""
Free games / deals aggregation logic.

Kinds:
- free_to_keep: 100% free ownership (Epic, some GOG giveaways)
- deal: discounted (Humble deals, etc.)
- subscription: playable with subscription (Amazon Luna "subscription picks")
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import aiohttp
import discord
from bs4 import BeautifulSoup

# Color palette requested:
BABY_BLUE = 0xA7D8FF     # free-to-keep
BABY_PINK = 0xFFB6C1     # deals/discounts
BURNT_ORANGE = 0xCC5500  # subscription

DEFAULT_TIMEOUT_S = 18


def _load_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _safe_strip(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


@dataclass(frozen=True)
class Offer:
    platform: str
    kind: str  # free_to_keep | deal | subscription
    title: str
    url: str
    note: str = ""


async def fetch_epic_offers(session: aiohttp.ClientSession, endpoint: str, timeout_s: int) -> List[Dict[str, Any]]:
    """
    Parse Epic 'freeGamesPromotions' endpoint (public).
    Returns a list of dicts with {title,url,kind,note}.
    """
    timeout = aiohttp.ClientTimeout(total=timeout_s)
    async with session.get(endpoint, timeout=timeout) as resp:
        resp.raise_for_status()
        data = await resp.json()

    out: List[Dict[str, Any]] = []
    elements = (
        data.get("data", {})
            .get("Catalog", {})
            .get("searchStore", {})
            .get("elements", [])
    )
    for el in elements:
        promos = el.get("promotions") or {}
        promo_blocks = (promos.get("promotionalOffers") or []) + (promos.get("upcomingPromotionalOffers") or [])
        if not promo_blocks:
            continue

        # We only keep "free" promotions
        is_free = False
        for pb in promo_blocks:
            for po in pb.get("promotionalOffers", []) or []:
                price = (po.get("discountSetting") or {}).get("discountPercentage")
                if price == 0 or price == 100:
                    is_free = True
        if not is_free:
            continue

        slug = None
        if el.get("productSlug"):
            slug = el["productSlug"]
        elif el.get("urlSlug"):
            slug = el["urlSlug"]

        url = "https://store.epicgames.com/"
        if slug:
            url += f"p/{slug}"
        title = el.get("title") or el.get("productName") or "Epic Games Store"
        out.append({"title": _safe_strip(title), "url": url, "kind": "free_to_keep", "note": "Epic Games Store"})
    return out


async def fetch_gog_offers(session: aiohttp.ClientSession, endpoints: List[str], timeout_s: int) -> List[Dict[str, Any]]:
    """
    Scrape GOG pages for 'free' / 'giveaway' CTA links.
    This is heuristic but works well enough for a weekly list.
    """
    timeout = aiohttp.ClientTimeout(total=timeout_s)
    out: List[Dict[str, Any]] = []

    for url in endpoints:
        try:
            async with session.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                if resp.status >= 400:
                    continue
                html = await resp.text()
        except Exception:
            continue

        soup = BeautifulSoup(html, "lxml")
        # Look for anchors mentioning free/giveaway
        for a in soup.find_all("a", href=True):
            txt = _safe_strip(a.get_text(" ", strip=True)).lower()
            if not txt:
                continue
            if ("free" in txt and ("claim" in txt or "get" in txt or "redeem" in txt)) or ("giveaway" in txt):
                href = a["href"]
                if href.startswith("/"):
                    href = "https://www.gog.com" + href
                title = _safe_strip(a.get_text(" ", strip=True))[:140] or "GOG Freebie"
                out.append({"title": title, "url": href, "kind": "free_to_keep", "note": "GOG"})
        # Deduplicate per page
        seen = set()
        dedup = []
        for r in out:
            k = (r["title"], r["url"])
            if k in seen:
                continue
            seen.add(k)
            dedup.append(r)
        out = dedup

    return out


async def fetch_humble_offers(session: aiohttp.ClientSession, urls: List[str], timeout_s: int) -> List[Dict[str, Any]]:
    """
    Scrape Humble pages for "deal" links. Humble rarely does free-to-keep;
    treat everything here as 'deal' unless you add a verified free endpoint later.
    """
    timeout = aiohttp.ClientTimeout(total=timeout_s)
    out: List[Dict[str, Any]] = []
    for url in urls:
        try:
            async with session.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                if resp.status >= 400:
                    continue
                html = await resp.text()
        except Exception:
            continue

        soup = BeautifulSoup(html, "lxml")
        # Try common card patterns
        for a in soup.find_all("a", href=True):
            txt = _safe_strip(a.get_text(" ", strip=True))
            if not txt:
                continue
            low = txt.lower()
            if any(k in low for k in ["bundle", "deal", "sale", "save", "%", "off"]):
                href = a["href"]
                if href.startswith("/"):
                    href = "https://www.humblebundle.com" + href
                title = txt[:140]
                out.append({"title": title, "url": href, "kind": "deal", "note": "Humble"})
        # light dedupe
        seen = set()
        dedup = []
        for r in out:
            k = (r["title"], r["url"])
            if k in seen:
                continue
            seen.add(k)
            dedup.append(r)
        out = dedup

    return out


async def fetch_luna_subscription_picks(session: aiohttp.ClientSession, luna_cfg: Dict[str, Any], timeout_s: int, cache_path: str) -> List[Dict[str, Any]]:
    """
    Auto-refresh Luna subscription picks by scraping a small set of official pages.

    Strategy:
    - If cache is present and "fresh" (<= 7 days) -> return cache
    - Else scrape configured URLs (luna_cfg["urls"]) and extract game titles/links
    - Save to cache and return
    """
    # Cache read
    cache = _load_json(cache_path, {})
    now = int(asyncio.get_event_loop().time())
    # store wall time in cache too
    wall_now = int(__import__("time").time())
    max_age_s = int(luna_cfg.get("cache_max_age_s", 7 * 24 * 3600))
    if isinstance(cache, dict) and cache.get("items") and isinstance(cache.get("ts"), int):
        if wall_now - cache["ts"] <= max_age_s:
            return list(cache["items"])

    urls = luna_cfg.get("urls") or [
        "https://luna.amazon.com/",  # homepage often contains 'Play on Luna' carousel
        "https://luna.amazon.com/channels",
    ]
    timeout = aiohttp.ClientTimeout(total=timeout_s)
    items: List[Dict[str, Any]] = []
    for url in urls:
        try:
            async with session.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                if resp.status >= 400:
                    continue
                html = await resp.text()
        except Exception:
            continue

        soup = BeautifulSoup(html, "lxml")
        # Heuristics: links that look like games/channels tiles
        for a in soup.find_all("a", href=True):
            href = a["href"]
            txt = _safe_strip(a.get_text(" ", strip=True))
            if not txt or len(txt) < 2:
                continue
            # Skip generic nav
            if txt.lower() in {"home", "channels", "games", "pricing", "faq", "help"}:
                continue
            if "/game/" in href or "/games/" in href or "/channel/" in href or "/channels/" in href:
                if href.startswith("/"):
                    href = "https://luna.amazon.com" + href
                items.append({"title": txt[:140], "url": href, "kind": "subscription", "note": "Amazon Luna"})
    # Deduplicate and keep a reasonable cap
    seen = set()
    dedup: List[Dict[str, Any]] = []
    for it in items:
        k = (it.get("title"), it.get("url"))
        if k in seen:
            continue
        seen.add(k)
        dedup.append(it)
    dedup = dedup[: int(luna_cfg.get("max_items", 60))]

    # Fallback to curated list if scraping yields nothing
    if not dedup:
        for it in luna_cfg.get("fallback_items", []) or []:
            if it.get("title") and it.get("url"):
                dedup.append({"title": it["title"], "url": it["url"], "kind": "subscription", "note": "Amazon Luna"})

    _save_json(cache_path, {"ts": wall_now, "items": dedup, "source_urls": urls})
    return dedup


def _sort_key(o: Offer) -> str:
    return (o.platform + " " + o.title).lower()


def build_kind_embeds(offers: List[Offer], *, title_prefix: str = "Free games & deals") -> List[discord.Embed]:
    """
    Return up to 3 embeds (Free-to-keep / Deals / Subscription).
    """
    by_kind: Dict[str, List[Offer]] = {"free_to_keep": [], "deal": [], "subscription": []}
    for o in offers:
        by_kind.setdefault(o.kind, []).append(o)

    embeds: List[discord.Embed] = []

    def _mk(kind: str, title: str, color: int) -> Optional[discord.Embed]:
        items = sorted(by_kind.get(kind, []), key=_sort_key)
        if not items:
            return None
        emb = discord.Embed(title=f"{title_prefix} — {title}", color=color)
        lines = []
        for o in items[:25]:
            note = f" — {o.note}" if o.note else ""
            lines.append(f"• [{o.title}]({o.url}){note}")
        emb.description = "\n".join(lines)
        if len(items) > 25:
            emb.set_footer(text=f"+{len(items)-25} more not shown")
        return emb

    e1 = _mk("free_to_keep", "Free-to-keep", BABY_BLUE)
    e2 = _mk("deal", "Discount deals", BABY_PINK)
    e3 = _mk("subscription", "Subscription picks", BURNT_ORANGE)
    for e in (e1, e2, e3):
        if e:
            embeds.append(e)
    return embeds


async def gather_offers(
    registry_path: str,
    *,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    only_free: bool = False,
) -> List[Offer]:
    """
    Read registry (data/freegames_registry.json) and gather offers.

    Registry layout (minimal):
    {
      "sources": {
        "epic": {"endpoint": "..."},
        "gog": {"endpoints": ["..."]},
        "humble": {"urls": ["..."]},
        "luna": {"urls": ["..."], "cache_file": "data/luna_cache.json"}
      }
    }
    """
    reg = _load_json(registry_path, {})
    sources = (reg or {}).get("sources", {}) if isinstance(reg, dict) else {}
    epic = sources.get("epic", {})
    gog = sources.get("gog", {})
    humble = sources.get("humble", {})
    luna = sources.get("luna", {})

    offers: List[Offer] = []

    async with aiohttp.ClientSession() as session:
        # Epic
        endpoint = epic.get("endpoint") or "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions"
        try:
            epic_raw = await fetch_epic_offers(session, endpoint, timeout_s)
            for r in epic_raw:
                offers.append(Offer(platform="epic", kind=r.get("kind", "free_to_keep"), title=r["title"], url=r["url"], note=r.get("note", "")))
        except Exception:
            pass

        # GOG
        endpoints = gog.get("endpoints") or ["https://www.gog.com/en/partner/free_games", "https://www.gog.com/#giveaway"]
        try:
            gog_raw = await fetch_gog_offers(session, endpoints, timeout_s)
            for r in gog_raw:
                offers.append(Offer(platform="gog", kind=r.get("kind", "free_to_keep"), title=r["title"], url=r["url"], note=r.get("note", "")))
        except Exception:
            pass

        # Humble
        humble_urls = humble.get("urls") or [
            "https://www.humblebundle.com/store/search?sort=bestselling&filter=onsale",
            "https://www.humblebundle.com/games",
        ]
        try:
            humble_raw = await fetch_humble_offers(session, humble_urls, timeout_s)
            for r in humble_raw:
                offers.append(Offer(platform="humble", kind=r.get("kind", "deal"), title=r["title"], url=r["url"], note=r.get("note", "")))
        except Exception:
            pass

        # Luna
        cache_file = luna.get("cache_file") or os.path.join(os.path.dirname(registry_path), "luna_cache.json")
        try:
            luna_raw = await fetch_luna_subscription_picks(session, luna, timeout_s, cache_file)
            for r in luna_raw:
                offers.append(Offer(platform="luna", kind=r.get("kind", "subscription"), title=r["title"], url=r["url"], note=r.get("note", "")))
        except Exception:
            pass

    # Normalize / filter
    uniq: Dict[str, Offer] = {}
    for o in offers:
        key = (o.kind + "|" + o.title.strip().lower() + "|" + o.url.strip().lower())
        uniq[key] = o
    offers = list(uniq.values())

    if only_free:
        offers = [o for o in offers if o.kind == "free_to_keep"]

    return sorted(offers, key=_sort_key)

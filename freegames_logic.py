
"""
Free games / deals aggregation logic (v2 stabilized).

Kinds:
- free_to_keep: 100% free ownership (Epic, some GOG giveaways)
- deal: discounted (Humble deals, etc.)
- subscription: playable with subscription (Amazon Luna picks)
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import aiohttp
import discord
from bs4 import BeautifulSoup

import discord

BABY_BLUE = 0xA7D8FF
BABY_PINK = 0xFFB6C1
BURNT_ORANGE = 0xCC5500

def build_kind_embeds(offers, *, title_prefix="Free games & deals"):
    by_kind = {"free_to_keep": [], "deal": [], "subscription": []}
    for o in offers:
        by_kind.setdefault(o.kind, []).append(o)

    embeds = []

    def _mk(kind, title, color):
        items = sorted(by_kind.get(kind, []), key=lambda x: (x.platform + x.title).lower())
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


# ---- Import stabilized Epic  ----
from freegames_epic import fetch_epic_offers


BABY_BLUE = 0xA7D8FF
BABY_PINK = 0xFFB6C1
BURNT_ORANGE = 0xCC5500

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
    kind: str
    title: str
    url: str
    note: str = ""


# ---------------- GOG ----------------

async def fetch_gog_offers(session: aiohttp.ClientSession, endpoints: List[str], timeout_s: int):
    timeout = aiohttp.ClientTimeout(total=timeout_s)
    out = []

    for url in endpoints:
        try:
            async with session.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                if resp.status >= 400:
                    continue
                html = await resp.text()
        except Exception:
            continue

        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            txt = _safe_strip(a.get_text(" ", strip=True)).lower()
            if not txt:
                continue
            if "free" in txt or "giveaway" in txt:
                href = a["href"]
                if href.startswith("/"):
                    href = "https://www.gog.com" + href
                out.append({
                    "title": txt[:140],
                    "url": href,
                    "kind": "free_to_keep",
                    "note": "GOG"
                })

    # Deduplicate
    uniq = {}
    for r in out:
        uniq[(r["title"], r["url"])] = r
    return list(uniq.values())


# ---------------- Humble ----------------

async def fetch_humble_offers(session: aiohttp.ClientSession, urls: List[str], timeout_s: int):
    timeout = aiohttp.ClientTimeout(total=timeout_s)
    out = []

    for url in urls:
        try:
            async with session.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                if resp.status >= 400:
                    continue
                html = await resp.text()
        except Exception:
            continue

        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            txt = _safe_strip(a.get_text(" ", strip=True))
            if not txt:
                continue
            low = txt.lower()
            if any(k in low for k in ["bundle", "deal", "sale", "%", "off"]):
                href = a["href"]
                if href.startswith("/"):
                    href = "https://www.humblebundle.com" + href
                out.append({
                    "title": txt[:140],
                    "url": href,
                    "kind": "deal",
                    "note": "Humble"
                })

    uniq = {}
    for r in out:
        uniq[(r["title"], r["url"])] = r
    return list(uniq.values())


# ---------------- Luna ----------------

async def fetch_luna_subscription_picks(session, luna_cfg, timeout_s, cache_path):
    cache = _load_json(cache_path, {})
    wall_now = int(__import__("time").time())
    max_age_s = int(luna_cfg.get("cache_max_age_s", 7 * 24 * 3600))

    if isinstance(cache, dict) and cache.get("items") and isinstance(cache.get("ts"), int):
        if wall_now - cache["ts"] <= max_age_s:
            return list(cache["items"])

    urls = luna_cfg.get("urls") or []
    timeout = aiohttp.ClientTimeout(total=timeout_s)
    items = []

    for url in urls:
        try:
            async with session.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                if resp.status >= 400:
                    continue
                html = await resp.text()
        except Exception:
            continue

        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            txt = _safe_strip(a.get_text(" ", strip=True))
            if not txt:
                continue
            if "/game/" in href or "/games/" in href:
                if href.startswith("/"):
                    href = "https://luna.amazon.com" + href
                items.append({
                    "title": txt[:140],
                    "url": href,
                    "kind": "subscription",
                    "note": "Amazon Luna"
                })

    uniq = {}
    for r in items:
        uniq[(r["title"], r["url"])] = r

    result = list(uniq.values())[:60]

    _save_json(cache_path, {"ts": wall_now, "items": result})
    return result


# ---------------- Gather ----------------

async def gather_offers(registry_path: str, *, timeout_s: int = DEFAULT_TIMEOUT_S, only_free: bool = False):

    reg = _load_json(registry_path, {})
    sources = (reg or {}).get("sources", {})

    epic = sources.get("epic", {})
    gog = sources.get("gog", {})
    humble = sources.get("humble", {})
    luna = sources.get("luna", {})

    offers: List[Offer] = []

    async with aiohttp.ClientSession() as session:

        # ---- Epic (stabilized v2) ----
        endpoint = epic.get("endpoint") or "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions"
        try:
            epic_raw = await fetch_epic_offers(session, endpoint, timeout_s)
            for r in epic_raw:
                offers.append(Offer(platform="epic", kind="free_to_keep", title=r["title"], url=r["url"], note="Epic"))
        except Exception:
            pass

        # ---- GOG ----
        try:
            gog_raw = await fetch_gog_offers(session, gog.get("endpoints", []), timeout_s)
            for r in gog_raw:
                offers.append(Offer(platform="gog", kind="free_to_keep", title=r["title"], url=r["url"], note="GOG"))
        except Exception:
            pass

        # ---- Humble ----
        try:
            humble_raw = await fetch_humble_offers(session, humble.get("urls", []), timeout_s)
            for r in humble_raw:
                offers.append(Offer(platform="humble", kind="deal", title=r["title"], url=r["url"], note="Humble"))
        except Exception:
            pass

        # ---- Luna ----
        cache_file = luna.get("cache_file") or os.path.join(os.path.dirname(registry_path), "luna_cache.json")
        try:
            luna_raw = await fetch_luna_subscription_picks(session, luna, timeout_s, cache_file)
            for r in luna_raw:
                offers.append(Offer(platform="luna", kind="subscription", title=r["title"], url=r["url"], note="Amazon Luna"))
        except Exception:
            pass

    # ---- Normalize ----
    uniq = {}
    for o in offers:
        key = (o.kind + "|" + o.title.lower() + "|" + o.url.lower())
        uniq[key] = o

    offers = list(uniq.values())

    if only_free:
        offers = [o for o in offers if o.kind == "free_to_keep"]

    return sorted(offers, key=lambda x: (x.platform + x.title).lower())

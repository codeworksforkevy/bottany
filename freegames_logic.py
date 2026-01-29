from __future__ import annotations

import os, json, time, asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import aiohttp
import discord

from providers.freegames_humble import fetch_humble_offers, DEFAULT_URLS as HUMBLE_DEFAULT_URLS
from providers.freegames_luna import fetch_luna_subscription_picks

# NOTE: You already have Epic/GOG fetchers somewhere in your repo.
# Keep importing them the same way you do today. If your current file already
# defines fetch_epic_offers / fetch_gog_offers, you can remove these imports.
# NOTE: Epic/GOG fetchers are expected to live in providers/. If they aren't present,
# we fall back to internal minimal implementations by treating those sources as unavailable.
try:
    from providers.freegames_epic import fetch_epic_offers  # type: ignore
except Exception:  # pragma: no cover
    fetch_epic_offers = None  # type: ignore

try:
    from providers.freegames_gog import fetch_gog_offers  # type: ignore
except Exception:  # pragma: no cover
    fetch_gog_offers = None  # type: ignore

def load_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def now_ts() -> float:
    return time.time()

@dataclass
class Offer:
    platform: str
    kind: str  # free_to_keep | deal | subscription
    title: str
    url: str
    note: str = ""

def _dedupe_key(o: Offer) -> str:
    return f"{o.platform}|{o.title}|{o.url}"

def load_registry(data_dir: str) -> Dict[str, Any]:
    # Prefer canonical file
    p1 = os.path.join(data_dir, "freegames_registry.json")
    p2 = os.path.join(data_dir, "free_games_registry.json")
    reg = load_json(p1, None)
    if reg is None:
        reg = load_json(p2, {})
    return reg or {}

async def fetch_all_offers(session: aiohttp.ClientSession, data_dir: str, timeout_s: int = 12) -> List[Offer]:
    reg = load_registry(data_dir)
    sources = (reg.get("sources") or {})
    out: List[Offer] = []

    # Epic (free-to-keep)
    epic = sources.get("epic", {})
    endpoint = epic.get("endpoint") or "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions"
    if fetch_epic_offers:
        try:
            epic_raw = await fetch_epic_offers(session, endpoint, timeout_s)  # type: ignore
            for r in epic_raw:
                out.append(Offer(platform="epic", kind=r.get("kind","free_to_keep"), title=r["title"], url=r["url"], note=r.get("note","")))
        except Exception:
            pass

    # GOG (free-to-keep / giveaway)
    gog = sources.get("gog", {})
    endpoints = gog.get("endpoints") or ["https://www.gog.com/en/partner/free_games", "https://www.gog.com/#giveaway"]
    if fetch_gog_offers:
        try:
            gog_raw = await fetch_gog_offers(session, endpoints, timeout_s)  # type: ignore
            for r in gog_raw:
                out.append(Offer(platform="gog", kind=r.get("kind","free_to_keep"), title=r["title"], url=r["url"], note=r.get("note","")))
        except Exception:
            pass

    # Humble (deals/possible freebies) — treat as 'deal' unless you have a verified free endpoint
    humble = sources.get("humble", {})
    humble_urls = humble.get("urls") or HUMBLE_DEFAULT_URLS
    try:
        humble_raw = await fetch_humble_offers(session, humble_urls, timeout_s)
        for r in humble_raw:
            out.append(Offer(platform="humble", kind=r.get("kind","deal"), title=r["title"], url=r["url"], note=r.get("note","")))
    except Exception:
        pass

    # Amazon Luna (subscription picks from curated registry)
    luna = sources.get("luna", {})
    try:
        luna_raw = await fetch_luna_subscription_picks(luna)
        for r in luna_raw:
            out.append(Offer(platform="luna", kind=r.get("kind","subscription"), title=r["title"], url=r["url"], note=r.get("note","")))
    except Exception:
        pass

    # Dedupe
    seen=set()
    deduped=[]
    for o in out:
        k=_dedupe_key(o)
        if k in seen: 
            continue
        seen.add(k)
        deduped.append(o)
    return deduped

def build_freegames_embed(offers: List[Offer]) -> discord.Embed:
    # You asked for the first sentence to be baby-blue — Discord only supports embed color,
    # so we set the embed accent color to baby blue.
    e = discord.Embed(
        title="Free games & selected deals",
        color=BABY_BLUE
    )
    if not offers:
        e.description = "No updates found right now."
        return e

    lines=[]
    for o in offers[:10]:
        tag = {
            "free_to_keep": "Free-to-keep",
            "deal": "Deal",
            "subscription": "Subscription pick",
        }.get(o.kind, o.kind)
        lines.append(f"**{tag} — {o.title}**\n{o.url}")
        if o.note:
            lines.append(f"*{o.note}*")
        lines.append("")
    e.description = "\n".join(lines).strip()
    e.set_footer(text="Tip: use /freegames only_free:true for 100% free-to-keep only (if enabled).")
    return e

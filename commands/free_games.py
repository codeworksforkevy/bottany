"""
Free games + selected deals (Epic, GOG, Humble, Amazon Luna).

- Slash command group: /freegames ...
- Optional weekly auto-post to a configured channel.
- Public vs ephemeral replies: by default, public (visibility="public").

Notes:
- Amazon Luna "subscription picks" are best-effort scraped from public Luna pages.
  If Amazon changes markup or requires auth, the Luna section may be empty rather than error.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import discord
from discord import app_commands
from discord.ext import commands, tasks

import aiohttp
from bs4 import BeautifulSoup

# -------------------------
# Small utilities
# -------------------------

BABY_BLUE = 0x89CFF0  # Discord embed accent color

def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

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

def _pick_registry(data_dir: str) -> Tuple[str, Dict[str, Any]]:
    """
    Canonicalize the accidental "free_games_registry.json" vs "freegames_registry.json".

    Preference order:
      1) data/freegames_registry.json
      2) data/free_games_registry.json
      3) default empty registry
    """
    p1 = os.path.join(data_dir, "freegames_registry.json")
    p2 = os.path.join(data_dir, "free_games_registry.json")
    if os.path.exists(p1):
        return p1, _load_json(p1, {})
    if os.path.exists(p2):
        return p2, _load_json(p2, {})
    return p1, {}

def _visibility_to_ephemeral(visibility: Optional[str]) -> bool:
    return (visibility or "public").lower().strip() != "public"

# -------------------------
# Model
# -------------------------

@dataclass
class Offer:
    source: str
    title: str
    url: str
    kind: str  # "free" | "deal" | "subscription"
    subtitle: Optional[str] = None
    ends_at: Optional[str] = None

# -------------------------
# Providers
# -------------------------

async def fetch_epic(session: aiohttp.ClientSession, endpoint: str, timeout_s: int = 20) -> List[Offer]:
    """
    Epic freeGamesPromotions endpoint (public JSON).
    """
    offers: List[Offer] = []
    try:
        async with session.get(endpoint, timeout=timeout_s) as r:
            if r.status != 200:
                return offers
            data = await r.json(content_type=None)
    except Exception:
        return offers

    # The JSON shape can vary a bit; we keep this robust.
    elems = (((data or {}).get("data") or {}).get("Catalog") or {}).get("searchStore") or {}
    el = elems.get("elements") or []
    for e in el:
        promos = e.get("promotions") or {}
        # current promotions
        current = (promos.get("promotionalOffers") or [])
        if not current:
            continue
        po = current[0]
        offers_list = po.get("promotionalOffers") or []
        if not offers_list:
            continue
        p = offers_list[0]
        discount = (p.get("discountSetting") or {}).get("discountPercentage")
        if discount != 0:
            continue  # we want free-to-keep
        title = e.get("title") or "Untitled"
        slug = e.get("productSlug") or ""
        url = f"https://store.epicgames.com/en-US/p/{slug}" if slug else "https://store.epicgames.com/"
        ends = p.get("endDate")
        offers.append(Offer(source="Epic", title=title, url=url, kind="free", ends_at=ends))
    return offers

async def fetch_gog(session: aiohttp.ClientSession, endpoints: List[str], timeout_s: int = 20) -> List[Offer]:
    """
    Best-effort scrape of GOG partner free games page (and a couple fallbacks).
    """
    offers: List[Offer] = []
    for url in endpoints:
        try:
            async with session.get(url, timeout=timeout_s, headers={"User-Agent": "Mozilla/5.0"}) as r:
                if r.status != 200:
                    continue
                html = await r.text()
        except Exception:
            continue

        soup = BeautifulSoup(html, "lxml")
        # Try to find giveaway tiles/links
        for a in soup.select("a[href]"):
            href = a.get("href") or ""
            text = (a.get_text(" ", strip=True) or "").strip()
            if not href or not text:
                continue
            if "giveaway" in href.lower() or "free" in text.lower():
                full = href if href.startswith("http") else f"https://www.gog.com{href}"
                # avoid duplicates and very short titles
                if len(text) < 6:
                    continue
                offers.append(Offer(source="GOG", title=text[:120], url=full, kind="free"))
        if offers:
            break

    # de-dupe by url
    seen = set()
    out = []
    for o in offers:
        if o.url in seen:
            continue
        seen.add(o.url)
        out.append(o)
    return out

async def fetch_humble(session: aiohttp.ClientSession, url: str, timeout_s: int = 20) -> List[Offer]:
    """
    Humble Store: best-effort scrape for items marked Free.
    Suggested URL: https://www.humblebundle.com/store/search?sort=bestselling&filter=free
    """
    offers: List[Offer] = []
    try:
        async with session.get(url, timeout=timeout_s, headers={"User-Agent": "Mozilla/5.0"}) as r:
            if r.status != 200:
                return offers
            html = await r.text()
    except Exception:
        return offers

    soup = BeautifulSoup(html, "lxml")
    # Humble is JS-heavy; sometimes server HTML still includes product cards.
    for card in soup.select("[data-entity-type='storefront_product'], .entity-block, .storefront-product-tile, a[href*='/store/']"):
        # normalize to link
        a = card if card.name == "a" else card.select_one("a[href]")
        if not a:
            continue
        href = a.get("href") or ""
        if "/store/" not in href:
            continue
        title = (a.get_text(" ", strip=True) or "").strip()
        if not title:
            continue
        full = href if href.startswith("http") else f"https://www.humblebundle.com{href}"
        # "Free" tag
        text_blob = (card.get_text(" ", strip=True) or "").lower()
        if "free" not in text_blob:
            continue
        offers.append(Offer(source="Humble", title=title[:120], url=full, kind="free"))
    # de-dupe
    seen = set()
    out = []
    for o in offers:
        key = (o.title, o.url)
        if key in seen:
            continue
        seen.add(key)
        out.append(o)
    return out

async def fetch_luna_subscription_picks(session: aiohttp.ClientSession, url: str, timeout_s: int = 20) -> List[Offer]:
    """
    Amazon Luna "subscription picks" (best-effort).
    Default URL: https://luna.amazon.com/
    We scrape visible game tiles/links if present.
    """
    offers: List[Offer] = []
    try:
        async with session.get(url, timeout=timeout_s, headers={"User-Agent": "Mozilla/5.0"}) as r:
            if r.status != 200:
                return offers
            html = await r.text()
    except Exception:
        return offers

    soup = BeautifulSoup(html, "lxml")

    # Strategy A: direct game links
    for a in soup.select("a[href*='/game/']"):
        href = a.get("href") or ""
        title = (a.get_text(" ", strip=True) or "").strip()
        if not title:
            # sometimes text is in aria-label
            title = (a.get("aria-label") or "").strip()
        if not title:
            continue
        full = href if href.startswith("http") else f"https://luna.amazon.com{href}"
        offers.append(Offer(source="Amazon Luna", title=title[:120], url=full, kind="subscription"))

    # Strategy B: embedded JSON blobs (very defensive)
    if not offers:
        m = re.search(r'__NEXT_DATA__\s*=\s*({.*?})\s*</script>', html, flags=re.S)
        if m:
            try:
                data = json.loads(m.group(1))
                # walk a bit to find any list of games with title/slug
                blob = json.dumps(data)
                for mt in re.finditer(r'"title"\s*:\s*"([^"]+)"', blob):
                    title = mt.group(1)
                    if len(title) < 4:
                        continue
                    offers.append(Offer(source="Amazon Luna", title=title[:120], url=url, kind="subscription"))
            except Exception:
                pass

    # De-dupe & cap
    seen = set()
    out = []
    for o in offers:
        key = (o.title.lower(), o.url)
        if key in seen:
            continue
        seen.add(key)
        out.append(o)
    return out[:30]

# -------------------------
# Presentation
# -------------------------

def _build_embed(offers: List[Offer], pool_size: int) -> discord.Embed:
    title = "Free games & selected picks"
    desc = "Latest from Epic, GOG, Humble, and Amazon Luna (subscription picks)."
    emb = discord.Embed(title=title, description=desc, color=BABY_BLUE)
    emb.set_footer(text=f"Pool size: {pool_size}")
    # group by kind
    groups: Dict[str, List[Offer]] = {"free": [], "deal": [], "subscription": []}
    for o in offers:
        groups.get(o.kind, groups["free"]).append(o)

    def add_group(label: str, items: List[Offer]):
        if not items:
            return
        lines = []
        for o in items[:10]:
            extra = f" — {o.subtitle}" if o.subtitle else ""
            end = f" (ends {o.ends_at[:10]})" if o.ends_at else ""
            lines.append(f"• **[{o.title}]({o.url})**{extra}{end}")
        emb.add_field(name=label, value="\n".join(lines)[:1024], inline=False)

    add_group("Free-to-keep", groups["free"])
    add_group("Subscription picks", groups["subscription"])
    if groups["deal"]:
        add_group("Discounts", groups["deal"])
    if not offers:
        emb.add_field(name="Nothing found", value="No items found from the current providers.", inline=False)
    return emb

# -------------------------
# Cog
# -------------------------

class FreeGamesCog(commands.Cog):
    def __init__(self, bot: commands.Bot, data_dir: str):
        self.bot = bot
        self.data_dir = data_dir

        self.registry_path, self.registry = _pick_registry(data_dir)
        src = (self.registry or {}).get("sources", {})

        epic = src.get("epic", {})
        gog = src.get("gog", {})
        humble = src.get("humble", {})
        luna = src.get("luna", {})

        self.enable_epic = epic.get("enabled", True)
        self.enable_gog = gog.get("enabled", True)
        self.enable_humble = humble.get("enabled", True)
        self.enable_luna = luna.get("enabled", True)

        self.epic_endpoint = epic.get("endpoint") or "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions"
        self.gog_endpoints = gog.get("endpoints") or ["https://www.gog.com/en/partner/free_games", "https://www.gog.com/#giveaway"]
        self.humble_url = humble.get("url") or "https://www.humblebundle.com/store/search?sort=bestselling&filter=free"
        self.luna_url = luna.get("url") or "https://luna.amazon.com/"

        self.timeout_s = int((self.registry or {}).get("timeout_s", 20))
        self.max_items = int((self.registry or {}).get("max_items", 25))

        weekly = (self.registry or {}).get("weekly", {})
        self.weekly_enabled = bool(weekly.get("enabled", False))
        self.weekly_channel_id = weekly.get("channel_id")
        self.weekly_hour_utc = int(weekly.get("hour_utc", 9))
        self.weekly_dedupe_days = int(weekly.get("dedupe_days", 7))

        self.state_path = os.path.join(data_dir, "freegames_state.json")
        self.state = _load_json(self.state_path, {"last_weekly": None, "seen": {}})

        self._session: Optional[aiohttp.ClientSession] = None
        if self.weekly_enabled and self.weekly_channel_id:
            self.weekly_loop.start()

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session and not self._session.closed:
            return self._session
        timeout = aiohttp.ClientTimeout(total=self.timeout_s)
        self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def cog_unload(self):
        try:
            self.weekly_loop.cancel()
        except Exception:
            pass
        if self._session and not self._session.closed:
            await self._session.close()

    async def _fetch_all(self) -> List[Offer]:
        session = await self._get_session()
        tasks_list = []
        if self.enable_epic:
            tasks_list.append(fetch_epic(session, self.epic_endpoint, self.timeout_s))
        if self.enable_gog:
            tasks_list.append(fetch_gog(session, self.gog_endpoints, self.timeout_s))
        if self.enable_humble:
            tasks_list.append(fetch_humble(session, self.humble_url, self.timeout_s))
        if self.enable_luna:
            tasks_list.append(fetch_luna_subscription_picks(session, self.luna_url, self.timeout_s))

        results: List[Offer] = []
        for res in await asyncio.gather(*tasks_list, return_exceptions=True):
            if isinstance(res, Exception):
                continue
            results.extend(res)

        # de-dupe by (source,title,url)
        seen = set()
        out = []
        for o in results:
            key = (o.source.lower(), o.title.lower(), o.url)
            if key in seen:
                continue
            seen.add(key)
            out.append(o)

        return out[: self.max_items]

    def _should_post_now(self) -> bool:
        last = self.state.get("last_weekly")
        if last:
            try:
                last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
            except Exception:
                last_dt = None
            if last_dt and (datetime.utcnow() - last_dt.replace(tzinfo=None)) < timedelta(hours=23):
                return False
        now = datetime.utcnow()
        return now.hour == self.weekly_hour_utc

    def _mark_seen(self, offer: Offer, now_iso: str) -> None:
        key = _sha1(f"{offer.source}|{offer.title}|{offer.url}")
        seen = self.state.setdefault("seen", {})
        seen[key] = now_iso

    def _is_recently_seen(self, offer: Offer) -> bool:
        key = _sha1(f"{offer.source}|{offer.title}|{offer.url}")
        seen = self.state.get("seen", {})
        ts = seen.get(key)
        if not ts:
            return False
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            return False
        return (datetime.utcnow() - dt) < timedelta(days=self.weekly_dedupe_days)

    @tasks.loop(minutes=1)
    async def weekly_loop(self):
        if not self.weekly_enabled or not self.weekly_channel_id:
            return
        if not self._should_post_now():
            return
        offers = await self._fetch_all()
        fresh = [o for o in offers if not self._is_recently_seen(o)]
        now_iso = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

        channel = self.bot.get_channel(int(self.weekly_channel_id)) if self.weekly_channel_id else None
        if channel is None and self.weekly_channel_id:
            try:
                channel = await self.bot.fetch_channel(int(self.weekly_channel_id))
            except Exception:
                channel = None
        if channel is None:
            # still update last_weekly to avoid spamming retries
            self.state["last_weekly"] = now_iso
            _save_json(self.state_path, self.state)
            return

        emb = _build_embed(fresh, pool_size=len(fresh))
        emb.title = "Weekly free games & picks"
        try:
            await channel.send(embed=emb)
        except Exception:
            pass

        self.state["last_weekly"] = now_iso
        for o in fresh:
            self._mark_seen(o, now_iso)
        _save_json(self.state_path, self.state)

    @weekly_loop.before_loop
    async def before_weekly_loop(self):
        await self.bot.wait_until_ready()

    # -------------------------
    # Slash command group
    # -------------------------

    freegames = app_commands.Group(
        name="freegames",
        description="Free games & selected picks (Epic, GOG, Humble, Amazon Luna).",
    )

    @freegames.command(name="list", description="Show current free games & picks.")
    @app_commands.describe(visibility="public (default) or ephemeral")
    async def cmd_list(self, interaction: discord.Interaction, visibility: Optional[str] = "public"):
        ephemeral = _visibility_to_ephemeral(visibility)
        await interaction.response.defer(thinking=True, ephemeral=ephemeral)
        offers = await self._fetch_all()
        emb = _build_embed(offers, pool_size=len(offers))
        await interaction.followup.send(embed=emb, ephemeral=ephemeral)

    @freegames.command(name="weekly", description="Post the weekly announcement to the configured channel.")
    async def cmd_weekly(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        offers = await self._fetch_all()
        now_iso = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        for o in offers:
            self._mark_seen(o, now_iso)
        _save_json(self.state_path, self.state)
        # fire-and-forget post
        await interaction.followup.send("OK — posting to the configured weekly channel (if enabled).", ephemeral=True)
        if self.weekly_enabled and self.weekly_channel_id:
            emb = _build_embed(offers, pool_size=len(offers))
            emb.title = "Weekly free games & picks"
            channel = self.bot.get_channel(int(self.weekly_channel_id))
            if channel is None:
                try:
                    channel = await self.bot.fetch_channel(int(self.weekly_channel_id))
                except Exception:
                    channel = None
            if channel is not None:
                try:
                    await channel.send(embed=emb)
                except Exception:
                    pass

async def register_free_games(bot: commands.Bot, data_dir: str) -> None:
    cog = FreeGamesCog(bot, data_dir)
    await bot.add_cog(cog)
    try:
        bot.tree.add_command(cog.freegames)
    except Exception:
        # already registered
        pass

# commands/free_games.py
from __future__ import annotations

import os
import json
import asyncio
import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

def _load_json(path: str, default: Any) -> Any:
    try:
        if not os.path.exists(path):
            return default
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def _save_json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()

def _now_tz(tz_name: str) -> datetime:
    if ZoneInfo is None:
        return datetime.utcnow()
    try:
        return datetime.now(ZoneInfo(tz_name))
    except Exception:
        return datetime.utcnow()

def _parse_int_env(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None:
        return default
    try:
        return int(str(v).strip())
    except Exception:
        return default

def _parse_bool_env(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    s = str(v).strip().lower()
    return s in ("1", "true", "yes", "y", "on")

@dataclass
class Offer:
    source: str  # epic|gog
    title: str
    url: str
    start: Optional[str] = None  # ISO
    end: Optional[str] = None    # ISO
    note: Optional[str] = None

def _within_dedupe_window(last_iso: str, days: int) -> bool:
    try:
        last = datetime.fromisoformat(last_iso.replace("Z", "+00:00"))
    except Exception:
        return False
    return datetime.now(last.tzinfo) - last < timedelta(days=days)

class FreeGamesState:
    def __init__(self, path: str):
        self.path = path
        self.obj: Dict[str, Any] = _load_json(path, default={
            "announced": {},  # offer_id -> {"first_seen": iso, "last_announced": iso}
            "last_weekly_announcement": None
        })

    def save(self) -> None:
        _save_json(self.path, self.obj)

    def mark_announced(self, offer_id: str, now_iso: str) -> None:
        a = self.obj.setdefault("announced", {})
        entry = a.get(offer_id) or {"first_seen": now_iso, "last_announced": now_iso}
        entry["last_announced"] = now_iso
        a[offer_id] = entry

    def recently_announced(self, offer_id: str, dedupe_days: int) -> bool:
        a = self.obj.get("announced", {})
        entry = a.get(offer_id)
        if not entry:
            return False
        last_iso = entry.get("last_announced")
        if not last_iso:
            return False
        return _within_dedupe_window(last_iso, dedupe_days)

    def get_last_weekly(self) -> Optional[str]:
        return self.obj.get("last_weekly_announcement")

    def set_last_weekly(self, now_iso: str) -> None:
        self.obj["last_weekly_announcement"] = now_iso

async def _http_get_json(session: aiohttp.ClientSession, url: str, timeout_s: int) -> Any:
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout_s)) as r:
        r.raise_for_status()
        return await r.json()

async def _http_get_text(session: aiohttp.ClientSession, url: str, timeout_s: int) -> str:
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout_s)) as r:
        r.raise_for_status()
        return await r.text()

def _pick_epic_offers(obj: Any, locale: str = "en-US") -> List[Offer]:
    offers: List[Offer] = []
    elements = None
    try:
        elements = obj.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", None)
    except Exception:
        elements = None
    if not isinstance(elements, list):
        elements = obj.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", []) if isinstance(obj, dict) else []

    for el in elements or []:
        try:
            promos = el.get("promotions") or {}
            p = promos.get("promotionalOffers") or []
            up = promos.get("upcomingPromotionalOffers") or []
            if not p and not up:
                continue

            slug = el.get("productSlug") or el.get("urlSlug") or ""
            url = ""
            if slug:
                slug = slug.replace("/home", "")
                url = f"https://store.epicgames.com/{locale}/p/{slug.strip('/')}"
            else:
                url = "https://store.epicgames.com/free-games"

            title = el.get("title") or el.get("name") or "Epic Free Game"

            start_iso = None
            end_iso = None
            if isinstance(p, list) and p:
                inner = (p[0] or {}).get("promotionalOffers") or []
                if inner:
                    start_iso = (inner[0] or {}).get("startDate")
                    end_iso = (inner[0] or {}).get("endDate")

            offers.append(Offer(source="epic", title=title, url=url, start=start_iso, end=end_iso))
        except Exception:
            continue

    seen = set()
    deduped = []
    for o in offers:
        k = (o.title.lower().strip(), o.url)
        if k in seen:
            continue
        seen.add(k)
        deduped.append(o)
    return deduped

async def fetch_epic_offers(session: aiohttp.ClientSession, endpoint: str, timeout_s: int) -> List[Offer]:
    obj = await _http_get_json(session, endpoint, timeout_s)
    return _pick_epic_offers(obj)

def _extract_gog_links(html: str) -> List[Tuple[str, str]]:
    links: List[Tuple[str, str]] = []
    import re
    hrefs = set(re.findall(r'href="([^"]+?/game/[^"]+)"', html))
    for h in hrefs:
        if h.startswith("//"):
            url = "https:" + h
        elif h.startswith("/"):
            url = "https://www.gog.com" + h
        elif h.startswith("http"):
            url = h
        else:
            url = "https://www.gog.com/" + h.lstrip("/")
        slug = url.split("/game/")[-1].split("?")[0].strip("/")
        title = slug.replace("_", " ").replace("-", " ").title() if slug else "GOG Free Game"
        links.append((title, url))
    return links

async def fetch_gog_offers(session: aiohttp.ClientSession, endpoints: List[str], timeout_s: int) -> List[Offer]:
    offers: List[Offer] = []
    for url in endpoints:
        try:
            html = await _http_get_text(session, url, timeout_s)
            for title, link in _extract_gog_links(html):
                offers.append(Offer(source="gog", title=title, url=link))
        except Exception:
            continue

    seen = set()
    out = []
    for o in offers:
        if o.url in seen:
            continue
        seen.add(o.url)
        out.append(o)
    return out

def _fmt_offer(o: Offer) -> str:
    parts = [f"**{o.title}**", o.url]
    if o.end:
        parts.append(f"Ends: `{o.end}`")
    return " — ".join(parts)

def _group_offers(offers: List[Offer]) -> Dict[str, List[Offer]]:
    d: Dict[str, List[Offer]] = {"epic": [], "gog": []}
    for o in offers:
        d.setdefault(o.source, []).append(o)
    return d

def _compose_message(offers: List[Offer], title: str = "Free games") -> str:
    if not offers:
        return "No free games found right now (best-effort check)."

    groups = _group_offers(offers)
    lines = [f"**{title}**"]
    if groups.get("epic"):
        lines.append("\n**Epic Games Store**")
        for o in groups["epic"][:10]:
            lines.append(f"• {_fmt_offer(o)}")
    if groups.get("gog"):
        lines.append("\n**GOG**")
        for o in groups["gog"][:10]:
            lines.append(f"• {_fmt_offer(o)}")
    return "\n".join(lines)

class FreeGamesCog(commands.Cog):
    def __init__(self, bot: commands.Bot, data_dir: str):
        self.bot = bot
        self.data_dir = data_dir

        self.registry_path = os.path.join(self.data_dir, "free_games_registry.json")
        self.state_path = os.path.join(self.data_dir, "free_games_state.json")

        self.registry = _load_json(self.registry_path, default={})
        self.state = FreeGamesState(self.state_path)

        self.tz_name = os.getenv("TZ_NAME", "Europe/Berlin")

        self.target_channel_id = _parse_int_env("FREE_GAMES_CHANNEL_ID", 0)
        self.target_guild_id = _parse_int_env("FREE_GAMES_GUILD_ID", 0)

        self.timeout_s = _parse_int_env("HTTP_TIMEOUT_SECONDS", 12)
        self.retries = _parse_int_env("HTTP_RETRIES", 2)
        self.backoff_s = _parse_int_env("HTTP_BACKOFF_SECONDS", 2)
        self.user_agent = os.getenv("HTTP_USER_AGENT", "Mozilla/5.0 (compatible; BottanyBot/1.0)")

        self.enable_epic = _parse_bool_env("FREE_GAMES_ENABLE_EPIC", True)
        self.enable_gog = _parse_bool_env("FREE_GAMES_ENABLE_GOG", True)
        self.enable_prime = _parse_bool_env("FREE_GAMES_ENABLE_PRIME", False)

        self.max_items = _parse_int_env("FREE_GAMES_MAX_ITEMS", 10)
        self.dedupe_days = _parse_int_env("FREE_GAMES_DEDUPE_DAYS", 14)
        self.silent_if_empty = _parse_bool_env("FREE_GAMES_SILENT_IF_EMPTY", True)

        self.post_dow = os.getenv("FREE_GAMES_POST_DOW", "MON").strip().upper()
        self.post_hour = _parse_int_env("FREE_GAMES_POST_HOUR", 10)
        self.post_minute = _parse_int_env("FREE_GAMES_POST_MINUTE", 0)

        self._http_session: Optional[aiohttp.ClientSession] = None

        self.weekly_announce_loop.start()

    async def cog_unload(self):
        try:
            self.weekly_announce_loop.cancel()
        except Exception:
            pass
        if self._http_session and not self._http_session.closed:
            await self._http_session.close()

    def _is_target_guild(self, guild: Optional[discord.Guild]) -> bool:
        if not self.target_guild_id:
            return True
        if guild is None:
            return False
        return guild.id == self.target_guild_id

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._http_session and not self._http_session.closed:
            return self._http_session
        headers = {"User-Agent": self.user_agent}
        self._http_session = aiohttp.ClientSession(headers=headers)
        return self._http_session

    async def _fetch_all(self) -> List[Offer]:
        offers: List[Offer] = []
        reg_sources = (self.registry or {}).get("sources", {})

        async def attempt(fn, *args):
            last_err = None
            for _ in range(max(1, self.retries)):
                try:
                    return await fn(*args)
                except Exception as e:
                    last_err = e
                    await asyncio.sleep(self.backoff_s)
            if last_err:
                raise last_err
            return []

        session = await self._get_session()

        if self.enable_epic:
            epic = reg_sources.get("epic", {})
            endpoint = epic.get("endpoint") or "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions"
            try:
                offers.extend(await attempt(fetch_epic_offers, session, endpoint, self.timeout_s))
            except Exception:
                pass

        if self.enable_gog:
            gog = reg_sources.get("gog", {})
            endpoints = gog.get("endpoints") or ["https://www.gog.com/en/partner/free_games", "https://www.gog.com/#giveaway"]
            try:
                offers.extend(await attempt(fetch_gog_offers, session, endpoints, self.timeout_s))
            except Exception:
                pass

        return offers

    def _should_post_now(self) -> bool:
        now = _now_tz(self.tz_name)
        dow = now.strftime("%a").upper()[:3]
        if dow != self.post_dow:
            return False
        if now.hour != self.post_hour or now.minute != self.post_minute:
            return False

        last = self.state.get_last_weekly()
        if last:
            try:
                last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
            except Exception:
                last_dt = None
            if last_dt and (datetime.utcnow() - last_dt.replace(tzinfo=None)) < timedelta(hours=23):
                return False
        return True

    async def _post_weekly_to_channel(self, offers: List[Offer]) -> None:
        if not self.target_channel_id:
            return

        now_iso = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        filtered: List[Offer] = []
        for o in offers:
            offer_id = _sha1(f"{o.source}|{o.title}|{o.url}")
            if self.state.recently_announced(offer_id, self.dedupe_days):
                continue
            filtered.append(o)

        if not filtered and self.silent_if_empty:
            self.state.set_last_weekly(now_iso)
            self.state.save()
            return

        channel = self.bot.get_channel(self.target_channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(self.target_channel_id)
            except Exception:
                return

        if channel is None:
            return

        msg = _compose_message(filtered[: self.max_items], title="Weekly free games")
        try:
            await channel.send(msg)
        except Exception:
            return

        self.state.set_last_weekly(now_iso)
        for o in filtered:
            offer_id = _sha1(f"{o.source}|{o.title}|{o.url}")
            self.state.mark_announced(offer_id, now_iso)
        self.state.save()

    @tasks.loop(minutes=1)
    async def weekly_announce_loop(self):
        if not self._should_post_now():
            return
        offers = await self._fetch_all()
        await self._post_weekly_to_channel(offers)

    @weekly_announce_loop.before_loop
    async def before_weekly_announce(self):
        await self.bot.wait_until_ready()

    # -------------------------
    # Slash commands group
    # -------------------------

    freegames_group = app_commands.Group(
        name="freegames",
        description="Weekly free games (Epic, GOG). Announcements are posted to the configured #gaming channel."
    )

    @freegames_group.command(name="list", description="List current free games (best-effort).")
    async def cmd_list(self, interaction: discord.Interaction):
        offers = (await self._fetch_all())[: self.max_items]
        await interaction.response.send_message(_compose_message(offers, title="Free games (current)"))

    @freegames_group.command(name="epic", description="List current free games from Epic Games Store.")
    async def cmd_epic(self, interaction: discord.Interaction):
        if not self.enable_epic:
            await interaction.response.send_message("Epic source is disabled by configuration.", ephemeral=True)
            return
        reg_sources = (self.registry or {}).get("sources", {})
        epic = reg_sources.get("epic", {})
        endpoint = epic.get("endpoint") or "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions"
        session = await self._get_session()
        offers = (await fetch_epic_offers(session, endpoint, self.timeout_s))[: self.max_items]
        await interaction.response.send_message(_compose_message(offers, title="Free games (Epic)"))

    @freegames_group.command(name="gog", description="List current free games from GOG (best-effort).")
    async def cmd_gog(self, interaction: discord.Interaction):
        if not self.enable_gog:
            await interaction.response.send_message("GOG source is disabled by configuration.", ephemeral=True)
            return
        reg_sources = (self.registry or {}).get("sources", {})
        gog = reg_sources.get("gog", {})
        endpoints = gog.get("endpoints") or ["https://www.gog.com/en/partner/free_games", "https://www.gog.com/#giveaway"]
        session = await self._get_session()
        offers = (await fetch_gog_offers(session, endpoints, self.timeout_s))[: self.max_items]
        await interaction.response.send_message(_compose_message(offers, title="Free games (GOG)"))

    @freegames_group.command(name="weekly", description="Post the weekly free games announcement to the configured #gaming channel.")
    async def cmd_weekly(self, interaction: discord.Interaction):
        if not self._is_target_guild(interaction.guild):
            await interaction.response.send_message("This command is not enabled for this server.", ephemeral=True)
            return
        # Allow command anywhere, but keep public posts locked to target channel
        offers = await self._fetch_all()
        await interaction.response.send_message("Posting weekly announcement to #gaming (if configured).", ephemeral=True)
        await self._post_weekly_to_channel(offers)

async def register_free_games(bot: commands.Bot, data_dir: str) -> None:
    cog = FreeGamesCog(bot, data_dir)
    await bot.add_cog(cog)
    try:
        bot.tree.add_command(cog.freegames_group)
    except Exception:
        pass

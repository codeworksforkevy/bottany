# commands/twitch_badges_watch.py
# Twitch badge watcher for Bottany (Discord bot)
# - Uses official Twitch Helix API for global/channel chat badges
# - Posts new badge versions into a configured Discord channel
#
# Env required:
#   TWITCH_CLIENT_ID
#   TWITCH_CLIENT_SECRET
#
# Optional env:
#   TWITCH_BADGES_POLL_MINUTES (default from config)
#
from __future__ import annotations

import os
import json
import time
import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import discord
from discord import app_commands

# ----------------------------
# Paths / IO helpers
# ----------------------------

CONFIG_FILE = "twitch_badges_watch_config.json"
CACHE_FILE = "twitch_badges_cache.json"

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
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def _config_path(data_dir: str) -> str:
    return os.path.join(data_dir, CONFIG_FILE)

def _cache_path(data_dir: str) -> str:
    return os.path.join(data_dir, CACHE_FILE)

def _default_config() -> Dict[str, Any]:
    return {
        "enabled": False,
        "announce_channel_id": None,
        "poll_minutes": 360,
        "include_channel_badges": False,
        "broadcaster_id": None,
        "max_embeds_per_message": 9  # keep 1 slot for header if you add it later
    }

def _default_cache() -> Dict[str, Any]:
    return {
        "seen": {},   # key -> {"first_seen_ts": int, "scope": "global|channel"}
        "last_check_ts": 0
    }

# ----------------------------
# Twitch API
# ----------------------------

TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
HELIX_GLOBAL_BADGES = "https://api.twitch.tv/helix/chat/badges/global"
HELIX_CHANNEL_BADGES = "https://api.twitch.tv/helix/chat/badges"

@dataclass(frozen=True)
class BadgeVersion:
    scope: str  # "global" or "channel"
    set_id: str
    version_id: str
    title: str
    description: str
    image_url_1x: Optional[str]
    image_url_2x: Optional[str]
    image_url_4x: Optional[str]

def _pick_image(b: BadgeVersion) -> Optional[str]:
    # Prefer highest resolution; Discord will resize.
    return b.image_url_4x or b.image_url_2x or b.image_url_1x

def _badge_key(b: BadgeVersion) -> str:
    return f"{b.scope}:{b.set_id}:{b.version_id}"

class TwitchClient:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self._token: Optional[str] = None
        self._token_expiry_ts: float = 0.0

    async def _ensure_token(self) -> str:
        now = time.time()
        if self._token and now < (self._token_expiry_ts - 60):
            return self._token

        import urllib.parse
        import urllib.request

        payload = urllib.parse.urlencode({
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }).encode("utf-8")

        def _do():
            req = urllib.request.Request(TWITCH_TOKEN_URL, data=payload, method="POST")
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))

        data = await asyncio.to_thread(_do)
        access = data.get("access_token")
        expires = int(data.get("expires_in", 0))
        if not access or expires <= 0:
            raise RuntimeError("Failed to obtain Twitch app access token.")
        self._token = access
        self._token_expiry_ts = now + expires
        return access

    async def _helix_get(self, url: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        import urllib.parse
        import urllib.request

        token = await self._ensure_token()
        if params:
            url = url + "?" + urllib.parse.urlencode(params)

        headers = {
            "Client-Id": self.client_id,
            "Authorization": f"Bearer {token}",
        }

        def _do():
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=25) as resp:
                return json.loads(resp.read().decode("utf-8"))

        return await asyncio.to_thread(_do)

    async def get_global_badges(self) -> List[BadgeVersion]:
        data = await self._helix_get(HELIX_GLOBAL_BADGES)
        return _parse_badges(data, scope="global")

    async def get_channel_badges(self, broadcaster_id: str) -> List[BadgeVersion]:
        data = await self._helix_get(HELIX_CHANNEL_BADGES, params={"broadcaster_id": broadcaster_id})
        return _parse_badges(data, scope="channel")

def _parse_badges(payload: Dict[str, Any], scope: str) -> List[BadgeVersion]:
    out: List[BadgeVersion] = []
    for badge_set in payload.get("data", []) or []:
        set_id = str(badge_set.get("set_id", "") or "")
        for v in badge_set.get("versions", []) or []:
            out.append(BadgeVersion(
                scope=scope,
                set_id=set_id,
                version_id=str(v.get("id", "") or ""),
                title=str(v.get("title", "") or "").strip(),
                description=str(v.get("description", "") or "").strip(),
                image_url_1x=v.get("image_url_1x"),
                image_url_2x=v.get("image_url_2x"),
                image_url_4x=v.get("image_url_4x"),
            ))
    return out

# ----------------------------
# Discord / Watcher
# ----------------------------

class BadgesGroup(app_commands.Group):
    def __init__(self, bot: discord.Client, data_dir: str):
        super().__init__(name="badges", description="Twitch badge watcher (official API)")
        self._bot = bot
        self._data_dir = data_dir

    def _load_cfg(self) -> Dict[str, Any]:
        cfg = _load_json(_config_path(self._data_dir), _default_config())
        base = _default_config()
        base.update(cfg if isinstance(cfg, dict) else {})
        return base

    def _save_cfg(self, cfg: Dict[str, Any]) -> None:
        _save_json(_config_path(self._data_dir), cfg)

    @app_commands.command(name="set_channel", description="Set the Discord channel for badge announcements")
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        cfg = self._load_cfg()
        cfg["announce_channel_id"] = channel.id
        self._save_cfg(cfg)
        await interaction.response.send_message(f"Badge announcements will be posted in {channel.mention}.", ephemeral=True)

    @app_commands.command(name="enable", description="Enable/disable badge watcher")
    async def enable(self, interaction: discord.Interaction, enabled: bool):
        cfg = self._load_cfg()
        cfg["enabled"] = bool(enabled)
        self._save_cfg(cfg)
        await interaction.response.send_message(f"Badge watcher enabled: {cfg['enabled']}", ephemeral=True)

    @app_commands.command(name="status", description="Show badge watcher status")
    async def status(self, interaction: discord.Interaction):
        cfg = self._load_cfg()
        cache = _load_json(_cache_path(self._data_dir), _default_cache())
        ch = cfg.get("announce_channel_id")
        await interaction.response.send_message(
            "Badge watcher status:\n"
            f"- enabled: {cfg.get('enabled')}\n"
            f"- announce_channel_id: {ch}\n"
            f"- include_channel_badges: {cfg.get('include_channel_badges')}\n"
            f"- broadcaster_id: {cfg.get('broadcaster_id')}\n"
            f"- poll_minutes: {cfg.get('poll_minutes')}\n"
            f"- cached_seen: {len((cache or {}).get('seen', {}) or {})}",
            ephemeral=True
        )

    @app_commands.command(name="check", description="Manually check for new badges now")
    async def check(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        n = await check_and_announce(self._bot, self._data_dir, force=True)
        await interaction.followup.send(f"Checked. New badge versions detected: {n}", ephemeral=True)

async def _send_badge_embeds(
    channel: discord.abc.Messageable,
    badges: List[BadgeVersion],
    max_embeds_per_message: int = 9
) -> None:
    # Discord supports up to 10 embeds per message.
    # We send one embed per badge so the image renders directly (set_image/set_thumbnail),
    # instead of putting a markdown link ("Badge image").
    if not badges:
        return

    def _mk_embed(b: BadgeVersion) -> discord.Embed:
        title = b.title or b.set_id
        scope_label = "Global" if b.scope == "global" else "Channel"
        e = discord.Embed(
            title=title,
            description=(b.description or "").strip()[:4096],
            color=0x2F3136
        )
        e.add_field(name="Scope", value=scope_label, inline=True)
        e.add_field(name="Set", value=f"`{b.set_id}`", inline=True)
        e.add_field(name="Version", value=f"`{b.version_id}`", inline=True)

        img = _pick_image(b)
        if img:
            e.set_thumbnail(url=img)
            # If single-badge message, also set big image; otherwise thumbnails are still visible per-embed
            e.set_image(url=img)
        return e

    embeds = [_mk_embed(b) for b in badges]

    # Chunk messages to respect 10-embed limit.
    chunk_size = max(1, min(10, max_embeds_per_message))
    for i in range(0, len(embeds), chunk_size):
        await channel.send(
            content=f"New Twitch badges detected ({len(badges)}) — via official Twitch API.",
            embeds=embeds[i:i+chunk_size]
        )

async def check_and_announce(bot: discord.Client, data_dir: str, force: bool = False) -> int:
    client_id = os.getenv("TWITCH_CLIENT_ID", "").strip()
    client_secret = os.getenv("TWITCH_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        return 0

    cfg = _load_json(_config_path(data_dir), _default_config())
    base = _default_config()
    base.update(cfg if isinstance(cfg, dict) else {})
    cfg = base

    if not cfg.get("enabled") and not force:
        return 0

    announce_channel_id = cfg.get("announce_channel_id")
    if not announce_channel_id:
        return 0

    cache = _load_json(_cache_path(data_dir), _default_cache())
    if not isinstance(cache, dict):
        cache = _default_cache()
    seen = cache.get("seen", {}) or {}
    if not isinstance(seen, dict):
        seen = {}

    twitch = TwitchClient(client_id, client_secret)

    badges: List[BadgeVersion] = []
    try:
        badges.extend(await twitch.get_global_badges())
        if cfg.get("include_channel_badges") and cfg.get("broadcaster_id"):
            badges.extend(await twitch.get_channel_badges(str(cfg.get("broadcaster_id"))))
    except Exception:
        # Fail closed; do not spam logs here.
        return 0

    new: List[BadgeVersion] = []
    now_ts = int(time.time())
    for b in badges:
        key = _badge_key(b)
        if key in seen:
            continue
        new.append(b)
        seen[key] = {"first_seen_ts": now_ts, "scope": b.scope}

    if new:
        # Stable ordering for readability: global first, then channel; then title.
        new.sort(key=lambda x: (0 if x.scope == "global" else 1, (x.title or x.set_id).lower(), x.version_id))
        cache["seen"] = seen
        cache["last_check_ts"] = now_ts
        _save_json(_cache_path(data_dir), cache)

        channel = bot.get_channel(int(announce_channel_id))
        if channel is None:
            return 0

        # IMPORTANT: one embed per badge so images appear inline
        await _send_badge_embeds(channel, new, max_embeds_per_message=int(cfg.get("max_embeds_per_message", 9) or 9))
        return len(new)

    cache["seen"] = seen
    cache["last_check_ts"] = now_ts
    _save_json(_cache_path(data_dir), cache)
    return 0

async def _watch_loop(bot: discord.Client, data_dir: str) -> None:
    await bot.wait_until_ready()
    while not bot.is_closed():
        cfg = _load_json(_config_path(data_dir), _default_config())
        base = _default_config()
        base.update(cfg if isinstance(cfg, dict) else {})
        cfg = base

        poll_minutes = int(os.getenv("TWITCH_BADGES_POLL_MINUTES", str(cfg.get("poll_minutes", 360))) or 360)
        poll_seconds = max(60, poll_minutes * 60)

        try:
            await check_and_announce(bot, data_dir, force=False)
        except Exception:
            pass

        await asyncio.sleep(poll_seconds)

async def register_badges(bot: discord.Client, data_dir: str) -> None:
    # Add /badges group commands
    group = BadgesGroup(bot, data_dir)
    try:
        bot.tree.add_command(group)
    except Exception:
        # In case it's already added
        pass

    # Start watcher loop once
    if not hasattr(bot, "_badges_watch_task"):
        bot._badges_watch_task = asyncio.create_task(_watch_loop(bot, data_dir))

    # Sync is optional; some bots manage sync elsewhere
    try:
        await bot.tree.sync()
    except Exception:
        pass

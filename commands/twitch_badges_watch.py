import os
import json
import asyncio
import datetime
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import discord
from discord import app_commands

try:
    import aiohttp
except Exception as e:
    aiohttp = None  # type: ignore


CONFIG_FILE = "twitch_badges_watch_config.json"
CACHE_FILE = "twitch_badges_cache.json"


# -----------------------------
# Utilities
# -----------------------------
def _safe_load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _safe_save_json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    return v if v not in (None, "") else default


def _fmt_dt(ts: float) -> str:
    try:
        return f"<t:{int(ts)}:R>"
    except Exception:
        return "unknown"


def _chunk(lst: List[Any], n: int) -> List[List[Any]]:
    return [lst[i:i + n] for i in range(0, len(lst), n)]


@dataclass
class BadgeVersion:
    set_id: str
    version_id: str
    title: str
    description: str
    image_url_1x: str
    image_url_2x: str
    image_url_4x: str
    scope: str  # global|channel


# -----------------------------
# Twitch API (official)
# -----------------------------
class TwitchClient:
    """
    Minimal Helix client for badges using App Access Token.

    Docs: Get Global Chat Badges / Get Channel Chat Badges.
    """
    def __init__(self, client_id: str, client_secret: str) -> None:
        if aiohttp is None:
            raise RuntimeError("aiohttp is required for Twitch API calls.")
        self.client_id = client_id
        self.client_secret = client_secret
        self._token: Optional[str] = None
        self._token_expiry_ts: float = 0.0

    async def _ensure_token(self) -> str:
        now = asyncio.get_event_loop().time()
        if self._token and now < (self._token_expiry_ts - 60):
            return self._token

        url = "https://id.twitch.tv/oauth2/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data, timeout=20) as resp:
                if resp.status != 200:
                    txt = await resp.text()
                    raise RuntimeError(f"Twitch token request failed: {resp.status} {txt[:200]}")
                obj = await resp.json()
        token = obj.get("access_token")
        expires_in = int(obj.get("expires_in", 0))
        if not token or expires_in <= 0:
            raise RuntimeError("Twitch token response missing access_token / expires_in.")
        self._token = token
        self._token_expiry_ts = asyncio.get_event_loop().time() + float(expires_in)
        return token

    async def _get(self, url: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        token = await self._ensure_token()
        headers = {
            "Client-Id": self.client_id,
            "Authorization": f"Bearer {token}",
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params, timeout=20) as resp:
                txt = await resp.text()
                if resp.status != 200:
                    raise RuntimeError(f"Twitch API request failed: {resp.status} {txt[:200]}")
                try:
                    return json.loads(txt)
                except Exception:
                    raise RuntimeError("Twitch API returned non-JSON response.")

    async def get_global_chat_badges(self) -> List[BadgeVersion]:
        url = "https://api.twitch.tv/helix/chat/badges/global"
        obj = await self._get(url)
        return _parse_badges_response(obj, scope="global")

    async def get_channel_chat_badges(self, broadcaster_id: str) -> List[BadgeVersion]:
        url = "https://api.twitch.tv/helix/chat/badges"
        obj = await self._get(url, params={"broadcaster_id": broadcaster_id})
        return _parse_badges_response(obj, scope="channel")

    async def get_user_id_by_login(self, login: str) -> Optional[str]:
        url = "https://api.twitch.tv/helix/users"
        obj = await self._get(url, params={"login": login})
        data = obj.get("data", [])
        if isinstance(data, list) and data:
            return str(data[0].get("id") or "")
        return None


def _parse_badges_response(obj: Dict[str, Any], scope: str) -> List[BadgeVersion]:
    out: List[BadgeVersion] = []
    data = obj.get("data", [])
    if not isinstance(data, list):
        return out

    for badge_set in data:
        set_id = str(badge_set.get("set_id") or "")
        versions = badge_set.get("versions", [])
        if not set_id or not isinstance(versions, list):
            continue
        for v in versions:
            version_id = str(v.get("id") or "")
            title = str(v.get("title") or "")
            description = str(v.get("description") or "")
            image_url_1x = str(v.get("image_url_1x") or "")
            image_url_2x = str(v.get("image_url_2x") or "")
            image_url_4x = str(v.get("image_url_4x") or "")
            if not version_id:
                continue
            out.append(BadgeVersion(
                set_id=set_id,
                version_id=version_id,
                title=title,
                description=description,
                image_url_1x=image_url_1x,
                image_url_2x=image_url_2x,
                image_url_4x=image_url_4x,
                scope=scope,
            ))
    return out


# -----------------------------
# Watcher logic
# -----------------------------
def _default_config() -> Dict[str, Any]:
    return {
        "version": 1,
        "enabled": True,
        "discord_channel_id": None,  # set via /badges set_channel
        "watch_global_badges": True,
        "watch_channel_badges": False,
        "twitch_broadcaster_login": _env("TWITCH_STREAMER_LOGIN", ""),
        "twitch_broadcaster_id": _env("TWITCH_BROADCASTER_ID", ""),  # optional; can be resolved
        "poll_minutes": int(_env("TWITCH_BADGES_POLL_MINUTES", "360") or "360"),  # default 6 hours
        "announce_max_badges_per_run": 6,
        "last_run_ts": 0,
    }


def _default_cache() -> Dict[str, Any]:
    return {"version": 1, "seen": {}, "updated_utc": None}


def _badge_key(b: BadgeVersion) -> str:
    return f"{b.scope}:{b.set_id}:{b.version_id}"


def _cache_diff(cache: Dict[str, Any], current: List[BadgeVersion]) -> Tuple[List[BadgeVersion], Dict[str, Any]]:
    seen: Dict[str, Any] = cache.get("seen", {}) if isinstance(cache.get("seen"), dict) else {}
    new_badges: List[BadgeVersion] = []
    for b in current:
        k = _badge_key(b)
        if k not in seen:
            new_badges.append(b)
            seen[k] = {"title": b.title, "description": b.description}
    cache["seen"] = seen
    cache["updated_utc"] = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    return new_badges, cache


class BadgesGroup(app_commands.Group):
    def __init__(self, bot: discord.Client, data_dir: str):
        super().__init__(name="badges", description="Twitch badges watcher (global + optional channel badges)")
        self.bot = bot
        self.data_dir = data_dir

    def _config_path(self) -> str:
        return os.path.join(self.data_dir, CONFIG_FILE)

    def _cache_path(self) -> str:
        return os.path.join(self.data_dir, CACHE_FILE)

    def load_config(self) -> Dict[str, Any]:
        cfg = _safe_load_json(self._config_path(), _default_config())
        merged = _default_config()
        merged.update(cfg if isinstance(cfg, dict) else {})
        return merged

    def save_config(self, cfg: Dict[str, Any]) -> None:
        _safe_save_json(self._config_path(), cfg)

    def load_cache(self) -> Dict[str, Any]:
        return _safe_load_json(self._cache_path(), _default_cache())

    def save_cache(self, cache: Dict[str, Any]) -> None:
        _safe_save_json(self._cache_path(), cache)

    @app_commands.command(name="set_channel", description="Set the Discord channel for badge announcements (this server)")
    async def set_channel(self, interaction: discord.Interaction):
        cfg = self.load_config()
        cfg["discord_channel_id"] = interaction.channel_id
        self.save_config(cfg)
        await interaction.response.send_message("Badge announcements channel set for this bot instance.", ephemeral=True)

    @app_commands.command(name="enable", description="Enable or disable badge announcements")
    @app_commands.describe(enabled="True to enable, False to disable")
    async def enable(self, interaction: discord.Interaction, enabled: bool):
        cfg = self.load_config()
        cfg["enabled"] = bool(enabled)
        self.save_config(cfg)
        await interaction.response.send_message(f"Badges watcher enabled: {cfg['enabled']}", ephemeral=True)

    @app_commands.command(name="status", description="Show watcher status and configuration")
    async def status(self, interaction: discord.Interaction):
        cfg = self.load_config()
        cache = self.load_cache()
        desc = []
        desc.append(f"Enabled: **{cfg.get('enabled')}**")
        desc.append(f"Channel ID: `{cfg.get('discord_channel_id')}`")
        desc.append(f"Watch global: **{cfg.get('watch_global_badges')}**")
        desc.append(f"Watch channel: **{cfg.get('watch_channel_badges')}**")
        desc.append(f"Poll minutes: **{cfg.get('poll_minutes')}**")
        desc.append(f"Last run: {_fmt_dt(float(cfg.get('last_run_ts') or 0))}")
        desc.append(f"Seen badges: **{len((cache.get('seen') or {}))}**")
        embed = discord.Embed(title="Twitch Badges Watcher", description="\n".join(desc), color=0x2F3136)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="check", description="Check now and post any newly detected badges")
    async def check(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        n = await run_badges_check(self.bot, self.data_dir, force=True)
        await interaction.followup.send(f"Checked. New badges announced: **{n}**", ephemeral=True)


async def run_badges_check(bot: discord.Client, data_dir: str, force: bool = False) -> int:
    """
    Returns number of newly announced badge versions.
    """
    cfg_path = os.path.join(data_dir, CONFIG_FILE)
    cache_path = os.path.join(data_dir, CACHE_FILE)

    cfg = _safe_load_json(cfg_path, _default_config())
    merged = _default_config()
    if isinstance(cfg, dict):
        merged.update(cfg)
    cfg = merged

    if not cfg.get("enabled"):
        return 0

    channel_id = cfg.get("discord_channel_id")
    if not channel_id:
        return 0

    client_id = _env("TWITCH_CLIENT_ID")
    client_secret = _env("TWITCH_CLIENT_SECRET")
    if not client_id or not client_secret:
        # Can't operate without app credentials
        return 0

    twitch = TwitchClient(client_id=client_id, client_secret=client_secret)

    # Resolve broadcaster_id if needed for channel badges watch
    broadcaster_id = str(cfg.get("twitch_broadcaster_id") or "").strip()
    broadcaster_login = str(cfg.get("twitch_broadcaster_login") or "").strip()
    if cfg.get("watch_channel_badges") and (not broadcaster_id) and broadcaster_login:
        try:
            broadcaster_id = (await twitch.get_user_id_by_login(broadcaster_login)) or ""
            if broadcaster_id:
                cfg["twitch_broadcaster_id"] = broadcaster_id
                _safe_save_json(cfg_path, cfg)
        except Exception:
            broadcaster_id = ""

    # Rate limit runs
    now_ts = int(asyncio.get_event_loop().time())
    last_run_ts = int(cfg.get("last_run_ts") or 0)
    poll_minutes = int(cfg.get("poll_minutes") or 360)
    if not force and last_run_ts and (now_ts - last_run_ts) < (poll_minutes * 60):
        return 0

    cfg["last_run_ts"] = now_ts
    _safe_save_json(cfg_path, cfg)

    # Fetch badges
    current: List[BadgeVersion] = []
    try:
        if cfg.get("watch_global_badges"):
            current.extend(await twitch.get_global_chat_badges())
        if cfg.get("watch_channel_badges") and broadcaster_id:
            current.extend(await twitch.get_channel_chat_badges(broadcaster_id=broadcaster_id))
    except Exception:
        return 0

    cache = _safe_load_json(cache_path, _default_cache())
    if not isinstance(cache, dict):
        cache = _default_cache()

    new_badges, cache = _cache_diff(cache, current)
    _safe_save_json(cache_path, cache)

    if not new_badges:
        return 0

    # Post announcement (limit per run)
    max_n = int(cfg.get("announce_max_badges_per_run") or 6)
    new_badges = new_badges[:max_n]

    ch = bot.get_channel(int(channel_id))
    if ch is None:
        try:
            ch = await bot.fetch_channel(int(channel_id))
        except Exception:
            return 0

    # Build embed(s)
    announced = 0
    for batch in _chunk(new_badges, 3):
        embed = discord.Embed(
            title=f"New Twitch badge{'s' if len(batch)!=1 else ''} detected ({len(batch)})",
            description="Detected via the official Twitch API (Chat Badges).",
            color=0x9146FF,
        )
        for b in batch:
            scope_label = "Global" if b.scope == "global" else "Channel"
            label = f"{b.title or b.set_id} — {scope_label} (set `{b.set_id}`, v `{b.version_id}`)"
            img = b.image_url_4x or b.image_url_2x or b.image_url_1x
            value = (b.description or "No description.").strip()
            if img:
                value = f"{value}\n[Badge image]({img})"
            if len(value) > 700:
                value = value[:700] + "…"
            embed.add_field(name=label, value=value[:1024], inline=False)

        # Thumbnail: first badge 4x if available
        thumb = batch[0].image_url_4x or batch[0].image_url_2x or batch[0].image_url_1x
        if thumb:
            embed.set_thumbnail(url=thumb)
        # If only one badge in this embed, show the large image too.
        if len(batch) == 1 and thumb:
            embed.set_image(url=thumb)

        try:
            await ch.send(embed=embed)
            announced += len(batch)
        except Exception:
            # ignore to avoid crashing scheduled loop
            pass

    return announced


async def _badges_loop(bot: discord.Client, data_dir: str) -> None:
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            await run_badges_check(bot, data_dir, force=False)
        except Exception:
            pass
        # sleep a bit; actual gating handled by poll_minutes
        await asyncio.sleep(60)


async def register_badges(bot: discord.Client, data_dir: str) -> None:
    """
    Registers the /badges command group and starts the background watcher.
    """
    group = BadgesGroup(bot, data_dir)
    try:
        bot.tree.add_command(group)
    except Exception:
        # might already exist
        pass

    # Start background task once
    if not hasattr(bot, "_badges_watch_task"):
        bot._badges_watch_task = asyncio.create_task(_badges_loop(bot, data_dir))  # type: ignore[attr-defined]

    # Sync (best-effort)
    try:
        await bot.tree.sync()
    except Exception:
        pass

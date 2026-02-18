import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

import aiohttp
import discord
from discord import app_commands

TWITCH_CFG_FILE = "twitch_stream_config.json"
TWITCH_SCHEDULE_FILE = "twitch_schedule.json"
TWITCH_MILESTONES_FILE = "twitch_milestones.json"


# -------------------------
# Helpers
# -------------------------
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


def _now_utc() -> datetime:
    return datetime.utcnow().replace(microsecond=0)


def _cfg_path(data_dir: str) -> str:
    return os.path.join(data_dir, TWITCH_CFG_FILE)


def _schedule_path(data_dir: str) -> str:
    return os.path.join(data_dir, TWITCH_SCHEDULE_FILE)


def _milestones_path(data_dir: str) -> str:
    return os.path.join(data_dir, TWITCH_MILESTONES_FILE)


# -------------------------
# Twitch API
# -------------------------
async def _get_app_token(session: aiohttp.ClientSession) -> Optional[str]:
    client_id = os.getenv("TWITCH_CLIENT_ID", "").strip()
    client_secret = os.getenv("TWITCH_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        return None

    async with session.post(
        "https://id.twitch.tv/oauth2/token",
        params={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
        },
        timeout=20,
    ) as resp:
        if resp.status != 200:
            return None
        data = await resp.json()
        return data.get("access_token")


async def _twitch_get(session, url, token, params):
    client_id = os.getenv("TWITCH_CLIENT_ID", "").strip()
    if not client_id or not token:
        return None

    headers = {"Client-ID": client_id, "Authorization": f"Bearer {token}"}
    async with session.get(url, headers=headers, params=params, timeout=20) as resp:
        if resp.status != 200:
            return None
        return await resp.json()


async def _get_user_id(session, token, login):
    data = await _twitch_get(session, "https://api.twitch.tv/helix/users", token, {"login": login})
    if not data:
        return None
    items = data.get("data", [])
    return str(items[0]["id"]) if items else None


async def _get_stream(session, token, broadcaster_id):
    data = await _twitch_get(session, "https://api.twitch.tv/helix/streams", token, {"user_id": broadcaster_id})
    if not data:
        return None
    items = data.get("data", [])
    return items[0] if items else None


# -------------------------
# Twitch Command Group
# -------------------------
class TwitchGroup(app_commands.Group):
    def __init__(self, bot: discord.Client, data_dir: str):
        super().__init__(name="twitch", description="Twitch stream tools")
        self._bot = bot
        self._data_dir = data_dir
        self._session: Optional[aiohttp.ClientSession] = None
        self._app_token: Optional[str] = None
        self._app_token_expiry: Optional[datetime] = None
        self._last_live_state = {"is_live": False}

    async def _ensure_session(self):
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _ensure_app_token(self):
        if self._app_token and self._app_token_expiry and _now_utc() < self._app_token_expiry:
            return self._app_token

        session = await self._ensure_session()
        tok = await _get_app_token(session)
        if not tok:
            return None

        self._app_token = tok
        self._app_token_expiry = _now_utc() + timedelta(hours=20)
        return tok

    def _cfg(self):
        return _load_json(
            _cfg_path(self._data_dir),
            {"guild_channels": {}, "streamer_login": os.getenv("TWITCH_STREAMER_LOGIN", "").strip()},
        )

    def _save_cfg(self, obj):
        _save_json(_cfg_path(self._data_dir), obj)

    # -------------------------
    # Commands
    # -------------------------
    @app_commands.command(name="status", description="Show stream status")
    async def status(self, interaction: discord.Interaction):
        login = (self._cfg().get("streamer_login") or "").strip()
        if not login:
            await interaction.response.send_message("Streamer login not configured.", ephemeral=True)
            return

        tok = await self._ensure_app_token()
        if not tok:
            await interaction.response.send_message("Twitch credentials missing.", ephemeral=True)
            return

        session = await self._ensure_session()
        uid = await _get_user_id(session, tok, login)
        if not uid:
            await interaction.response.send_message("User not found.", ephemeral=True)
            return

        stream = await _get_stream(session, tok, uid)
        if not stream:
            await interaction.response.send_message("Offline.")
            return

        embed = discord.Embed(
            title="LIVE on Twitch",
            description=stream.get("title") or "(no title)",
            color=discord.Color.purple(),
        )
        embed.add_field(name="Category", value=stream.get("game_name") or "Unknown")
        embed.add_field(name="Watch", value=f"https://twitch.tv/{login}", inline=False)

        await interaction.response.send_message(embed=embed)

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


# -------------------------
# Register Function
# -------------------------
async def register_twitch_stream(bot: discord.Client, data_dir: str):
    group = TwitchGroup(bot, data_dir)
    bot.tree.add_command(group)

    # ❗ GLOBAL SYNC KALDIRILDI
    # Sync işlemi main.py içinde merkezi olarak yapılmalı.

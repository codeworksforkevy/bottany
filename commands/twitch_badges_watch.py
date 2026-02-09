
from __future__ import annotations
import os, json, hashlib, logging
from typing import Any, List, Optional
import aiohttp
import discord
from discord import app_commands
from discord.ext import tasks

logger = logging.getLogger("bottany.twitch_badges")
HELIX_BASE = "https://api.twitch.tv/helix"
TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"

def _load(path: str, default=None):
    try:
        with open(path,"r",encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default or {}

def _save(path: str, obj: Any):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,"w",encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def _hash_obj(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

class TwitchAuth:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self._token = None
        self._exp = 0.0

    async def get_token(self):
        import time
        if self._token and time.time() < (self._exp - 30):
            return self._token
        if not self.client_id or not self.client_secret:
            return None
        async with aiohttp.ClientSession() as s:
            async with s.post(TWITCH_TOKEN_URL, data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
            }) as r:
                js = await r.json()
        self._token = js.get("access_token")
        self._exp = time.time() + int(js.get("expires_in", 60))
        return self._token

async def helix_get(auth: TwitchAuth, path: str):
    token = await auth.get_token()
    if not token:
        raise RuntimeError("Missing Twitch credentials")
    headers = {
        "Client-ID": auth.client_id,
        "Authorization": f"Bearer {token}",
    }
    async with aiohttp.ClientSession(headers=headers) as s:
        async with s.get(HELIX_BASE + path) as r:
            return await r.json()

def _extract_badges(data: dict) -> list[dict]:
    out = []
    for s in data.get("data", []):
        for v in s.get("versions", []):
            out.append({
                "set_id": s.get("set_id"),
                "version": v.get("id"),
                "title": v.get("title",""),
                "image": v.get("image_url_2x","")
            })
    return out

async def register_badges(bot, tree, data_dir: str):
    cache_path = os.path.join(data_dir, "twitch_badges_cache.json")
    state = _load(cache_path, {"hash":"", "badges":[], "updated_utc":""})

    client_id = os.getenv("TWITCH_CLIENT_ID","")
    client_secret = os.getenv("TWITCH_CLIENT_SECRET","")
    auth = TwitchAuth(client_id, client_secret)

    badges_group = app_commands.Group(name="badges", description="Twitch badges")

    @badges_group.command(name="latest", description="Show latest Twitch badges")
    async def latest(interaction: discord.Interaction):
        if not state["badges"]:
            await interaction.response.send_message("No badge cache yet.", ephemeral=True)
            return
        e = discord.Embed(title="Twitch Badges")
        e.description = "\n".join("• " + b["title"] for b in state["badges"][:20])
        if state["badges"][0].get("image"):
            e.set_thumbnail(url=state["badges"][0]["image"])
        await interaction.response.send_message(embed=e)

    tree.add_command(badges_group)

    @tasks.loop(minutes=15)
    async def watcher():
        js = await helix_get(auth, "/chat/badges/global")
        badges = _extract_badges(js)
        h = _hash_obj(badges)
        if h == state.get("hash"):
            return
        state.update({
            "hash": h,
            "badges": badges,
        })
        _save(cache_path, state)

    if not getattr(bot, "_badges_started", False):
        bot._badges_started = True
        watcher.start()

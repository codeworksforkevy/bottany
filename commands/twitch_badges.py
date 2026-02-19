from __future__ import annotations

import os
import json
import hashlib
import logging
import asyncio
import time
from typing import Any, Dict, List, Tuple

import discord
from discord import app_commands
from discord.ext import tasks

from services.http_client import http_client

logger = logging.getLogger("bottany.twitch_badges")

HELIX_BASE = "https://api.twitch.tv/helix"
TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
CACHE_FILE = "twitch_badges_cache.json"


# =========================================================
# JSON UTILS
# =========================================================

def _load(path: str, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default or {"hash": "", "badges": [], "changes": []}


def _save(path: str, obj: Any):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _hash_obj(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


# =========================================================
# AUTH
# =========================================================

class TwitchAuth:

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self._token = None
        self._exp = 0.0

    async def get_token(self):

        if self._token and time.time() < (self._exp - 30):
            return self._token

        if not self.client_id or not self.client_secret:
            return None

        async with http_client.session.post(
            TWITCH_TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
            },
        ) as r:
            js = await r.json()

        self._token = js.get("access_token")
        self._exp = time.time() + int(js.get("expires_in", 60))

        return self._token


# =========================================================
# HELIX GET (Rate-aware + retry)
# =========================================================

async def helix_get(auth: TwitchAuth, path: str):

    token = await auth.get_token()
    if not token:
        raise RuntimeError("Missing Twitch credentials")

    headers = {
        "Client-ID": auth.client_id,
        "Authorization": f"Bearer {token}",
    }

    backoff = 1

    while True:

        async with http_client.session.get(HELIX_BASE + path, headers=headers) as r:

            remaining = r.headers.get("Ratelimit-Remaining")
            limit = r.headers.get("Ratelimit-Limit")
            reset = r.headers.get("Ratelimit-Reset")

            logger.info(
                "Helix budget: remaining=%s limit=%s reset=%s",
                remaining, limit, reset
            )

            if r.status == 429:
                logger.warning("Twitch rate limit hit. Backing off.")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)
                continue

            if r.status != 200:
                logger.warning("Helix returned status %s", r.status)
                return {}

            return await r.json()


# =========================================================
# BADGE PARSER
# =========================================================

def _extract_badges(data: dict) -> List[Dict[str, str]]:
    out = []
    for s in data.get("data", []):
        for v in s.get("versions", []):
            out.append({
                "set_id": s.get("set_id"),
                "version": v.get("id"),
                "title": v.get("title", ""),
                "image": v.get("image_url_2x", "")
            })
    return out


# =========================================================
# REGISTER
# =========================================================

async def register_badges(client: discord.Client, tree, data_dir):

    cache_path = os.path.join(data_dir, CACHE_FILE)
    state = _load(cache_path)

    auth = TwitchAuth(
        os.getenv("TWITCH_CLIENT_ID", ""),
        os.getenv("TWITCH_CLIENT_SECRET", "")
    )

    # -----------------------------------------------------
    # GROUP STRUCTURE
    # -----------------------------------------------------

    existing = tree.get_command("twitch")

    if isinstance(existing, app_commands.Group):
        twitch = existing
    else:
        twitch = app_commands.Group(
            name="twitch",
            description="Twitch utilities"
        )
        tree.add_command(twitch)

    badges_group = app_commands.Group(
        name="badges",
        description="Twitch badges"
    )

    twitch.add_command(badges_group)

    # -----------------------------------------------------
    # COMMAND: latest
    # -----------------------------------------------------

    @badges_group.command(name="latest", description="Show cached Twitch badges")
    async def latest(interaction: discord.Interaction):

        if not state["badges"]:
            await interaction.response.send_message(
                "Badge cache not populated yet.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="👩‍💻 Twitch Global Badges",
            color=0x9146FF
        )

        lines = [
            f"• {b.get('title','Badge')[:200]}"
            for b in state["badges"][:20]
        ]

        embed.description = "\n".join(lines)[:4000]

        if state["badges"][0].get("image"):
            embed.set_thumbnail(url=state["badges"][0]["image"])

        embed.set_footer(text=f"{len(state['badges'])} cached badges")

        await interaction.response.send_message(embed=embed)

    # -----------------------------------------------------
    # COMMAND: grid
    # -----------------------------------------------------

    @badges_group.command(name="grid", description="Show badge image grid")
    async def grid(interaction: discord.Interaction):

        if not state["badges"]:
            await interaction.response.send_message("No badges cached.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🧩 Twitch Badge Grid",
            color=0x9146FF
        )

        lines = [
            f"[{b['title'][:100]}]({b['image']})"
            for b in state["badges"][:12]
            if b.get("image")
        ]

        embed.description = "\n".join(lines)[:4000]

        await interaction.response.send_message(embed=embed)

    # -----------------------------------------------------
    # COMMAND: changes
    # -----------------------------------------------------

    @badges_group.command(name="changes", description="Show recent badge changes")
    async def changes(interaction: discord.Interaction):

        if not state.get("changes"):
            await interaction.response.send_message(
                "No recent badge changes detected.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🔄 Recent Badge Changes",
            color=0xF59E0B
        )

        embed.description = "\n".join(state["changes"][:15])[:4000]

        await interaction.response.send_message(embed=embed)

    # -----------------------------------------------------
    # WATCHER
    # -----------------------------------------------------

    @tasks.loop(minutes=15)
    async def watcher():

        try:
            js = await helix_get(auth, "/chat/badges/global")
            badges = _extract_badges(js)

            old_ids = {(b["set_id"], b["version"]) for b in state.get("badges", [])}
            new_ids = {(b["set_id"], b["version"]) for b in badges}

            added = new_ids - old_ids
            removed = old_ids - new_ids

            if not added and not removed:
                return

            changes = []

            for b in badges:
                key = (b["set_id"], b["version"])
                if key in added:
                    changes.append(f"Added: {b.get('title','Badge')}")

            for b in state.get("badges", []):
                key = (b["set_id"], b["version"])
                if key in removed:
                    changes.append(f"Removed: {b.get('title','Badge')}")

            state["hash"] = _hash_obj(badges)
            state["badges"] = badges
            state["changes"] = changes[:20]

            _save(cache_path, state)

            logger.info("Badge changes detected +%s -%s", len(added), len(removed))

        except Exception as e:
            logger.warning("Badge watcher error: %s", e)

    @watcher.before_loop
    async def before():
        await client.wait_until_ready()

    if not getattr(client, "_badges_started", False):
        client._badges_started = True
        watcher.start()

from __future__ import annotations

import os
import time
import asyncio
import aiohttp
import discord
from discord import app_commands
from typing import List, Dict, Any, Optional

HELIX_BADGES = "https://api.twitch.tv/helix/chat/badges/global"

COLOR_TWITCH = 0x9146FF
COLOR_EVENT = 0xF59E0B

# ---------------------------
# Simple in-memory cache
# ---------------------------
_BADGE_CACHE: Dict[str, Any] = {
    "data": None,
    "expires": 0
}

CACHE_TTL = 300  # 5 minutes


def _load_drops(data_dir: str) -> List[Dict[str, Any]]:
    path = os.path.join(data_dir, "twitch_drops_registry.json")
    if not os.path.exists(path):
        return []
    try:
        import json
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        drops = obj.get("drops", [])
        return [d for d in drops if d.get("status") == "active"]
    except Exception:
        return []


async def _fetch_badges(session: aiohttp.ClientSession) -> List[Dict[str, str]]:
    # Cache check
    now = time.time()
    if _BADGE_CACHE["data"] and _BADGE_CACHE["expires"] > now:
        return _BADGE_CACHE["data"]

    cid = os.getenv("TWITCH_CLIENT_ID")
    tok = os.getenv("TWITCH_APP_TOKEN")

    if not cid or not tok:
        return []

    headers = {
        "Client-ID": cid,
        "Authorization": f"Bearer {tok}"
    }

    try:
        async with session.get(
            HELIX_BADGES,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=10)
        ) as r:

            if r.status == 429:
                retry_after = int(r.headers.get("Retry-After", 3))
                await asyncio.sleep(retry_after)
                return []

            if r.status != 200:
                return []

            data = await r.json()

    except asyncio.TimeoutError:
        return []
    except aiohttp.ClientError:
        return []

    out = []
    for s in data.get("data", []):
        for v in s.get("versions", []):
            out.append({
                "title": v.get("title") or s.get("set_id"),
                "img": v.get("image_url_2x")
            })

    # Store in cache
    _BADGE_CACHE["data"] = out
    _BADGE_CACHE["expires"] = now + CACHE_TTL

    return out


def register_twitch_unified_feed(
    client: discord.Client,
    tree: app_commands.CommandTree,
    data_dir: str
) -> None:

    session: Optional[aiohttp.ClientSession] = None

    @client.event
    async def on_ready():
        nonlocal session
        if session is None:
            session = aiohttp.ClientSession()

    @tree.command(
        name="twitchfeed",
        description="Unified Twitch feed (badges + active drops)."
    )
    async def twitchfeed(interaction: discord.Interaction):

        await interaction.response.defer(thinking=True)

        if session is None:
            await interaction.followup.send("Twitch session not ready.")
            return

        badges = await _fetch_badges(session)
        drops = _load_drops(data_dir)

        embeds = []

        if badges:
            e = discord.Embed(
                title="👩‍💻 Twitch Badges",
                description="Latest global Twitch chat badges.",
                color=COLOR_TWITCH
            )
            if badges[0].get("img"):
                e.set_thumbnail(url=badges[0]["img"])
            e.set_footer(text=f"{len(badges)} total badges")
            embeds.append(e)

        if drops:
            e2 = discord.Embed(
                title="🎁 Active Twitch Drops",
                color=COLOR_EVENT
            )
            e2.description = "\n".join(
                f"• {d.get('game','Unknown')} — {d.get('campaign','')}"
                for d in drops[:5]
            )
            embeds.append(e2)

        if not embeds:
            await interaction.followup.send("No Twitch data available.")
            return

        await interaction.followup.send(embeds=embeds)

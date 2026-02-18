from __future__ import annotations
import os
import time
from typing import List, Dict, Any

import aiohttp
import discord
from discord import app_commands

COLOR_TWITCH = 0x9146FF
HELIX_GLOBAL_BADGES = "https://api.twitch.tv/helix/chat/badges/global"

# -------------------------------------------------
# MEMORY CACHE
# -------------------------------------------------
_BADGE_CACHE: Dict[str, Any] = {
    "data": [],
    "expires": 0
}

CACHE_TTL = int(os.getenv("TWITCH_BADGE_CACHE_SECONDS", "600"))  # 10 min


# -------------------------------------------------
# TWITCH API
# -------------------------------------------------
async def fetch_global_badges(client_id: str, app_token: str) -> List[Dict[str, Any]]:
    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {app_token}"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(HELIX_GLOBAL_BADGES, headers=headers) as resp:
            if resp.status != 200:
                return []
            payload = await resp.json()

    out = []
    for s in payload.get("data", []):
        for v in s.get("versions", []):
            out.append({
                "title": v.get("title") or s.get("set_id"),
                "image": v.get("image_url_4x") or v.get("image_url_2x")
            })

    return out


async def get_badges_cached(client_id: str, token: str):
    now = time.time()

    if _BADGE_CACHE["data"] and now < _BADGE_CACHE["expires"]:
        return _BADGE_CACHE["data"]

    badges = await fetch_global_badges(client_id, token)

    if badges:
        _BADGE_CACHE["data"] = badges
        _BADGE_CACHE["expires"] = now + CACHE_TTL

    return badges


# -------------------------------------------------
# REGISTER
# -------------------------------------------------
async def register_twitch_badges(bot: discord.Client, data_dir: str):

    group = app_commands.Group(
        name="badges",
        description="Twitch badges"
    )

    @group.command(name="all", description="All global Twitch badges.")
    async def all_badges(interaction: discord.Interaction):

        await interaction.response.defer()

        client_id = os.getenv("TWITCH_CLIENT_ID", "").strip()
        token = os.getenv("TWITCH_APP_TOKEN", "").strip()

        if not client_id or not token:
            await interaction.followup.send(
                "Twitch API credentials missing.",
                ephemeral=True
            )
            return

        badges = await get_badges_cached(client_id, token)

        if not badges:
            await interaction.followup.send("Could not fetch badges.")
            return

        embed = discord.Embed(
            title="Twitch Global Badges",
            description=f"Showing first {min(len(badges), 20)} badges",
            color=COLOR_TWITCH
        )

        # Liste
        embed.description += "\n\n" + "\n".join(
            f"• {b['title']}" for b in badges[:20]
        )

        # Thumbnail preview (ilk badge görseli)
        first_image = badges[0].get("image")
        if first_image:
            embed.set_thumbnail(url=first_image)

        await interaction.followup.send(embed=embed)

    bot.tree.add_command(group)



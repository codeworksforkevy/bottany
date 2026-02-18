from __future__ import annotations
import os
from typing import List, Dict, Any

import aiohttp
import discord
from discord import app_commands

COLOR_TWITCH = 0x9146FF
HELIX_GLOBAL_BADGES = "https://api.twitch.tv/helix/chat/badges/global"


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
                "image": v.get("image_url_2x")
            })

    return out


# -------------------------------------------------
# REGISTER (NEW ARCHITECTURE)
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
        app_token = os.getenv("TWITCH_APP_TOKEN", "").strip()

        if not client_id or not app_token:
            await interaction.followup.send(
                "Twitch API credentials missing.",
                ephemeral=True
            )
            return

        badges = await fetch_global_badges(client_id, app_token)

        if not badges:
            await interaction.followup.send("Could not fetch badges.")
            return

        embed = discord.Embed(
            title="Twitch Global Badges",
            color=COLOR_TWITCH
        )

        embed.description = "\n".join(
            f"• {b['title']}" for b in badges[:20]
        )

        await interaction.followup.send(embed=embed)

    bot.tree.add_command(group)



from __future__ import annotations
import os, json, time, re
from typing import List, Dict, Any
import aiohttp
import discord
from discord import app_commands

COLOR_TWITCH = 0x9146FF

HELIX_GLOBAL_BADGES = "https://api.twitch.tv/helix/chat/badges/global"

async def fetch_global_badges(client_id: str, app_token: str, session: aiohttp.ClientSession):
    headers = {"Client-ID": client_id, "Authorization": f"Bearer {app_token}"}
    async with session.get(HELIX_GLOBAL_BADGES, headers=headers) as resp:
        payload = await resp.json()
    out = []
    for s in payload.get("data", []):
        for v in s.get("versions", []):
            out.append({
                "title": v.get("title") or s.get("set_id"),
                "image": v.get("image_url_2x")
            })
    return out

def register_twitch_badges(client: discord.Client, tree: app_commands.CommandTree, data_dir: str) -> None:
    group = app_commands.Group(name="badges", description="Twitch badges")

    @group.command(name="all", description="All global Twitch badges.")
    async def all_badges(interaction: discord.Interaction):
        await interaction.response.defer()
        cid = os.getenv("TWITCH_CLIENT_ID")
        tok = os.getenv("TWITCH_APP_TOKEN")
        async with aiohttp.ClientSession() as session:
            badges = await fetch_global_badges(cid, tok, session)
        e = discord.Embed(title="Twitch Badges", color=COLOR_TWITCH)
        e.description = "\n".join(f"• {b['title']}" for b in badges[:20])
        await interaction.followup.send(embed=e)

    tree.add_command(group)

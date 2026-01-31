
from __future__ import annotations

import os
import time
import aiohttp
import discord
from discord import app_commands
from typing import List, Dict, Any

HELIX_BADGES = "https://api.twitch.tv/helix/chat/badges/global"

COLOR_TWITCH = 0x9146FF
COLOR_EVENT = 0xF59E0B

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

async def _fetch_badges() -> List[Dict[str, str]]:
    cid = os.getenv("TWITCH_CLIENT_ID")
    tok = os.getenv("TWITCH_APP_TOKEN")
    headers = {"Client-ID": cid, "Authorization": f"Bearer {tok}"}
    async with aiohttp.ClientSession() as session:
        async with session.get(HELIX_BADGES, headers=headers) as r:
            data = await r.json()
    out = []
    for s in data.get("data", []):
        for v in s.get("versions", []):
            out.append({
                "title": v.get("title") or s.get("set_id"),
                "img": v.get("image_url_2x")
            })
    return out

def register_twitch_unified_feed(client: discord.Client, tree: app_commands.CommandTree, data_dir: str) -> None:
    @tree.command(name="twitchfeed", description="Unified Twitch feed (badges + active drops).")
    async def twitchfeed(interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        badges = await _fetch_badges()
        drops = _load_drops(data_dir)

        embeds = []

        if badges:
            e = discord.Embed(
                title="Twitch Badges",
                description="Latest global Twitch chat badges.",
                color=COLOR_TWITCH
            )
            e.set_thumbnail(url=badges[0]["img"])
            e.set_footer(text=f"{len(badges)} total badges")
            embeds.append(e)

        if drops:
            e2 = discord.Embed(
                title="Active Twitch Drops",
                color=COLOR_EVENT
            )
            e2.description = "\n".join(
                f"• {d.get('game','')} — {d.get('campaign','')}" for d in drops[:5]
            )
            embeds.append(e2)

        if not embeds:
            await interaction.followup.send("No Twitch data available.")
            return

        await interaction.followup.send(embeds=embeds)

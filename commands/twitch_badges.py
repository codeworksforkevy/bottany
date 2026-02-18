from __future__ import annotations
import os
import time
import json
import asyncio
from typing import List, Dict, Any, Optional

import aiohttp
import discord
from discord import app_commands

COLOR_TWITCH = 0x9146FF
HELIX_GLOBAL_BADGES = "https://api.twitch.tv/helix/chat/badges/global"

CACHE_TTL = int(os.getenv("TWITCH_BADGE_CACHE_SECONDS", "600"))
BACKOFF_BASE = 2
MAX_BACKOFF = 60

_BADGE_CACHE: Dict[str, Any] = {
    "data": [],
    "expires": 0,
    "refreshing": False
}


# -------------------------------------------------
# DISK CACHE
# -------------------------------------------------
def _cache_file(data_dir: str):
    return os.path.join(data_dir, "twitch_badges_cache.json")


def load_disk_cache(data_dir: str):
    try:
        with open(_cache_file(data_dir), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_disk_cache(data_dir: str, data: List[Dict[str, Any]]):
    try:
        os.makedirs(data_dir, exist_ok=True)
        with open(_cache_file(data_dir), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# -------------------------------------------------
# TWITCH API (Rate-limit aware)
# -------------------------------------------------
async def fetch_global_badges(client_id: str, token: str) -> List[Dict[str, Any]]:
    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {token}"
    }

    backoff = 1

    async with aiohttp.ClientSession() as session:
        while True:
            async with session.get(HELIX_GLOBAL_BADGES, headers=headers) as resp:

                if resp.status == 429:
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * BACKOFF_BASE, MAX_BACKOFF)
                    continue

                if resp.status != 200:
                    return []

                payload = await resp.json()
                break

    out = []
    for s in payload.get("data", []):
        for v in s.get("versions", []):
            out.append({
                "title": v.get("title") or s.get("set_id"),
                "image": v.get("image_url_4x") or v.get("image_url_2x")
            })

    return out


# -------------------------------------------------
# SMART CACHE LAYER
# -------------------------------------------------
async def get_badges(client_id: str, token: str, data_dir: str):

    now = time.time()

    # 1️⃣ Fresh memory cache
    if _BADGE_CACHE["data"] and now < _BADGE_CACHE["expires"]:
        return _BADGE_CACHE["data"]

    # 2️⃣ Expired but usable → return old & refresh in background
    if _BADGE_CACHE["data"] and not _BADGE_CACHE["refreshing"]:
        _BADGE_CACHE["refreshing"] = True

        async def refresh():
            try:
                badges = await fetch_global_badges(client_id, token)
                if badges:
                    _BADGE_CACHE["data"] = badges
                    _BADGE_CACHE["expires"] = time.time() + CACHE_TTL
                    save_disk_cache(data_dir, badges)
            finally:
                _BADGE_CACHE["refreshing"] = False

        asyncio.create_task(refresh())

        return _BADGE_CACHE["data"]

    # 3️⃣ No memory → try API
    badges = await fetch_global_badges(client_id, token)

    if badges:
        _BADGE_CACHE["data"] = badges
        _BADGE_CACHE["expires"] = now + CACHE_TTL
        save_disk_cache(data_dir, badges)
        return badges

    # 4️⃣ API failed → fallback to disk
    disk_data = load_disk_cache(data_dir)
    if disk_data:
        _BADGE_CACHE["data"] = disk_data
        _BADGE_CACHE["expires"] = now + 120
        return disk_data

    return []


# -------------------------------------------------
# REGISTER
# -------------------------------------------------
async def register_twitch_badges(bot: discord.Client, data_dir: str):

    group = app_commands.Group(
        name="badges",
        description="Twitch badges"
    )

    @group.command(name="all", description="List global Twitch badges.")
    async def all_badges(interaction: discord.Interaction):

        await interaction.response.defer()

        cid = os.getenv("TWITCH_CLIENT_ID", "").strip()
        tok = os.getenv("TWITCH_APP_TOKEN", "").strip()

        if not cid or not tok:
            await interaction.followup.send("Missing Twitch credentials.", ephemeral=True)
            return

        badges = await get_badges(cid, tok, data_dir)

        if not badges:
            await interaction.followup.send("No badge data available.")
            return

        embed = discord.Embed(
            title="Twitch Global Badges",
            description="\n".join(f"• {b['title']}" for b in badges[:20]),
            color=COLOR_TWITCH
        )

        await interaction.followup.send(embed=embed)

    # -------------------------------------------------
    # SINGLE BADGE PREVIEW
    # -------------------------------------------------
    @group.command(name="view", description="View a specific badge thumbnail.")
    @app_commands.describe(name="Badge name")
    async def view_badge(interaction: discord.Interaction, name: str):

        await interaction.response.defer()

        cid = os.getenv("TWITCH_CLIENT_ID", "").strip()
        tok = os.getenv("TWITCH_APP_TOKEN", "").strip()

        if not cid or not tok:
            await interaction.followup.send("Missing Twitch credentials.", ephemeral=True)
            return

        badges = await get_badges(cid, tok, data_dir)

        badge = next((b for b in badges if name.lower() in b["title"].lower()), None)

        if not badge:
            await interaction.followup.send("Badge not found.")
            return

        embed = discord.Embed(
            title=badge["title"],
            color=COLOR_TWITCH
        )

        if badge["image"]:
            embed.set_thumbnail(url=badge["image"])

        await interaction.followup.send(embed=embed)

    bot.tree.add_command(group)




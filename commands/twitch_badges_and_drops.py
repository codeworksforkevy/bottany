from __future__ import annotations

import os
import json
import random
import discord
from discord import app_commands

REG_FILE = "twitch_badges_and_drops_registry.json"


def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_campaigns(data_dir: str) -> list[dict]:
    path = os.path.join(data_dir, REG_FILE)
    if not os.path.exists(path):
        return []
    obj = _load_json(path)
    items = obj.get("campaigns", [])
    return items if isinstance(items, list) else []


def _fmt_sources(c: dict) -> str:
    srcs = c.get("sources", [])
    if not isinstance(srcs, list) or not srcs:
        return "—"
    parts = []
    for s in srcs[:6]:
        name = (s.get("name") or "Source").strip()
        url = (s.get("url") or "").strip()
        if url:
            parts.append(f"[{name}]({url})")
        else:
            parts.append(name)
    return " | ".join(parts)[:1024]


def register_twitch_badges_and_drops(bot: discord.Client, data_dir: str) -> None:
    twitch = app_commands.Group(name="twitch", description="Twitch badges & drops (curated).")

    @twitch.command(
        name="badges_and_drops",
        description="Shows a curated Twitch badges & drops campaign (random).",
    )
    async def badges_and_drops(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        campaigns = _load_campaigns(data_dir)
        if not campaigns:
            await interaction.followup.send("Registry is empty: data/twitch_badges_and_drops_registry.json", ephemeral=True)
            return

        c = random.choice(campaigns)
        title = (c.get("title") or "Twitch Badges & Drops").strip()
        game = (c.get("game") or "").strip()
        window = (c.get("time_window") or "").strip()
        summary = (c.get("summary") or "").strip()
        thumb = (c.get("thumbnail_url") or "").strip()

        embed = discord.Embed(title=title, description=summary or "—")
        if game:
            embed.add_field(name="Game", value=game, inline=True)
        if window:
            embed.add_field(name="Time window", value=window, inline=True)
        embed.add_field(name="Sources", value=_fmt_sources(c), inline=False)
        if thumb:
            embed.set_thumbnail(url=thumb)
        embed.set_footer(text="Curated dataset. We love Kevy")
        await interaction.followup.send(embed=embed, ephemeral=True)

    bot.tree.add_command(twitch)

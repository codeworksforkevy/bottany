from __future__ import annotations

import os
import json
import random
import discord
from discord import app_commands


REG_FILE = "twitch_badges_and_drops_registry.json"


# --------------------------------------------------------
# SAFE LOAD
# --------------------------------------------------------

def _load_campaigns(data_dir: str) -> list[dict]:

    path = os.path.join(data_dir, REG_FILE)

    if not os.path.exists(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
    except Exception:
        return []

    items = obj.get("campaigns", [])
    return items if isinstance(items, list) else []


def _fmt_sources(c: dict) -> str:

    srcs = c.get("sources", [])
    if not isinstance(srcs, list) or not srcs:
        return "—"

    parts = []

    for s in srcs[:6]:
        name = (s.get("name") or "Source").strip()[:80]
        url = (s.get("url") or "").strip()

        if url:
            parts.append(f"[{name}]({url})")
        else:
            parts.append(name)

    joined = " | ".join(parts)
    return joined[:1024] if joined else "—"


# --------------------------------------------------------
# REGISTER
# --------------------------------------------------------

def register_twitch_badges_and_drops(bot: discord.Client, data_dir: str) -> None:

    existing = bot.tree.get_command("twitch")

    if isinstance(existing, app_commands.Group):
        twitch = existing
    else:
        twitch = app_commands.Group(
            name="twitch",
            description="Twitch utilities"
        )
        bot.tree.add_command(twitch)

    @twitch.command(
        name="badges_and_drops",
        description="Discover a random curated Twitch badges & drops campaign."
    )
    async def badges_and_drops(interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)

        campaigns = _load_campaigns(data_dir)

        if not campaigns:
            await interaction.followup.send(
                "No curated campaigns available yet.",
                ephemeral=True
            )
            return

        c = random.choice(campaigns)

        title = (c.get("title") or "Twitch Badges & Drops").strip()[:256]
        summary = (c.get("summary") or "").strip()
        game = (c.get("game") or "").strip()[:1024]
        window = (c.get("time_window") or "").strip()[:1024]
        thumb = (c.get("thumbnail_url") or "").strip()

        if summary:
            summary = summary[:4096]
        else:
            summary = "—"

        embed = discord.Embed(
            title=title,
            description=summary,
            color=0x9146FF
        )

        if game:
            embed.add_field(name="Game", value=game, inline=True)

        if window:
            embed.add_field(name="Time Window", value=window, inline=True)

        embed.add_field(
            name="Sources",
            value=_fmt_sources(c),
            inline=False
        )

        if thumb:
            embed.set_thumbnail(url=thumb)

        embed.set_footer(text="Curated dataset. We love Kevy")

        await interaction.followup.send(embed=embed, ephemeral=True)

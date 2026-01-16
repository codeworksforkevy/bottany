from __future__ import annotations

import os
import json
import random
import discord
from discord import app_commands

REG_FILE = "consoles_registry.json"

def _load_items(data_dir: str) -> list[dict]:
    path = os.path.join(data_dir, REG_FILE)
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    items = obj.get("items", [])
    return items if isinstance(items, list) else []

def _fmt_source(item: dict) -> str:
    src = (item.get("source") or "").strip()
    url = (item.get("source_url") or "").strip()
    if src and url:
        return f"[{src}]({url})"
    return src or url or "—"

def register_history_of_the_consoles(bot: discord.Client, data_dir: str) -> None:
    """Registers /console random"""
    console = app_commands.Group(name="console", description="Console history commands (curated).")

    @console.command(name="random", description="Shows a random game console from history.")
    async def random_console(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        items = _load_items(data_dir)
        if not items:
            await interaction.followup.send("Console registry is empty.", ephemeral=True)
            return

        item = random.choice(items)
        name = item.get("name", "Unknown console")
        year = item.get("release_year", "—")
        mfg = item.get("manufacturer", "Unknown manufacturer")
        intro = item.get("short_intro", "") or item.get("why_it_matters", "")
        img = (item.get("image_url") or "").strip()

        embed = discord.Embed(
            title=f"{name} ({year})",
            description=f"**Manufacturer:** {mfg}\n\n{intro}".strip(),
        )
        if img:
            embed.set_image(url=img)

        embed.add_field(name="Source", value=_fmt_source(item)[:1024], inline=False)
        embed.set_footer(text="Curated registry • We love Kevy")
        await interaction.followup.send(embed=embed, ephemeral=True)

    bot.tree.add_command(console)

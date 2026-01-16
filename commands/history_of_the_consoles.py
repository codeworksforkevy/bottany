from __future__ import annotations

import os
import json
import random
import logging
import discord
from discord import app_commands

REG_FILE = "consoles_registry.json"
ICON_CONSOLE = "🧩"
ICON_SOURCE = "🔗"

logger = logging.getLogger("bottany")

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
    """Registers /console random.

    This function is defensive:
    - If a /console group already exists, it reuses it.
    - It will not crash the bot on duplicate registration.
    """
    try:
        existing = bot.tree.get_command("console")
    except Exception:
        existing = None

    if isinstance(existing, app_commands.Group):
        console_group = existing
    else:
        console_group = app_commands.Group(name="console", description="Console history commands (curated).")
        try:
            bot.tree.add_command(console_group)
        except Exception as e:
            # If already registered by another module, reuse it
            logger.warning("console group add skipped: %s", e)
            try:
                existing2 = bot.tree.get_command("console")
                if isinstance(existing2, app_commands.Group):
                    console_group = existing2
            except Exception:
                pass

    @console_group.command(name="random", description="Shows a random game console from history.")
    async def random_console(interaction: discord.Interaction):
        await interaction.response.defer()  # public response
        items = _load_items(data_dir)
        if not items:
            await interaction.followup.send("Console registry is empty.")
            return

        item = random.choice(items)
        name = item.get("name", "Unknown console")
        year = item.get("release_year", "—")
        mfg = item.get("manufacturer", "Unknown manufacturer")
        intro = item.get("short_intro", "") or item.get("why_it_matters", "")
        img = (item.get("image_url") or "").strip()

        embed = discord.Embed(
            title=f"{ICON_CONSOLE} {name} ({year})",
            description=f"**🏷️ Manufacturer:** {mfg}\n\n{intro}".strip(),
        )
        if img:
            embed.set_image(url=img)

        embed.add_field(name=f"{ICON_SOURCE} Source", value=_fmt_source(item)[:1024], inline=False)
        embed.set_footer(text="Curated registry • We love Kevy")
        await interaction.followup.send(embed=embed)

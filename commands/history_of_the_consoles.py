from __future__ import annotations

import os
import json
import logging
import secrets
import discord
from discord import app_commands

REG_FILE = "consoles_registry.json"
ICON_CONSOLE = "🧩"
ICON_SOURCE = "🔗"

logger = logging.getLogger("bottany")

_LAST_BY_CHANNEL: dict[int, str] = {}

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

def _pick_non_repeating(items: list[dict], channel_id: int) -> dict:
    if not items:
        return {}
    last_id = _LAST_BY_CHANNEL.get(channel_id)
    rng = secrets.SystemRandom()

    if len(items) == 1:
        pick = items[0]
        _LAST_BY_CHANNEL[channel_id] = pick.get("id", "")
        return pick

    for _ in range(12):
        cand = rng.choice(items)
        cid = cand.get("id", "")
        if cid and cid != last_id:
            _LAST_BY_CHANNEL[channel_id] = cid
            return cand

    cand = rng.choice(items)
    _LAST_BY_CHANNEL[channel_id] = cand.get("id", "")
    return cand

def register_history_of_the_consoles(bot: discord.Client, data_dir: str) -> None:
    # Reuse existing /console group if present
    existing = bot.tree.get_command("console")
    if isinstance(existing, app_commands.Group):
        console_group = existing
    else:
        console_group = app_commands.Group(name="console", description="Console history commands (curated).")
        try:
            bot.tree.add_command(console_group)
        except Exception as e:
            logger.warning("console group add skipped: %s", e)
            existing2 = bot.tree.get_command("console")
            console_group = existing2 if isinstance(existing2, app_commands.Group) else console_group

    @console_group.command(name="random", description="Shows a random game console from history.")
    async def random_console(interaction: discord.Interaction):
        await interaction.response.defer()  # public
        items = _load_items(data_dir)
        if not items:
            await interaction.followup.send("Console registry is empty.")
            return

        item = _pick_non_repeating(items, interaction.channel_id or 0)

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
        embed.set_footer(text=f"Curated registry • {len(items)} items • We love Kevy")
        await interaction.followup.send(embed=embed)

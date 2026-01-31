
from __future__ import annotations

import os
import re
import json
import datetime as dt
from typing import Any, List

import discord
from discord import app_commands

# --- defensive import (Railway-safe) ---
try:
    from freegames_logic import Offer, fetch_offers
except Exception:
    Offer = None
    fetch_offers = None

COLOR_FREE = 0x8EC5FF
PLATFORM_EMOJI = {
    "epic": "🟦", "gog": "🟪", "humble": "🟥", "luna": "🟧", "steam": "🟩", "other": "🎮"
}

def _load_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def _fmt_when(now_utc: dt.datetime) -> str:
    return f"UTC day: {now_utc.strftime('%Y-%m-%d')}"

def _platform_icon(platform: str) -> str:
    return PLATFORM_EMOJI.get((platform or "").lower(), PLATFORM_EMOJI["other"])

async def _build_embeds(data_dir: str) -> List[discord.Embed]:
    e = discord.Embed(title="Free games", color=COLOR_FREE)
    if not fetch_offers:
        e.description = "Free games source is temporarily unavailable."
        return [e]

    reg = _load_json(os.path.join(data_dir, "freegames_registry.json"), {})
    offers = await fetch_offers(reg, timeout_s=int(reg.get("timeout_s", 20)))

    if not offers:
        e.description = "No items found."
        return [e]

    lines = []
    for o in offers[:12]:
        icon = _platform_icon(o.platform)
        title = re.sub(r"\s+", " ", (o.title or "").strip())
        if o.url:
            lines.append(f"{icon} **{title}** — [Free]({o.url})")
        else:
            lines.append(f"{icon} **{title}** — Free")

    e.description = "\n".join(lines)
    e.set_footer(text=_fmt_when(dt.datetime.now(dt.timezone.utc)))
    return [e]

def register_free_games(client: discord.Client, tree: app_commands.CommandTree, data_dir: str) -> None:
    @tree.command(name="free", description="Show free games and deals.")
    async def free(interaction: discord.Interaction):
        await interaction.response.defer()
        embeds = await _build_embeds(data_dir)
        await interaction.followup.send(embeds=embeds)

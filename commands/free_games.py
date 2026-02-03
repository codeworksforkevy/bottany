
from __future__ import annotations
import os, json, re, datetime as dt
from typing import Any, List
import discord
from discord import app_commands

try:
    from freegames_logic import fetch_offers
except Exception:
    fetch_offers = None

COLOR_FREE = 0x8EC5FF

def _load_json(path: str, default: Any):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

async def _build(data_dir: str) -> List[discord.Embed]:
    e = discord.Embed(title="Free games", color=COLOR_FREE)
    if not fetch_offers:
        e.description = "Free games source unavailable."
        return [e]
    reg = _load_json(os.path.join(data_dir, "freegames_registry.json"), {})
    offers = await fetch_offers(reg, timeout_s=20)
    if not offers:
        e.description = "No free games right now."
        return [e]
    e.description = "\n".join(
        f"• **{re.sub(r'\s+',' ',o.title)}** — {o.url}" for o in offers[:10]
    )
    e.set_footer(text=f"UTC {dt.datetime.utcnow().date()}")
    return [e]

def register_free_games(client: discord.Client, tree: app_commands.CommandTree, data_dir: str):
    @tree.command(name="free", description="Show current free games.")
    async def free(interaction: discord.Interaction):
        await interaction.response.defer()
        embeds = await _build(data_dir)
        await interaction.followup.send(embeds=embeds)

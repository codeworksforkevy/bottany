
from __future__ import annotations

import os
import re
import json
import datetime as dt
from typing import Any, Dict, List, Optional

import discord
from discord import app_commands

from freegames_logic import Offer, fetch_offers

COLOR_FREE = 0x8EC5FF
COLOR_DISCOUNT = 0xFFB6C8
COLOR_SUBSCRIPTION = 0xD97B2B

PLATFORM_EMOJI = {
    "epic": "🟦",
    "gog": "🟪",
    "humble": "🟥",
    "luna": "🟧",
    "steam": "🟩",
    "other": "🎮",
}

KIND_LABEL = {
    "free_to_keep": "Free (keep)",
    "free": "Free",
    "discount": "Discount",
    "deal": "Discount",
    "subscription": "Subscription pick",
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

def _clean(s: str) -> str:
    s = (s or "").strip()
    return re.sub(r"\s+", " ", s)

async def _build_embeds(data_dir: str, only_free: bool) -> List[discord.Embed]:
    reg_path = os.path.join(data_dir, "freegames_registry.json")
    reg = _load_json(reg_path, {})
    timeout_s = int(reg.get("timeout_s", 20))
    offers = await fetch_offers(reg, timeout_s=timeout_s)

    if only_free:
        offers = [o for o in offers if (o.kind or "").lower() in {"free_to_keep", "free"}]

    now_utc = dt.datetime.now(dt.timezone.utc)
    e = discord.Embed(title="Free games", color=COLOR_FREE)
    if not offers:
        e.description = "No items found."
        e.set_footer(text=_fmt_when(now_utc))
        return [e]

    lines = []
    for o in offers[:12]:
        icon = _platform_icon(o.platform)
        title = _clean(o.title)
        url = (o.url or "").strip()
        label = KIND_LABEL.get((o.kind or "").lower(), o.kind or "")
        if url:
            lines.append(f"{icon} **{title}** — [{label}]({url})")
        else:
            lines.append(f"{icon} **{title}** — {label}")

    e.description = "\n".join(lines)
    e.set_footer(text=_fmt_when(now_utc))
    return [e]

def register_free_games(client: discord.Client, tree: app_commands.CommandTree, data_dir: str) -> None:
    @tree.command(name="free", description="Show free games and deals.")
    async def free(interaction: discord.Interaction):
        await interaction.response.defer()
        embeds = await _build_embeds(data_dir, only_free=False)
        await interaction.followup.send(embeds=embeds)

    @tree.command(name="freegames", description="Alias of /free.")
    async def freegames(interaction: discord.Interaction):
        await free(interaction)

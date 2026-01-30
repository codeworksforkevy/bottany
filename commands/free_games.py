# commands/free_games.py
from __future__ import annotations

import os
import re
import json
import datetime as dt
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import discord

from freegames_logic import Offer, fetch_offers


# --- Visual/UX configuration -------------------------------------------------

# Discord embed colors are integer RGB (0xRRGGBB)
COLOR_FREE = 0x8EC5FF      # baby blue
COLOR_DISCOUNT = 0xFFB6C8  # baby pink
COLOR_SUBSCRIPTION = 0xD97B2B  # burnt orange

PLATFORM_EMOJI = {
    "epic": "🟦",     # safe default (no trademarked logo)
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


def _pick_color(kind: str) -> int:
    k = (kind or "").lower()
    if k in {"free_to_keep", "free"}:
        return COLOR_FREE
    if k in {"subscription"}:
        return COLOR_SUBSCRIPTION
    return COLOR_DISCOUNT


def _fmt_when(now_utc: dt.datetime) -> str:
    # e.g. "UTC day: 2026-01-30"
    return f"UTC day: {now_utc.strftime('%Y-%m-%d')}"


def _platform_icon(platform: str) -> str:
    return PLATFORM_EMOJI.get((platform or "").lower(), PLATFORM_EMOJI["other"])


def _clean(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _chunk_offers(offers: List[Offer]) -> Dict[str, List[Offer]]:
    """
    Group offers by kind (free/discount/subscription) for nicer embeds.
    """
    buckets: Dict[str, List[Offer]] = {"free": [], "discount": [], "subscription": []}
    for o in offers:
        kind = (o.kind or "").lower()
        if kind in {"subscription"}:
            buckets["subscription"].append(o)
        elif kind in {"free_to_keep", "free"}:
            buckets["free"].append(o)
        else:
            buckets["discount"].append(o)
    return buckets


def _offers_to_lines(offers: List[Offer], limit: int = 10) -> List[str]:
    out: List[str] = []
    for o in offers[:limit]:
        icon = _platform_icon(o.platform)
        title = _clean(o.title)
        url = (o.url or "").strip()
        note = _clean(getattr(o, "note", "") or "")
        label = KIND_LABEL.get((o.kind or "").lower(), (o.kind or ""))
        if url:
            line = f"{icon} **{title}** — [{label}]({url})"
        else:
            line = f"{icon} **{title}** — {label}"
        if note:
            line += f"\n> {note}"
        out.append(line)
    if len(offers) > limit:
        out.append(f"…and {len(offers) - limit} more.")
    return out


async def _build_embeds(data_dir: str, only_free: bool) -> List[discord.Embed]:
    reg_path = os.path.join(data_dir, "freegames_registry.json")
    reg = _load_json(reg_path, {})
    timeout_s = int(reg.get("timeout_s", 20))
    offers = await fetch_offers(reg, timeout_s=timeout_s)

    if only_free:
        offers = [o for o in offers if (o.kind or "").lower() in {"free_to_keep", "free"}]

    now_utc = dt.datetime.now(dt.timezone.utc)
    buckets = _chunk_offers(offers)

    embeds: List[discord.Embed] = []
    title = "Free games & deals"
    if only_free:
        title = "Free-to-keep games"

    # One embed per bucket for clear color-coding
    for bucket_key, bucket_offers in buckets.items():
        if not bucket_offers:
            continue

        if bucket_key == "free":
            color = COLOR_FREE
            heading = "Free (keep)"
        elif bucket_key == "subscription":
            color = COLOR_SUBSCRIPTION
            heading = "Subscription picks"
        else:
            color = COLOR_DISCOUNT
            heading = "Discounts & deals"

        e = discord.Embed(
            title=title,
            description=f"**{heading}**",
            color=color,
        )
        lines = _offers_to_lines(bucket_offers, limit=12)
        e.add_field(name="Items", value="\n\n".join(lines) if lines else "—", inline=False)
        e.set_footer(text=f"{_fmt_when(now_utc)} • Count: {len(bucket_offers)}")
        embeds.append(e)

    if not embeds:
        e = discord.Embed(
            title=title,
            description="No items found right now.",
            color=COLOR_DISCOUNT,
        )
        e.set_footer(text=_fmt_when(now_utc))
        embeds.append(e)

    return embeds


def register_free_games(client: discord.Client, tree: discord.app_commands.CommandTree, data_dir: str) -> None:
    """
    Register /freegames and /freegames_onlyfree.
    Uses the app command tree directly (no cogs) so it works with discord.Client.
    """

    @tree.command(name="freegames", description="Show free-to-keep games, discounts, and subscription picks.")
    async def freegames(interaction: discord.Interaction, only_free: Optional[bool] = False):
        await interaction.response.defer(thinking=False)
        embeds = await _build_embeds(data_dir=data_dir, only_free=bool(only_free))
        # Avoid hitting embed limits: send first, then follow-ups
        await interaction.followup.send(embeds=embeds[:1], ephemeral=False)
        for e in embeds[1:]:
            await interaction.followup.send(embed=e, ephemeral=False)

    @tree.command(name="freegames_onlyfree", description="Show only 100% free-to-keep games.")
    async def freegames_onlyfree(interaction: discord.Interaction):
        await interaction.response.defer(thinking=False)
        embeds = await _build_embeds(data_dir=data_dir, only_free=True)
        await interaction.followup.send(embeds=embeds[:1], ephemeral=False)
        for e in embeds[1:]:
            await interaction.followup.send(embed=e, ephemeral=False)

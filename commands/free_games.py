from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from _utils import load_json

# Unified registry file name (keep ONLY this one going forward)
REGISTRY_PATH = "data/freegames_registry.json"

# Shared aggregation logic
from freegames_logic import Offer, fetch_all_offers  # type: ignore

BABY_BLUE = 9031664


def _utc_day_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _group_offers(offers: List[Offer]) -> Dict[str, List[Offer]]:
    groups: Dict[str, List[Offer]] = {}
    for o in offers:
        groups.setdefault(o.platform, []).append(o)
    return groups


def _platform_label(p: str) -> str:
    return {
        "epic": "Epic Games Store",
        "gog": "GOG",
        "humble": "Humble Bundle",
        "luna": "Amazon Luna",
    }.get(p, p)


def _kind_label(kind: str) -> str:
    return {
        "free_to_keep": "Free to keep",
        "giveaway": "Giveaway",
        "deal": "Deal",
        "subscription": "Subscription picks",
    }.get(kind, kind)


def _render_offer(o: Offer) -> str:
    note = f" — {o.note}" if getattr(o, "note", "") else ""
    return f"• [{o.title}]({o.url}) ({_kind_label(o.kind)}){note}"


def _build_embed(offers: List[Offer]) -> discord.Embed:
    title = "Free games & selected deals"
    subtitle = "Official entry points for free-to-keep games, giveaways, and subscription picks from trusted platforms."
    emb = discord.Embed(title=title, description=subtitle, color=BABY_BLUE)

    groups = _group_offers(offers)
    for platform in ["epic", "gog", "humble", "luna"]:
        items = groups.get(platform, [])
        if not items:
            continue
        lines = [_render_offer(o) for o in items[:10]]
        if len(items) > 10:
            lines.append(f"…and {len(items)-10} more")
        emb.add_field(name=_platform_label(platform), value="\n".join(lines), inline=False)

    emb.set_footer(text=f"UTC day: {_utc_day_str()} • Items: {len(offers)}")
    return emb


class FreeGamesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.registry = load_json(REGISTRY_PATH, {})

    async def _fetch_offers(self) -> List[Offer]:
        async with aiohttp.ClientSession() as session:
            return await fetch_all_offers(session, self.registry)

    @app_commands.command(
        name="freegames",
        description="Show current free games and selected deals (Epic, GOG, Humble, Luna).",
    )
    async def freegames(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        try:
            offers = await self._fetch_offers()
        except Exception as e:
            await interaction.followup.send(f"Unable to fetch offers: {e}", ephemeral=True)
            return

        if not offers:
            await interaction.followup.send("No offers found right now.", ephemeral=True)
            return

        await interaction.followup.send(embed=_build_embed(offers))


async def setup(bot: commands.Bot):
    await bot.add_cog(FreeGamesCog(bot))

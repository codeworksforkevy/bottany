
from __future__ import annotations

import os
import json
import datetime as dt

import discord
from discord.ext import tasks
from discord import app_commands

from freegames_logic import gather_offers

GLOBAL_STATE_FILE = "data/freegames_global_state.json"
RATE_GUARD_SECONDS = 30

PLATFORM_COLORS = {
    "epic": 0x2F3136,
    "gog": 0x86328A,
    "humble": 0xCC2929,
    "luna": 0x00A8E1,
}


def _load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)


def _build_embed(offer):
    color = PLATFORM_COLORS.get(offer.platform.lower(), 0xA7D8FF)
    embed = discord.Embed(
        title=offer.title,
        url=offer.url,
        color=color,
        timestamp=dt.datetime.utcnow()
    )
    embed.add_field(name="Status", value="FREE TO KEEP", inline=False)
    embed.add_field(name="Platform", value=offer.platform.upper(), inline=False)

    if getattr(offer, "thumbnail", None):
        embed.set_thumbnail(url=offer.thumbnail)

    return embed


class FreeGamesEnterprise:

    def __init__(self, bot: discord.Client, registry_path: str):
        self.bot = bot
        self.registry_path = registry_path
        self.last_rate_push = 0
        self.loop.start()

    @tasks.loop(minutes=15)
    async def loop(self):

        offers = await gather_offers(self.registry_path)
        now_ts = dt.datetime.utcnow().timestamp()

        if now_ts - self.last_rate_push < RATE_GUARD_SECONDS:
            return

        state = _load_json(GLOBAL_STATE_FILE, {})
        old_titles = set(state.get("titles", []))

        new_offers = [o for o in offers if o.title not in old_titles]

        if not new_offers:
            return

        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    for offer in new_offers:
                        embed = _build_embed(offer)
                        await channel.send(embed=embed)
                    break

        _save_json(GLOBAL_STATE_FILE, {
            "titles": [o.title for o in offers]
        })

        self.last_rate_push = now_ts


def register_freegames_admin(tree: app_commands.CommandTree, enterprise: FreeGamesEnterprise):

    @tree.command(name="freegames_monitor", description="Show freegames metrics.")
    async def monitor(interaction: discord.Interaction):
        state = _load_json(GLOBAL_STATE_FILE, {})
        embed = discord.Embed(title="FreeGames Metrics", color=0x00FFAA)
        embed.add_field(name="Tracked Offers", value=str(len(state.get("titles", []))), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

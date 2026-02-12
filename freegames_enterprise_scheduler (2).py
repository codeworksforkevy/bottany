# Updated FreeGames Enterprise Scheduler (Enterprise-Ready Version)
# Includes:
# - Platform-specific slash commands
# - Duplicate detection per platform
# - Embed formatting layer separation
# - Improved scheduling flexibility

from __future__ import annotations

import os
import json
import hashlib
import datetime as dt

import discord
from discord.ext import tasks
from discord import app_commands

from freegames_logic import gather_offers

STATE_DIR = "data/freegames_state"
CONFIG_FILE = "data/freegames_channels.json"

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


def _offers_hash(offers):
    raw = "|".join(sorted(f"{o.platform}-{o.title}-{o.url}" for o in offers))
    return hashlib.sha256(raw.encode()).hexdigest()


def _format_countdown(expires_at):
    if not expires_at:
        return "Unknown"

    now = dt.datetime.now(dt.timezone.utc)
    delta = expires_at - now

    if delta.total_seconds() <= 0:
        return "Expired"

    days = delta.days
    hours = delta.seconds // 3600
    return f"{days}d {hours}h remaining"


def _build_embed(offer):
    color = PLATFORM_COLORS.get(offer.platform.lower(), 0xA7D8FF)

    embed = discord.Embed(
        title=offer.title,
        url=offer.url,
        color=color,
        timestamp=dt.datetime.now(dt.timezone.utc)
    )

    embed.add_field(name="Status", value="FREE TO KEEP", inline=False)

    if offer.expires_at:
        embed.add_field(
            name="Claim Before",
            value=offer.expires_at.strftime("%Y-%m-%d %H:%M UTC"),
            inline=True
        )
        embed.add_field(
            name="Countdown",
            value=_format_countdown(offer.expires_at),
            inline=True
        )

    embed.add_field(name="Platform", value=offer.platform.upper(), inline=False)

    if getattr(offer, "thumbnail", None):
        embed.set_thumbnail(url=offer.thumbnail)

    embed.set_footer(text="Bottany • Free Games Monitor")

    view = discord.ui.View()
    button = discord.ui.Button(
        label="Claim Now",
        style=discord.ButtonStyle.link,
        url=offer.url
    )
    view.add_item(button)

    return embed, view


class FreeGamesEnterprise:

    def __init__(self, bot: discord.Client, registry_path: str):
        self.bot = bot
        self.registry_path = registry_path
        self.loop.start()

    @tasks.loop(minutes=30)
    async def loop(self):
        now = dt.datetime.utcnow()
        if now.weekday() != 3 or now.hour != 18:
            return

        await self._post_updates(force=False)

    async def _post_updates(self, force: bool = False, guild_id: int | None = None, platform: str | None = None):

        configs = _load_json(CONFIG_FILE, {})
        offers = await gather_offers(self.registry_path)

        if platform:
            offers = [o for o in offers if o.platform.lower() == platform.lower()]

        if not offers:
            return

        new_hash = _offers_hash(offers)

        for g_id, channel_id in configs.items():

            if guild_id and int(g_id) != guild_id:
                continue

            state_path = os.path.join(STATE_DIR, f"{g_id}_{platform or 'all'}.json")
            state = _load_json(state_path, {})

            if not force and state.get("hash") == new_hash:
                continue

            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                continue

            for offer in offers:
                embed, view = _build_embed(offer)
                await channel.send(embed=embed, view=view)

            _save_json(state_path, {"hash": new_hash})

    @loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()


def register_freegames_admin(tree: app_commands.CommandTree, enterprise: FreeGamesEnterprise):

    @tree.command(name="freegames_channel", description="Set free games channel for this server.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel):
        configs = _load_json(CONFIG_FILE, {})
        configs[str(interaction.guild_id)] = channel.id
        _save_json(CONFIG_FILE, configs)
        await interaction.response.send_message(
            f"Free games channel set to {channel.mention}",
            ephemeral=True
        )

    @tree.command(name="freegames_force", description="Force post free games update now (admin only).")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def force_post(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await enterprise._post_updates(force=True, guild_id=interaction.guild_id)
        await interaction.followup.send("Free games update forced.", ephemeral=True)

    for platform in ["epic", "gog", "humble", "luna"]:

        @tree.command(name=f"freegames_{platform}", description=f"Show current {platform.capitalize()} free games.")
        async def platform_command(interaction: discord.Interaction, _platform=platform):
            await interaction.response.defer()
            offers = await gather_offers(enterprise.registry_path)
            offers = [o for o in offers if o.platform.lower() == _platform]

            if not offers:
                await interaction.followup.send(f"No active {_platform.capitalize()} free games found.")
                return

            for offer in offers:
                embed, view = _build_embed(offer)
                await interaction.followup.send(embed=embed, view=view)


from __future__ import annotations

import os
import json
import hashlib
import datetime as dt
from typing import Dict

import discord
from discord.ext import tasks
from discord import app_commands

from freegames_logic import gather_offers, build_kind_embeds

STATE_DIR = "data/freegames_state"
CONFIG_FILE = "data/freegames_channels.json"

TARGET_WEEKDAY = 3      # Thursday
TARGET_HOUR_UTC = 18    # 18:00 UTC
CHECK_INTERVAL_MIN = 30


def _load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default


def _save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)


def _offers_hash(offers):
    raw = "|".join(sorted(f"{o.platform}-{o.title}-{o.url}" for o in offers))
    return hashlib.sha256(raw.encode()).hexdigest()


class FreeGamesEnterprise:

    def __init__(self, bot: discord.Client, registry_path: str):
        self.bot = bot
        self.registry_path = registry_path
        self.loop.start()

    @tasks.loop(minutes=CHECK_INTERVAL_MIN)
    async def loop(self):
        now = dt.datetime.utcnow()
        if now.weekday() != TARGET_WEEKDAY or now.hour != TARGET_HOUR_UTC:
            return

        await self._post_updates(force=False)

    async def _post_updates(self, force: bool = False, guild_id: int | None = None):

        configs = _load_json(CONFIG_FILE, {})
        offers = await gather_offers(self.registry_path)
        if not offers:
            return

        new_hash = _offers_hash(offers)

        for g_id, channel_id in configs.items():

            if guild_id and int(g_id) != guild_id:
                continue

            state_path = os.path.join(STATE_DIR, f"{g_id}.json")
            state = _load_json(state_path, {})

            if not force and state.get("hash") == new_hash:
                continue

            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                continue

            embeds = build_kind_embeds(offers, title_prefix="Free Games Update")
            await channel.send(embeds=embeds)

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

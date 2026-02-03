
from __future__ import annotations
import datetime as dt
import discord
from discord import app_commands
from discord.ext import tasks

LAST_POST_AT: dt.datetime | None = None
TARGET_CHANNEL_NAME = "gaming"

async def _post_weekly(client: discord.Client):
    global LAST_POST_AT
    for g in client.guilds:
        ch = discord.utils.get(g.text_channels, name=TARGET_CHANNEL_NAME)
        if not ch:
            continue
        await ch.send("🎮 **Weekly Free Games Digest**\n(automated post)")
        LAST_POST_AT = dt.datetime.utcnow()

def register_weekly(client: discord.Client, tree: app_commands.CommandTree, *_):
    @tree.command(name="weekly_status", description="Show last weekly post time.")
    async def weekly_status(interaction: discord.Interaction):
        if LAST_POST_AT:
            await interaction.response.send_message(f"Last weekly post: {LAST_POST_AT} UTC", ephemeral=True)
        else:
            await interaction.response.send_message("Weekly post has not run yet.", ephemeral=True)

    @tree.command(name="weekly_force", description="Force weekly post now.")
    async def weekly_force(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await _post_weekly(interaction.client)
        await interaction.followup.send("Weekly post sent.", ephemeral=True)

    @tasks.loop(hours=168)
    async def weekly_loop():
        await _post_weekly(client)

    weekly_loop.start()

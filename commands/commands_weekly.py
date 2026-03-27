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

async def register(bot: discord.Client, data_dir: str) -> None:
    """Register weekly commands. Delegates to weekly_digest if available."""

    # Prefer the richer weekly_digest implementation if it exists alongside this file
    try:
        from weekly_digest import register as _wd_register
        await _wd_register(bot, data_dir)
        return
    except ImportError:
        pass  # weekly_digest not available — fall through to built-in stub

    # Guard against double-registration on reconnect
    if bot.tree.get_command("weekly_status"):
        return

    @bot.tree.command(name="weekly_status", description="Show last weekly post time.")
    async def weekly_status(interaction: discord.Interaction):
        if LAST_POST_AT:
            await interaction.response.send_message(
                f"Last weekly post: {LAST_POST_AT} UTC", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "Weekly post has not run yet.", ephemeral=True
            )

    @bot.tree.command(name="weekly_force", description="Force weekly post now.")
    async def weekly_force(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await _post_weekly(interaction.client)
        await interaction.followup.send("Weekly post sent.", ephemeral=True)

    # Guard: only start the loop once — tasks.loop crashes if started twice
    if getattr(bot, "_weekly_loop_started", False):
        return

    @tasks.loop(hours=168)
    async def weekly_loop():
        await _post_weekly(bot)

    @weekly_loop.before_loop
    async def _before_weekly():
        await bot.wait_until_ready()

    bot._weekly_loop_started = True
    weekly_loop.start()

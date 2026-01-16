from __future__ import annotations

import os
import discord
from discord import app_commands


def _parse_admin_ids() -> set[int]:
    raw = os.getenv("ADMIN_USER_IDS", "").strip()
    if not raw:
        return set()
    ids: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.add(int(part))
        except Exception:
            continue
    return ids


def _is_admin(user_id: int) -> bool:
    ids = _parse_admin_ids()
    # If not configured, allow nobody (safer default).
    if not ids:
        return False
    return user_id in ids


def register_admin_sync(bot: discord.Client) -> None:
    """Registers /admin sync commands.

    Environment variables:
      - ADMIN_USER_IDS: comma-separated Discord user IDs allowed to run admin sync commands.
      - DEV_GUILD_ID: the development guild ID for fast sync.

    Notes:
      - These commands are intended for development only.
      - Discord global command propagation can take time.
    """

    admin = app_commands.Group(name="admin", description="Admin tools.")

    @admin.command(name="sync_dev", description="Sync commands to the DEV guild only.")
    async def sync_dev(interaction: discord.Interaction):
        if not _is_admin(interaction.user.id):
            await interaction.response.send_message("Not authorized.", ephemeral=True)
            return

        dev_id = os.getenv("DEV_GUILD_ID", "").strip()
        if not dev_id:
            await interaction.response.send_message("DEV_GUILD_ID is not set.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        try:
            guild = discord.Object(id=int(dev_id))
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            await interaction.followup.send(f"Synced {len(synced)} command(s) to DEV guild {dev_id}.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"DEV guild sync failed: {e}", ephemeral=True)

    @admin.command(name="sync_global", description="Sync commands globally (slow propagation).")
    async def sync_global(interaction: discord.Interaction):
        if not _is_admin(interaction.user.id):
            await interaction.response.send_message("Not authorized.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        try:
            synced = await bot.tree.sync()
            await interaction.followup.send(f"Requested global sync for {len(synced)} command(s).", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Global sync failed: {e}", ephemeral=True)

    bot.tree.add_command(admin)


import os
import discord
from discord import app_commands
from services.twitch_eventsub_manager import subscribe_stream_online

OWNER_ID = int(os.getenv("BOT_OWNER_ID", "0"))
CHANNEL_ID = 1446562626695074006

def register(bot):

    group = app_commands.Group(name="twitch", description="Twitch Watch System")

    @group.command(name="add", description="Owner: add streamer")
    async def add(interaction: discord.Interaction, user_id: str):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("Owner only.", ephemeral=True)
            return

        await subscribe_stream_online(user_id)
        await interaction.response.send_message("Subscription created.", ephemeral=True)

    bot.tree.add_command(group)

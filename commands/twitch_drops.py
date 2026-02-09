
import discord
from discord import app_commands

def register_twitch_drops(client, tree, data_dir):
    group = app_commands.Group(name="twitch", description="Twitch related commands")

    @group.command(name="drops", description="Show current Twitch Drops")
    async def drops(interaction: discord.Interaction):
        await interaction.response.send_message(
            "🎁 Twitch Drops module is active.",
            ephemeral=True
        )

    tree.add_command(group)

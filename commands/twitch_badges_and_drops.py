from discord import app_commands
import discord

async def register_twitch_badges_and_drops(client):
    # reuse existing /twitch group if present
    group = next((c for c in client.tree.get_commands() if c.name == "twitch"), None)
    if group is None:
        group = app_commands.Group(name="twitch", description="Twitch tools")
        client.tree.add_command(group)

    @group.command(name="drops", description="Current Twitch drops")
    async def drops(interaction: discord.Interaction):
        await interaction.response.send_message("Twitch drops info coming soon.")

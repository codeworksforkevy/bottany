import discord
from discord import app_commands
from services.color_service import random_color, generate_palette
from services.stats_service import log_command

def register(bot):

    @bot.tree.command(name="random_color", description="Generate random color")
    async def random_color_cmd(interaction: discord.Interaction):
        r, g, b = random_color()
        log_command("random_color", interaction.user.id)
        await interaction.response.send_message(f"RGB({r}, {g}, {b})")

    @bot.tree.command(name="palette", description="Generate color palette")
    async def palette_cmd(interaction: discord.Interaction):
        palette = generate_palette()
        log_command("palette", interaction.user.id)
        text = "\n".join([f"RGB{c}" for c in palette])
        await interaction.response.send_message(text)
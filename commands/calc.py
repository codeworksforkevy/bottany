import discord
from discord import app_commands
from services.math_service import safe_eval
from services.stats_service import log_command

def register(bot):

    @bot.tree.command(name="calc", description="Scientific calculator")
    async def calc(interaction: discord.Interaction, expression: str):
        try:
            result = safe_eval(expression)
            log_command("calc", interaction.user.id)
            await interaction.response.send_message(f"Result: {result}")
        except Exception as e:
            await interaction.response.send_message(f"Error: {e}", ephemeral=True)
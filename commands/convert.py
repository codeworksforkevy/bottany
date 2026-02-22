
import discord
from discord import app_commands
from services.convert_service import convert_units, list_units
from services.stats_service import log_command

def register(bot):

    @bot.tree.command(name="convert", description="Advanced scientific unit converter")
    async def convert(interaction: discord.Interaction, value: float, from_unit: str, to_unit: str):
        try:
            result = convert_units(value, from_unit, to_unit)
            log_command("convert", interaction.user.id)
            await interaction.response.send_message(f"{value} {from_unit} = {result}")
        except Exception as e:
            await interaction.response.send_message(f"Error: {e}", ephemeral=True)

    @convert.autocomplete("from_unit")
    async def from_unit_autocomplete(interaction: discord.Interaction, current: str):
        units = list_units()
        return [
            app_commands.Choice(name=u, value=u)
            for u in units if current.lower() in u.lower()
        ][:25]

    @convert.autocomplete("to_unit")
    async def to_unit_autocomplete(interaction: discord.Interaction, current: str):
        units = list_units()
        return [
            app_commands.Choice(name=u, value=u)
            for u in units if current.lower() in u.lower()
        ][:25]

    @bot.tree.command(name="convert_list", description="List available units")
    async def convert_list(interaction: discord.Interaction):
        units = list_units()
        log_command("convert_list", interaction.user.id)
        preview = "\n".join(units[:50])
        await interaction.response.send_message(f"First 50 units:\n{preview}")

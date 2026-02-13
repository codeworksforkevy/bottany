import discord
from discord import app_commands

class Belgium(app_commands.Group):
    def __init__(self):
        super().__init__(name="belgium", description="Belgium related commands")

    @app_commands.command(name="beverages")
    async def beverages(self, interaction: discord.Interaction):
        await interaction.response.send_message("Belgian beverages")

    @app_commands.command(name="chocolate")
    async def chocolate(self, interaction: discord.Interaction):
        await interaction.response.send_message("Belgian chocolate")

def register_belgium(client, tree, data_dir):
    tree.add_command(Belgium())

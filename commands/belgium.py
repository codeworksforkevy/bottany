import discord
from discord import app_commands


class Belgium(app_commands.Group):
    def __init__(self):
        super().__init__(
            name="belgium",
            description="Belgium related commands"
        )


async def register(bot, data_dir):

    # Eğer zaten ekliyse tekrar ekleme
    existing = bot.tree.get_command("belgium")
    if existing:
        return

    bot.tree.add_command(Belgium())


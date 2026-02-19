import discord
from discord import app_commands


class Belgium(app_commands.Group):
    def __init__(self):
        super().__init__(
            name="belgium",
            description="Belgium related commands"
        )


# Hybrid loader compatible
def register(bot, data_dir):

    existing = bot.tree.get_command("belgium")

    # Eğer zaten Belgium group ise tekrar ekleme
    if isinstance(existing, app_commands.Group):
        return

    # Eğer aynı isimde ama farklı tipte command varsa hata ver
    if existing:
        raise RuntimeError(
            "Command name collision: 'belgium' already exists and is not a Group."
        )

    bot.tree.add_command(Belgium())


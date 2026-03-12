from io import BytesIO
import discord
from discord import app_commands

from services.pixel_weather_engine_v10 import PixelWeatherEngineV10

def register(bot):

    group = app_commands.Group(
        name="makeitrain",
        description="Pixel Weather Engine v10"
    )

    @group.command(name="world")

    async def world(interaction: discord.Interaction):

        await interaction.response.defer()

        engine=PixelWeatherEngineV10()

        frames=[]

        for _ in range(120):

            engine.update()

            frames.append(engine.render())

        buffer=BytesIO()

        frames[0].save(
            buffer,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=16,
            loop=0
        )

        buffer.seek(0)

        await interaction.followup.send(
            file=discord.File(buffer,"pixel_world_v10.gif")
        )

    bot.tree.add_command(group)

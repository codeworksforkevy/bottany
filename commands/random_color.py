import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image
import io
import random

class Color(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="random_color",
        description="Generate one or multiple random colors (max 5)"
    )
    @app_commands.describe(
        count="How many colors to generate (1–5)"
    )
    async def random_color(
        self, interaction: discord.Interaction, count: int = 1
    ):
        # Clamp count
        if count < 1:
            count = 1
        elif count > 5:
            count = 5

        embeds = []
        files = []

        for i in range(count):
            # Generate a random 24-bit RGB color
            r = random.randint(0, 255)
            g = random.randint(0, 255)
            b = random.randint(0, 255)
            color = discord.Color.from_rgb(r, g, b)
            hex_code = f"#{r:02X}{g:02X}{b:02X}"

            # Create thumbnail image
            size = (128, 128)
            img = Image.new("RGB", size, (r, g, b))
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            filename = f"color_{i}.png"
            files.append(discord.File(buffer, filename=filename))

            # Embed
            embed = discord.Embed(
                title=f"Random Color {i+1}",
                description=f"Hex: `{hex_code}`",
                color=color
            )
            embed.set_thumbnail(url=f"attachment://{filename}")
            embed.set_footer(text="Sources: Discord Color Standard + W3C CSS Color Module Level 4")

            embeds.append(embed)

        # Send response
        if count == 1:
            await interaction.response.send_message(embed=embeds[0], file=files[0])
        else:
            # Multiple colors: send first embed with all files
            await interaction.response.send_message(embeds=embeds, files=files)

async def setup(bot):
    await bot.add_cog(Color(bot))

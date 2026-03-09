import discord
from discord import app_commands
from services.color_service import random_color, generate_palette
from services.stats_service import log_command
from io import BytesIO
from PIL import Image, ImageDraw

def rgb_to_hex(r, g, b):
    return f"#{r:02X}{g:02X}{b:02X}"

def create_palette_image(colors, block_size=100):
    width = block_size * len(colors)
    height = block_size
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    for i, (r, g, b) in enumerate(colors):
        draw.rectangle([i*block_size, 0, (i+1)*block_size, height], fill=(r, g, b))
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

def register(bot):

    @bot.tree.command(name="random_color", description="Generate a random color with preview")
    async def random_color_cmd(interaction: discord.Interaction):
        r, g, b = random_color()
        hex_color = rgb_to_hex(r, g, b)
        log_command("random_color", interaction.user.id)

        embed = discord.Embed(
            title="Random Color Generated",
            description=f"RGB: ({r}, {g}, {b})\nHex: {hex_color}",
            color=discord.Color.from_rgb(r, g, b)
        )
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="palette", description="Generate a color palette with preview")
    @app_commands.describe(size="Number of colors in the palette (default 5)")
    async def palette_cmd(interaction: discord.Interaction, size: int = 5):
        palette = generate_palette(size)
        log_command("palette", interaction.user.id)

        # Embed
        embed = discord.Embed(title=f"Color Palette ({size} colors)")

        # Her renk için RGB ve Hex bilgisi
        for idx, (r, g, b) in enumerate(palette, 1):
            hex_color = rgb_to_hex(r, g, b)
            embed.add_field(
                name=f"Color {idx}",
                value=f"RGB: ({r}, {g}, {b})\nHex: {hex_color}",
                inline=True
            )

        # Görsel palet oluştur
        img_buffer = create_palette_image(palette)
        file = discord.File(fp=img_buffer, filename="palette.png")
        embed.set_image(url="attachment://palette.png")

        await interaction.response.send_message(embed=embed, file=file)

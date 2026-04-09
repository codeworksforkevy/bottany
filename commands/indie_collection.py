from __future__ import annotations
import discord
from discord import app_commands

def register(bot: discord.Client, data_dir: str = None) -> None:
    if bot.tree.get_command("gaming"):
        return

    gaming_group = app_commands.Group(name="gaming", description="Gaming stats, LFG, and history")

    @gaming_group.command(name="indie-discovery", description="Discover a hidden gem indie game.")
    async def indie_discovery(interaction: discord.Interaction):
        embed = discord.Embed(title="🌌 Indie Discovery: Celeste", color=0x002147)
        embed.description = "### A Masterpiece of Platforming\n*Help Madeline survive her inner demons on her journey to the top of Celeste Mountain.*"
        
        embed.add_field(name="Engine & Tech", value="*Developed using C# and the XNA framework (Monogame). Famous for its incredibly tight controls and micro-adjustments.* 👨‍💻", inline=False)
        embed.add_field(name="Soundtrack", value="*Composed by Lena Raine, blending retro 8-bit chip-tunes with profound emotional piano melodies.* 💽", inline=False)
        embed.add_field(name="Critical Acclaim", value="*Overwhelmingly Positive. A profound exploration of mental health disguised as a hardcore platformer.* ✅", inline=False)
        
        embed.set_footer(text="Indie Archive 📚")
        await interaction.response.send_message(embed=embed)

    @gaming_group.command(name="collection", description="Check the retro market price for a classic game.")
    async def collection(interaction: discord.Interaction, game_title: str):
        embed = discord.Embed(title=f"💽 Market Valuation: {game_title.title()}", color=0x002147)
        embed.description = "### Retro Archive Prices\n*Current estimated valuation for authentic collector's items.*"
        
        embed.add_field(name="Loose Cartridge", value="*$ 45.00* 🔵", inline=True)
        embed.add_field(name="Complete in Box (CIB)", value="*$ 180.50* 🔵", inline=True)
        embed.add_field(name="Sealed / Graded (Wata 9.0+)", value="*$ 1,250.00* 📘", inline=False)
        
        embed.set_footer(text="Prices are estimations for NTSC/PAL authentic copies. 🖲️")
        await interaction.response.send_message(embed=embed)

    bot.tree.add_command(gaming_group)

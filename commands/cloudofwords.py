from __future__ import annotations
import discord
from discord import app_commands
from collections import Counter

def register(bot, data_dir=None):
    if bot.tree.get_command("cloudofwords"):
        return

    cloud_group = app_commands.Group(name="cloudofwords", description="Linguistic analytics and word clouds")

    @cloud_group.command(name="generate", description="Generate a word cloud from recent messages.")
    async def generate(interaction: discord.Interaction, limit: int = 100):
        await interaction.response.defer()
        
        words = []
        async for message in interaction.channel.history(limit=limit):
            if not message.author.bot:
                words.extend(message.content.lower().split())
        
        if not words:
            await interaction.followup.send("*Not enough data to create a word cloud.* ☁️", ephemeral=True)
            return

        top_words = Counter(words).most_common(5)
        
        embed = discord.Embed(title="☁️ Word Cloud Data", color=0x87CEFA)
        embed.description = "### Linguistic Analysis\n*Top words used recently in this channel:*"
        for word, count in top_words:
            if len(word) > 2:
                embed.add_field(name=word, value=f"*{count} times*", inline=True)
        
        await interaction.followup.send(embed=embed)

    bot.tree.add_command(cloud_group)

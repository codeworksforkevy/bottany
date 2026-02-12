from __future__ import annotations

import discord
from discord import app_commands

from academic_trivia_loader import random_trivia


def register_trivia(tree: app_commands.CommandTree):

    @tree.command(name="trivia", description="Get an academic trivia statement.")
    async def trivia(interaction: discord.Interaction):

        entry = random_trivia()

        if not entry:
            await interaction.response.send_message(
                "Trivia database is empty.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="Academic Trivia",
            description=entry["text"],
            color=0x3498DB
        )

        if entry.get("field"):
            embed.add_field(
                name="Field",
                value=entry["field"],
                inline=True
            )

        await interaction.response.send_message(embed=embed)


from __future__ import annotations

import json
import os
import discord
from discord import app_commands

DATA_FILE = "data/awards_registry.json"


def _load():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def register_awards(tree: app_commands.CommandTree):

    @tree.command(name="awards", description="Show registered game awards.")
    async def awards(interaction: discord.Interaction):

        data = _load()
        if not data:
            await interaction.response.send_message(
                "No awards data available.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="Game Awards Registry",
            color=0xF1C40F
        )

        for name, info in data.items():
            embed.add_field(
                name=name,
                value=info.get("description", "No description"),
                inline=False
            )

        await interaction.response.send_message(embed=embed)

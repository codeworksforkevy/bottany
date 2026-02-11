
from __future__ import annotations

import json
import os
import discord
from discord import app_commands

DATA_FILE = "data/awards_registry_v2.json"


def _load():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def register_awards(tree: app_commands.CommandTree):

    @tree.command(name="awards", description="Query major game award winners.")
    @app_commands.describe(
        year="Filter by year (e.g. 2022)",
        award="Filter by award id (tga, bafta, dice, gja)",
        game="Filter by game title"
    )
    async def awards(
        interaction: discord.Interaction,
        year: int | None = None,
        award: str | None = None,
        game: str | None = None
    ):

        data = _load()
        if not data:
            await interaction.response.send_message("Awards registry missing.", ephemeral=True)
            return

        results = data.get("winners", [])

        if year:
            results = [r for r in results if r["year"] == year]

        if award:
            results = [r for r in results if r["award_id"].lower() == award.lower()]

        if game:
            results = [r for r in results if game.lower() in r["winner"].lower()]

        if not results:
            await interaction.response.send_message("No results found.", ephemeral=True)
            return

        embed = discord.Embed(title="Awards Results", color=0xF1C40F)

        for r in sorted(results, key=lambda x: (x["year"], x["award_id"])):
            embed.add_field(
                name=f'{r["year"]} — {r["award_id"].upper()}',
                value=f'{r["category"]}: {r["winner"]}',
                inline=False
            )

        await interaction.response.send_message(embed=embed)

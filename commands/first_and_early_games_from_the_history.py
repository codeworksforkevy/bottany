from __future__ import annotations

import os
import json
import discord
from discord import app_commands

REG_FILE = "first_games_registry.json"

def _load_items(data_dir: str) -> list[dict]:
    path = os.path.join(data_dir, REG_FILE)
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    items = obj.get("items", [])
    return items if isinstance(items, list) else []

def register_first_and_early_games_from_the_history(bot: discord.Client, data_dir: str) -> None:
    """Registers /games first100 and /games by_year"""
    games = app_commands.Group(name="games", description="First and early commercially released games (curated).")

    @games.command(name="first100", description="Lists up to the first 100 commercially released games (curated).")
    async def first100(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        items = _load_items(data_dir)
        if not items:
            await interaction.followup.send("First-games registry is empty.", ephemeral=True)
            return

        items = sorted(items, key=lambda x: (x.get("release_year", 9999), x.get("title", "")))
        top = items[:100]

        lines = []
        for i, g in enumerate(top, start=1):
            y = g.get("release_year", "—")
            t = g.get("title", "Untitled")
            plat = g.get("platform", "")
            tail = f" — {plat}" if plat else ""
            lines.append(f"{i}. **{t}** ({y}){tail}")

        text = "\n".join(lines)
        if len(text) > 3900:
            text = text[:3900] + "\n…"

        embed = discord.Embed(
            title=f"First {min(100, len(items))} commercially released games (curated)",
            description=text,
        )
        embed.set_footer(text="Curated list with references. Expand the dataset to reach 100 entries.")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @games.command(name="by_year", description="Shows early commercially released games by year (curated).")
    @app_commands.describe(year="Optional year filter (leave empty for summary).")
    async def by_year(interaction: discord.Interaction, year: int | None = None):
        await interaction.response.defer(ephemeral=True)
        items = _load_items(data_dir)
        if not items:
            await interaction.followup.send("First-games registry is empty.", ephemeral=True)
            return

        if year is None:
            counts: dict[int, int] = {}
            for g in items:
                y = g.get("release_year")
                if isinstance(y, int):
                    counts[y] = counts.get(y, 0) + 1
            years = sorted(counts.keys())
            lines = [f"**{y}**: {counts[y]} game(s)" for y in years] or ["No year data found."]

            embed = discord.Embed(
                title="First commercially released games by year (curated)",
                description="\n".join(lines)[:3900],
            )
            embed.set_footer(text="Use /games by_year <year> to list entries for a specific year.")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        filtered = [g for g in items if g.get("release_year") == year]
        filtered = sorted(filtered, key=lambda x: x.get("title", ""))

        if not filtered:
            await interaction.followup.send(f"No entries found for {year}.", ephemeral=True)
            return

        lines = []
        for g in filtered[:80]:
            t = g.get("title", "Untitled")
            plat = g.get("platform", "")
            pub = g.get("publisher", "")
            parts = [p for p in [plat, pub] if p]
            tail = " — ".join(parts)
            lines.append(f"• **{t}**" + (f" — {tail}" if tail else ""))

        embed = discord.Embed(
            title=f"Early commercially released games — {year} (curated)",
            description="\n".join(lines)[:3900],
        )
        embed.set_footer(text="Sources included per entry where available.")
        await interaction.followup.send(embed=embed, ephemeral=True)

    bot.tree.add_command(games)

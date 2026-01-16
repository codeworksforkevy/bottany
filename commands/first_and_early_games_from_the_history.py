from __future__ import annotations

import os
import json
import discord
from discord import app_commands

REG_FILE = "first_games_registry.json"
ICON_GAME = "🎮"
ICON_ARCADE = "🕹️"

def _load_items(data_dir: str) -> list[dict]:
    path = os.path.join(data_dir, REG_FILE)
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    items = obj.get("items", [])
    return items if isinstance(items, list) else []

def register_first_and_early_games_from_the_history(bot: discord.Client, data_dir: str) -> None:
    games = app_commands.Group(name="games", description="First and early commercially released games (curated).")

    @games.command(name="first100", description="Lists up to the first 100 early commercial games (curated).")
    async def first100(interaction: discord.Interaction):
        await interaction.response.defer()
        items = _load_items(data_dir)
        if not items:
            await interaction.followup.send("First-games registry is empty.")
            return

        items = sorted(items, key=lambda x: (x.get("release_year", 9999), x.get("title", "")))
        top = items[:100]

        lines = []
        for i, g in enumerate(top, start=1):
            y = g.get("release_year", "—")
            t = g.get("title", "Untitled")
            plat = (g.get("platform") or "").lower()
            badge = ICON_ARCADE if "arcade" in plat else ICON_GAME
            tail = f" — {g.get('platform','')}" if g.get("platform") else ""
            lines.append(f"{i}. {badge} **{t}** ({y}){tail}")

        text = "\n".join(lines)
        if len(text) > 3900:
            text = text[:3900] + "\n…"

        embed = discord.Embed(
            title=f"{ICON_GAME} First {min(100, len(items))} early commercial games (curated)",
            description=text,
        )
        embed.set_footer(text="Curated list with references. Expand dataset to reach 100 entries.")
        await interaction.followup.send(embed=embed)

    @games.command(name="by_year", description="Shows early commercial games by year (curated).")
    @app_commands.describe(year="Optional year filter (leave empty for summary).")
    async def by_year(interaction: discord.Interaction, year: int | None = None):
        await interaction.response.defer()
        items = _load_items(data_dir)
        if not items:
            await interaction.followup.send("First-games registry is empty.")
            return

        if year is None:
            counts: dict[int, int] = {}
            for g in items:
                y = g.get("release_year")
                if isinstance(y, int):
                    counts[y] = counts.get(y, 0) + 1
            years = sorted(counts.keys())
            lines = [f"• **{y}**: {counts[y]} game(s)" for y in years] or ["No year data found."]

            embed = discord.Embed(
                title="🗓️ Early games by year (curated)",
                description="\n".join(lines)[:3900],
            )
            embed.set_footer(text="Use /games by_year <year> to list entries for a specific year.")
            await interaction.followup.send(embed=embed)
            return

        filtered = [g for g in items if g.get("release_year") == year]
        filtered = sorted(filtered, key=lambda x: x.get("title", ""))

        if not filtered:
            await interaction.followup.send(f"No entries found for {year}.")
            return

        lines = []
        for g in filtered[:80]:
            t = g.get("title", "Untitled")
            plat = (g.get("platform") or "").lower()
            badge = ICON_ARCADE if "arcade" in plat else ICON_GAME
            pub = g.get("publisher", "")
            parts = [p for p in [g.get("platform", ""), pub] if p]
            tail = " — ".join(parts)
            lines.append(f"• {badge} **{t}**" + (f" — {tail}" if tail else ""))

        embed = discord.Embed(
            title=f"🗓️ Early games — {year} (curated)",
            description="\n".join(lines)[:3900],
        )
        embed.set_footer(text="Sources included per entry where available.")
        await interaction.followup.send(embed=embed)

    bot.tree.add_command(games)

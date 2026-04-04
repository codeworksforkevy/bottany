# first_and_early_games_from_the_history.py
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

import discord
from discord import app_commands

log = logging.getLogger(__name__)

REG_FILE = "first_games_registry.json"


# ── Loader ────────────────────────────────────────────────────────────────────

def _load(data_dir: str) -> List[Dict[str, Any]]:
    path = os.path.join(data_dir, REG_FILE)
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        # JSON uses "games" key (not "items")
        games = obj.get("games", [])
        return games if isinstance(games, list) else []
    except FileNotFoundError:
        log.error("First games registry not found at %s", path)
    except json.JSONDecodeError as exc:
        log.error("First games registry malformed: %s", exc)
    except OSError as exc:
        log.error("Could not read first games registry: %s", exc)
    return []


# ── Helpers ───────────────────────────────────────────────────────────────────

def _platform_tag(platform: str) -> str:
    """Return a short readable platform tag."""
    if not platform:
        return ""
    p = platform.lower()
    if "arcade" in p:
        return "Arcade"
    if "nes" in p or "famicom" in p:
        return "NES"
    if "snes" in p:
        return "SNES"
    if "genesis" in p or "mega drive" in p:
        return "Genesis"
    if "game boy" in p:
        return "Game Boy"
    if "pc" in p or "apple" in p or "mac" in p or "amiga" in p:
        return "PC"
    if "mainframe" in p or "plato" in p:
        return "Mainframe"
    if "atari" in p:
        return "Atari"
    return platform.split("/")[0].strip()


def _build_list_embed(
    games: List[Dict[str, Any]],
    title: str,
    footer: str,
) -> discord.Embed:
    embed = discord.Embed(title=title, color=0x000000)

    lines = []
    for i, g in enumerate(games[:50], start=1):
        name  = g.get("name", "Untitled")
        year  = g.get("year", "—")
        plat  = _platform_tag(g.get("platform", ""))
        genre = g.get("genre", "")

        parts = [p for p in [plat, genre] if p]
        tail  = f" — {' · '.join(parts)}" if parts else ""
        lines.append(f"`{i:2}.` **{name}** ({year}){tail}")

    embed.description = "\n".join(lines)[:4000]
    embed.set_footer(text=footer)

    # Thumbnail: first game's image
    if games and games[0].get("image_url"):
        embed.set_thumbnail(url=games[0]["image_url"])

    return embed


def _build_detail_embed(g: Dict[str, Any]) -> discord.Embed:
    name      = g.get("name", "Unknown")
    year      = g.get("year", "—")
    platform  = g.get("platform", "")
    developer = g.get("developer", "")
    publisher = g.get("publisher", "")
    genre     = g.get("genre", "")
    summary   = g.get("summary", "")
    significance = g.get("significance", "")
    image_url = g.get("image_url", "")
    image_credit = g.get("image_credit", "")
    sources   = g.get("sources", [])

    embed = discord.Embed(
        title=f"{name}  ({year})",
        color=0x000000,
    )

    if summary:
        embed.description = summary

    if platform:
        embed.add_field(name="Platform", value=platform, inline=True)
    if developer:
        embed.add_field(name="Developer", value=developer, inline=True)
    if publisher and publisher != "—":
        embed.add_field(name="Publisher", value=publisher, inline=True)
    if genre:
        embed.add_field(name="Genre", value=genre, inline=True)
    if significance:
        embed.add_field(name="Significance", value=significance, inline=False)

    # Source links
    if sources:
        link_parts = []
        for s in sources[:3]:
            label = s.get("name", "Source")
            url   = s.get("url", "")
            if url:
                link_parts.append(f"[{label}]({url})")
        if link_parts:
            embed.add_field(name="Sources", value="  ·  ".join(link_parts), inline=False)

    if image_url:
        embed.set_thumbnail(url=image_url)

    footer = image_credit if image_credit else "Early Games Registry"
    embed.set_footer(text=footer)

    return embed


# ── Command group ─────────────────────────────────────────────────────────────

class GamesGroup(app_commands.Group):
    def __init__(self, data_dir: str):
        super().__init__(name="games", description="First and early commercially significant games (curated)")
        self._data_dir = data_dir

    # /games list ──────────────────────────────────────────────────────────────

    @app_commands.command(
        name="list",
        description="Browse early commercial games, sorted by year",
    )
    @app_commands.describe(
        year="Filter by release year",
        genre="Filter by genre (partial match)",
        platform="Filter by platform (partial match)",
    )
    async def list_games(
        self,
        interaction: discord.Interaction,
        year: Optional[int] = None,
        genre: Optional[str] = None,
        platform: Optional[str] = None,
    ) -> None:
        await interaction.response.defer()

        games = _load(self._data_dir)
        if not games:
            await interaction.followup.send(
                "Games registry could not be loaded.", ephemeral=True
            )
            return

        filters: List[str] = []

        if year is not None:
            games = [g for g in games if g.get("year") == year]
            filters.append(str(year))

        if genre:
            needle = genre.lower()
            games  = [g for g in games if needle in g.get("genre", "").lower()]
            filters.append(genre)

        if platform:
            needle  = platform.lower()
            games   = [g for g in games if needle in g.get("platform", "").lower()]
            filters.append(platform)

        if not games:
            hint = " + ".join(filters) if filters else "those filters"
            await interaction.followup.send(
                f"No games found for **{hint}**.", ephemeral=True
            )
            return

        games = sorted(games, key=lambda g: (g.get("year", 9999), g.get("name", "")))

        filter_str = " — " + ", ".join(filters) if filters else ""
        title  = f"Early Commercial Games{filter_str}"
        footer = f"{len(games)} result(s) · Use /games info <title> for full details"

        await interaction.followup.send(embed=_build_list_embed(games, title, footer))

    # /games info ──────────────────────────────────────────────────────────────

    @app_commands.command(
        name="info",
        description="Full details for a specific early game",
    )
    @app_commands.describe(title="Game title (partial match)")
    async def info(
        self,
        interaction: discord.Interaction,
        title: str,
    ) -> None:
        await interaction.response.defer()

        games = _load(self._data_dir)
        if not games:
            await interaction.followup.send(
                "Games registry could not be loaded.", ephemeral=True
            )
            return

        needle  = title.lower().strip()
        matches = [g for g in games if needle in g.get("name", "").lower()]

        if not matches:
            await interaction.followup.send(
                f"No game found matching **\"{title}\"**.", ephemeral=True
            )
            return

        # Exact match preferred, otherwise earliest
        exact = [g for g in matches if g.get("name", "").lower() == needle]
        pick  = exact[0] if exact else sorted(matches, key=lambda g: g.get("year", 9999))[0]

        await interaction.followup.send(embed=_build_detail_embed(pick))

    # /games by_year ───────────────────────────────────────────────────────────

    @app_commands.command(
        name="by_year",
        description="Summary of games per year, or list all games for a specific year",
    )
    @app_commands.describe(year="Leave empty for a year-by-year summary")
    async def by_year(
        self,
        interaction: discord.Interaction,
        year: Optional[int] = None,
    ) -> None:
        await interaction.response.defer()

        games = _load(self._data_dir)
        if not games:
            await interaction.followup.send(
                "Games registry could not be loaded.", ephemeral=True
            )
            return

        if year is None:
            # Year summary
            counts: Dict[int, int] = {}
            for g in games:
                y = g.get("year")
                if isinstance(y, int):
                    counts[y] = counts.get(y, 0) + 1

            lines = [f"`{y}` — {counts[y]} game(s)" for y in sorted(counts)]
            embed = discord.Embed(
                title="Early Games by Year",
                description="\n".join(lines)[:4000],
                color=0x000000,
            )
            embed.set_footer(text="Use /games by_year <year> to list entries for a specific year")
            await interaction.followup.send(embed=embed)
            return

        filtered = sorted(
            [g for g in games if g.get("year") == year],
            key=lambda g: g.get("name", "")
        )

        if not filtered:
            await interaction.followup.send(
                f"No entries found for **{year}**.", ephemeral=True
            )
            return

        await interaction.followup.send(
            embed=_build_list_embed(
                filtered,
                title=f"Early Games — {year}",
                footer=f"{len(filtered)} game(s) in {year}",
            )
        )


# ── Registration ──────────────────────────────────────────────────────────────

async def register(bot: discord.Client, data_dir: str) -> None:
    """Register /games commands. Called by main.py loader."""
    if bot.tree.get_command("games"):
        return
    bot.tree.add_command(GamesGroup(data_dir))

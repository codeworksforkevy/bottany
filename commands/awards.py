from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

import discord
from discord import app_commands

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path resolution — resolves relative to this file so it works regardless of
# the working directory the bot is launched from.
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(_HERE, "data", "awards_registry.json")

# Lookup tables used by autocomplete
_AWARD_CHOICES = [
    app_commands.Choice(name="The Game Awards (TGA)",        value="tga"),
    app_commands.Choice(name="BAFTA Games Awards",           value="bafta"),
    app_commands.Choice(name="D.I.C.E. Awards",              value="dice"),
    app_commands.Choice(name="Golden Joystick Awards (GJA)", value="gja"),
    app_commands.Choice(name="IGN's Best of Year",           value="ign"),
    app_commands.Choice(name="GDC Choice Awards",            value="gdc"),
]

_CATEGORY_CHOICES = [
    app_commands.Choice(name="Game of the Year",        value="goty"),
    app_commands.Choice(name="Best Narrative",          value="narrative"),
    app_commands.Choice(name="Best Art Direction",      value="art"),
    app_commands.Choice(name="Best Score / Music",      value="music"),
    app_commands.Choice(name="Best Action Game",        value="action"),
    app_commands.Choice(name="Best RPG",                value="rpg"),
    app_commands.Choice(name="Best Indie Game",         value="indie"),
    app_commands.Choice(name="Best Multiplayer",        value="multiplayer"),
]

# Human-readable labels for category keys
_CATEGORY_LABELS: Dict[str, str] = {
    "goty":        "Game of the Year",
    "narrative":   "Best Narrative",
    "art":         "Best Art Direction",
    "music":       "Best Score / Music",
    "action":      "Best Action Game",
    "rpg":         "Best RPG",
    "indie":       "Best Indie Game",
    "multiplayer": "Best Multiplayer",
}

# Emoji badges per award show
_AWARD_BADGES: Dict[str, str] = {
    "tga":   "🏆",
    "bafta": "🎭",
    "dice":  "🎲",
    "gja":   "🕹️",
    "ign":   "🎮",
    "gdc":   "👾",
}


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _load() -> Dict[str, Any]:
    """Load and return the awards registry, or {} on any failure."""
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        log.error("awards_registry.json not found at %s", DATA_FILE)
        return {}
    except json.JSONDecodeError as exc:
        log.error("awards_registry.json is malformed: %s", exc)
        return {}
    except OSError as exc:
        log.error("Could not read awards_registry.json: %s", exc)
        return {}


def _get_winners(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    winners = data.get("winners")
    if not isinstance(winners, list):
        return []
    return winners


def _award_name(data: Dict[str, Any], award_id: str) -> str:
    """Return human-readable award name from registry metadata."""
    return (
        data.get("awards", {})
            .get(award_id.lower(), {})
            .get("name", award_id.upper())
    )


def _build_embed(
    results: List[Dict[str, Any]],
    data: Dict[str, Any],
    year: Optional[int],
    award: Optional[str],
    category: Optional[str],
    game: Optional[str],
    show_nominees: bool,
) -> discord.Embed:
    """Build a rich embed from filtered results."""

    # --- title / description ------------------------------------------------
    filters: List[str] = []
    if year:
        filters.append(str(year))
    if award:
        filters.append(_award_name(data, award))
    if category:
        filters.append(_CATEGORY_LABELS.get(category, category))
    if game:
        filters.append(f'"{game}"')

    title = "🎖️ Game Awards" + (f" — {', '.join(filters)}" if filters else "")
    embed = discord.Embed(title=title, color=0xF1C40F)

    # --- group by year → show -----------------------------------------------
    # Keep at most 20 entries to stay within embed limits
    capped = results[:20]
    grouped: Dict[int, List[Dict[str, Any]]] = {}
    for r in sorted(capped, key=lambda x: (x["year"], x["award_id"])):
        grouped.setdefault(r["year"], []).append(r)

    for yr in sorted(grouped):
        for r in grouped[yr]:
            badge  = _AWARD_BADGES.get(r["award_id"], "🏅")
            show   = _award_name(data, r["award_id"])
            cat    = r.get("category", "—")
            winner = r.get("winner", "Unknown")

            field_name  = f"{badge} {yr} · {show}"
            field_value = f"**{cat}**\n🥇 {winner}"

            if show_nominees:
                noms: List[str] = r.get("nominees", [])
                if noms:
                    nom_lines = "\n".join(f"  • {n}" for n in noms)
                    field_value += f"\n*Nominees:*\n{nom_lines}"

            embed.add_field(name=field_name, value=field_value, inline=False)

    # --- footer -------------------------------------------------------------
    total = len(results)
    shown = len(capped)
    footer = f"Showing {shown} of {total} result(s)"
    if total > 20:
        footer += " — narrow your search to see more"
    meta = data.get("meta", {})
    if meta.get("years_covered"):
        footer += f" · Coverage: {meta['years_covered']}"
    embed.set_footer(text=footer)

    return embed


# ---------------------------------------------------------------------------
# Command registration
# ---------------------------------------------------------------------------

def register(bot, data_dir) -> None:
    tree = bot.tree

    @tree.command(
        name="awards",
        description="Query major game award winners and nominees (TGA, BAFTA, DICE, GJA, IGN, GDC).",
    )
    @app_commands.describe(
        year="Filter by year (e.g. 2023)",
        award="Filter by award show",
        category="Filter by award category",
        game="Filter by game title (partial match)",
        nominees="Also show nominees, not just the winner",
    )
    @app_commands.choices(award=_AWARD_CHOICES, category=_CATEGORY_CHOICES)
    async def awards_cmd(
        interaction: discord.Interaction,
        year: Optional[int] = None,
        award: Optional[str] = None,
        category: Optional[str] = None,
        game: Optional[str] = None,
        nominees: Optional[bool] = False,
    ) -> None:

        # Defer immediately — data load + embed build can take a moment
        await interaction.response.defer(ephemeral=False)

        data = _load()
        if not data:
            await interaction.followup.send(
                "⚠️ The awards registry could not be loaded. "
                "Please ask an admin to check the data files.",
                ephemeral=True,
            )
            return

        results = _get_winners(data)

        if not results:
            await interaction.followup.send(
                "⚠️ The registry appears to be empty.", ephemeral=True
            )
            return

        # --- apply filters --------------------------------------------------
        if year is not None:
            results = [r for r in results if r.get("year") == year]

        if award:
            results = [r for r in results if r.get("award_id", "").lower() == award.lower()]

        if category:
            results = [
                r for r in results
                if r.get("category_key", "").lower() == category.lower()
            ]

        if game:
            needle = game.lower()
            results = [
                r for r in results
                if needle in r.get("winner", "").lower()
                or any(needle in n.lower() for n in r.get("nominees", []))
            ]

        if not results:
            hint_parts: List[str] = []
            if year:
                hint_parts.append(f"year **{year}**")
            if award:
                hint_parts.append(f"show **{award.upper()}**")
            if category:
                hint_parts.append(f"category **{_CATEGORY_LABELS.get(category, category)}**")
            if game:
                hint_parts.append(f"game **\"{game}\"**")
            hint = " + ".join(hint_parts) if hint_parts else "those filters"
            await interaction.followup.send(
                f"😕 No results found for {hint}.\n"
                "Try broadening your search — remove a filter or check the spelling.",
                ephemeral=True,
            )
            return

        embed = _build_embed(results, data, year, award, category, game, nominees or False)
        await interaction.followup.send(embed=embed)

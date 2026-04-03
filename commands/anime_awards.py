# anime_awards.py
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

import discord
from discord import app_commands

log = logging.getLogger(__name__)

_FILENAME = "anime_awards_registry.json"

_TYPE_CHOICES = [
    app_commands.Choice(name="🎌 Anime",   value="anime"),
    app_commands.Choice(name="🎬 Cartoon", value="cartoon"),
]

_SHOW_CHOICES = [
    app_commands.Choice(name="🏆 Academy Awards (Oscars)",   value="oscars"),
    app_commands.Choice(name="🎌 Japan Academy Film Prize",  value="japan_academy"),
    app_commands.Choice(name="🌟 Annecy Festival",           value="annecy"),
    app_commands.Choice(name="🎭 Annie Awards",              value="annie"),
    app_commands.Choice(name="🇯🇵 TAAF",                      value="taaf"),
    app_commands.Choice(name="🎥 Mainichi Film Awards",      value="mainichi"),
    app_commands.Choice(name="🎃 Fantasia Festival",         value="fantasia"),
    app_commands.Choice(name="🕷️ Sitges Film Festival",      value="sitges"),
    app_commands.Choice(name="🎞️ Blue Ribbon Awards",        value="blue_ribbon"),
    app_commands.Choice(name="📰 Kinema Junpō Awards",       value="kinema_junpo"),
]

_SHOW_EMOJIS = {
    "oscars":             "🏆",
    "japan_academy":      "🎌",
    "japan_academy_pre":  "🎌",
    "annecy":             "🌟",
    "annie":              "🎭",
    "taaf":               "🇯🇵",
    "mainichi":           "🎥",
    "fantasia":           "🎃",
    "sitges":             "🕷️",
    "blue_ribbon":        "🎞️",
    "kinema_junpo":       "📰",
}

_TYPE_EMOJIS = {
    "anime":   "🎌",
    "cartoon": "🎬",
}


# ── Loader ────────────────────────────────────────────────────────────────────

def _load(data_dir: str) -> Dict[str, Any]:
    path = os.path.join(str(data_dir), _FILENAME)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        log.error("Anime awards registry not found at %s", path)
    except json.JSONDecodeError as exc:
        log.error("Anime awards registry malformed: %s", exc)
    except OSError as exc:
        log.error("Could not read anime awards registry: %s", exc)
    return {}


# ── Embed builder ─────────────────────────────────────────────────────────────

def _build_embed(
    winners: List[Dict[str, Any]],
    show_index: Dict[str, Dict[str, Any]],
    filters: List[str],
    total: int,
) -> discord.Embed:
    title = "🎌 Anime & Animation Awards"
    if filters:
        title += f" — {', '.join(filters)}"

    embed = discord.Embed(title=title, color=0xE74C3C)

    # Cap at 20 fields to stay within Discord embed limits
    for item in winners[:20]:
        film    = item.get("title", "Unknown")
        year    = item.get("year", "—")
        itype   = item.get("type", "")
        award   = item.get("award", "—")
        show_id = item.get("award_show_id", "")
        source  = item.get("official_source", "")

        show_emoji = _SHOW_EMOJIS.get(show_id, "🎖️")

        # **Bold** film title with year in plain text — clean, readable
        # Italic type tag only when not filtered (so it adds info rather than repeating it)
        type_tag = f" *· {itype}*" if itype else ""
        field_name = f"**{film}** ({year}){type_tag}"

        # Award show emoji + award name, source as hyperlink on next line
        field_value = f"{show_emoji} {award}"
        if source:
            field_value += f"\n[↗ Source]({source})"

        embed.add_field(name=field_name, value=field_value, inline=False)

    shown = min(len(winners), 20)
    footer = f"Showing {shown} of {total} result(s)"
    if total > 20:
        footer += " — narrow your search to see fewer results"
    embed.set_footer(text=footer + " · Official sources only")
    return embed


# ── Command group ─────────────────────────────────────────────────────────────

class AnimeGroup(app_commands.Group):
    def __init__(self, data_dir: str):
        super().__init__(name="anime", description="Anime & animation award winners")
        self._data_dir = data_dir

    @app_commands.command(
        name="awards",
        description="Browse anime & animation award winners (Oscars, Japan Academy, Annecy, Annie Awards…)",
    )
    @app_commands.describe(
        type="Filter by animation type",
        award_show="Filter by award show",
        year="Filter by year (e.g. 2024)",
        title="Search by film title (partial match)",
    )
    @app_commands.choices(type=_TYPE_CHOICES, award_show=_SHOW_CHOICES)
    async def awards(
        self,
        interaction: discord.Interaction,
        type: Optional[str] = None,
        award_show: Optional[str] = None,
        year: Optional[int] = None,
        title: Optional[str] = None,
    ) -> None:

        await interaction.response.defer()

        data = _load(self._data_dir)
        if not data:
            await interaction.followup.send(
                "⚠️ Awards registry could not be loaded. "
                "Please ask an admin to check `data/anime_awards_registry.json`.",
                ephemeral=True,
            )
            return

        winners    = data.get("winners", [])
        show_index = {s["id"]: s for s in data.get("award_shows", [])}

        filters: List[str] = []

        if type:
            winners = [w for w in winners if w.get("type", "").lower() == type.lower()]
            filters.append(_TYPE_EMOJIS.get(type.lower(), "") + " " + type.title())

        if award_show:
            winners = [w for w in winners if w.get("award_show_id") == award_show]
            show_info = show_index.get(award_show, {})
            filters.append(_SHOW_EMOJIS.get(award_show, "") + " " + show_info.get("short", award_show))

        if year is not None:
            winners = [w for w in winners if w.get("year") == year]
            filters.append(str(year))

        if title:
            needle = title.lower().strip()
            winners = [w for w in winners if needle in w.get("title", "").lower()]
            filters.append(f'"{title}"')

        if not winners:
            hint = " + ".join(filters) if filters else "those filters"
            await interaction.followup.send(
                f"😕 No results found for **{hint}**.\n"
                "Try removing a filter or broadening your search.",
                ephemeral=True,
            )
            return

        # Sort: most recent first, then alphabetically by award show
        winners = sorted(winners, key=lambda w: (-w.get("year", 0), w.get("award_show_id", "")))

        embed = _build_embed(winners, show_index, filters, total=len(winners))
        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="shows",
        description="List all tracked award shows with official links.",
    )
    async def shows(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        data = _load(self._data_dir)
        if not data:
            await interaction.followup.send(
                "⚠️ Awards registry could not be loaded.", ephemeral=True
            )
            return

        shows = data.get("award_shows", [])
        embed = discord.Embed(
            title="🎌 Tracked Anime & Animation Award Shows",
            color=0xE74C3C,
        )

        for show in shows:
            emoji  = _SHOW_EMOJIS.get(show.get("id", ""), "🎖️")
            name   = show.get("name", "Unknown")
            since  = show.get("since")
            region = show.get("region", "").title()
            kind   = show.get("kind", "").title()
            org    = show.get("organizer", "")
            url    = show.get("url", "")

            value_parts = []
            if since:   value_parts.append(f"📅 Since {since}")
            if region:  value_parts.append(f"🌍 {region}")
            if kind:    value_parts.append(f"🏷 {kind}")
            if org:     value_parts.append(f"🏢 {org}")
            if url:     value_parts.append(f"[Official site]({url})")

            embed.add_field(
                name=f"{emoji} {name}",
                value="\n".join(value_parts),
                inline=False,
            )

        embed.set_footer(text=f"{len(shows)} award shows tracked · Official sources only")
        await interaction.followup.send(embed=embed)


# ── Registration ──────────────────────────────────────────────────────────────

async def register(bot: discord.Client, data_dir: str) -> None:
    """Register /anime awards and /anime shows. Called by main.py loader."""
    if bot.tree.get_command("anime"):
        return
    bot.tree.add_command(AnimeGroup(data_dir))

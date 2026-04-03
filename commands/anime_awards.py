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

# ── Kanji / Japanese labels used in embeds ────────────────────────────────────
# 監督  = kantoku   (director)
# 制作  = seisaku   (production / studio)
# 技術  = gijutsu   (technique)
# 受賞  = jushō     (award received)
# アニメ = anime
# 賞    = shō       (award/prize)
# 大賞  = taishō    (grand prize)

_TYPE_LABELS = {
    "anime":   "アニメ (Anime)",
    "cartoon": "Animation",
}

# ── Discord choices ────────────────────────────────────────────────────────────

_TYPE_CHOICES = [
    app_commands.Choice(name="Anime",   value="anime"),
    app_commands.Choice(name="Cartoon", value="cartoon"),
]

_SHOW_CHOICES = [
    app_commands.Choice(name="Academy Awards (Oscars)",  value="oscars"),
    app_commands.Choice(name="Japan Academy Film Prize", value="japan_academy"),
    app_commands.Choice(name="Annecy Festival",          value="annecy"),
    app_commands.Choice(name="Annie Awards",             value="annie"),
    app_commands.Choice(name="TAAF",                     value="taaf"),
    app_commands.Choice(name="Mainichi Film Awards",     value="mainichi"),
    app_commands.Choice(name="Fantasia Festival",        value="fantasia"),
    app_commands.Choice(name="Sitges Film Festival",     value="sitges"),
    app_commands.Choice(name="Blue Ribbon Awards",       value="blue_ribbon"),
    app_commands.Choice(name="Kinema Junpo Awards",      value="kinema_junpo"),
    app_commands.Choice(name="Berlinale",                value="berlinale"),
    app_commands.Choice(name="Hiroshima Animation Fest", value="hiroshima"),
    app_commands.Choice(name="Japan Film Festival",      value="japan_film_festival"),
]


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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_technique(v: Optional[str]) -> Optional[str]:
    """Normalise animation technique strings.
    'Cel animation / Digital / CGI / Mixed' → 'Cel animation / Digital / CGI (Mixed)'
    Any bare 'Mixed' at the end gets wrapped in parens for clarity.
    """
    if not v:
        return None
    s = v.strip()
    # If it ends with a bare '/ Mixed' or just 'Mixed', wrap it
    import re
    s = re.sub(r'\s*/\s*Mixed\s*$', ' (Mixed)', s)
    # If it's just 'Mixed' on its own
    if s.lower() == 'mixed':
        s = '(Mixed)'
    return s


def _award_label(award: str) -> str:
    """Append Japanese award kanji label based on award name keywords."""
    a = award.lower()
    if "grand prize" in a or "grand prix" in a or "cristal" in a or "taishō" in a:
        return f"{award}  大賞 (Grand Prize)"
    return f"{award}  賞 (Award)"


# ── Embed builder ─────────────────────────────────────────────────────────────

def _build_embed(
    winners: List[Dict[str, Any]],
    filters: List[str],
    total: int,
) -> discord.Embed:
    title = "アニメアワード (Anime Awards)"
    if filters:
        title += f" — {', '.join(filters)}"

    embed = discord.Embed(title=title, color=0xFFF9C4)

    for item in winners[:20]:
        # ── Field name: title_display or title + jp, year ─────────────────
        title_en  = item.get("title", "Unknown")
        title_jp  = item.get("title_jp", "")
        year      = item.get("year", "—")
        itype     = item.get("type", "")
        type_label = _TYPE_LABELS.get(itype.lower(), itype)

        if title_jp:
            field_name = f"**{title_en}** | {title_jp}  ({year})"
        else:
            field_name = f"**{title_en}**  ({year})"

        # ── Field value: structured lines ─────────────────────────────────
        lines: List[str] = []

        # Type label (アニメ / Animation)
        if type_label:
            lines.append(f"*{type_label}*")

        # Studio
        studios = item.get("studio", [])
        if studios:
            lines.append(f"制作 (Studio): {', '.join(studios)}")

        # Director
        directors = item.get("director", [])
        if directors:
            lines.append(f"監督 (Director): {', '.join(directors)}")

        # Animation technique — normalised
        technique = _fmt_technique(item.get("animation_technique") or item.get("technique"))
        if technique:
            lines.append(f"技術 (Technique): {technique}")

        # Award line
        award = item.get("award", "—")
        lines.append(f"受賞 (Award): {_award_label(award)}  ({year})")

        # Source link
        source = item.get("official_source", "")
        if source:
            lines.append(f"[↗ Source]({source})")

        embed.add_field(name=field_name, value="\n".join(lines), inline=False)

    # Show thumbnail of the most recent / top result (avatar size)
    if winners:
        thumb = (winners[0].get("thumbnail")
                 or winners[0].get("thumbnail_cdn_fallback", ""))
        if thumb:
            embed.set_thumbnail(url=thumb)

    shown  = min(len(winners), 20)
    footer = f"Showing {shown} of {total} result(s)"
    if total > 20:
        footer += " — narrow your search to see fewer results"
    embed.set_footer(text=footer + " · Official sources only")
    return embed


def _build_detail_embed(item: Dict[str, Any]) -> discord.Embed:
    """Full detail embed for a single entry — used by /anime info."""
    title_en = item.get("title", "Unknown")
    title_jp = item.get("title_jp", "")
    year     = item.get("year", "—")
    itype    = item.get("type", "")

    if title_jp:
        embed_title = f"{title_en} | {title_jp}"
    else:
        embed_title = title_en

    embed = discord.Embed(title=embed_title, color=0xFFF9C4)

    type_label = _TYPE_LABELS.get(itype.lower(), itype)
    if type_label:
        embed.description = f"*{type_label}*"

    # Studio + director
    studios   = item.get("studio", [])
    directors = item.get("director", [])
    if studios:
        embed.add_field(name="制作 (Studio)", value=", ".join(studios), inline=True)
    if directors:
        embed.add_field(name="監督 (Director)", value=", ".join(directors), inline=True)
    if year:
        embed.add_field(name="年 (Year)", value=str(year), inline=True)

    # Technique
    technique = _fmt_technique(item.get("animation_technique") or item.get("technique"))
    if technique:
        embed.add_field(name="技術 (Technique)", value=technique, inline=False)

    # Award
    award = item.get("award", "—")
    embed.add_field(
        name="受賞 (Award)",
        value=f"{_award_label(award)}  ({year})",
        inline=False,
    )

    # Links
    source  = item.get("official_source", "")
    imdb    = item.get("imdb_link", "")
    mal     = item.get("mal_link", "")
    thumb   = item.get("thumbnail") or item.get("thumbnail_cdn_fallback", "")

    link_parts = []
    if source: link_parts.append(f"[Official]({source})")
    if imdb:   link_parts.append(f"[IMDb]({imdb})")
    if mal:    link_parts.append(f"[MAL]({mal})")
    if link_parts:
        embed.add_field(name="Links", value="  ".join(link_parts), inline=False)

    if thumb:
        embed.set_thumbnail(url=thumb)

    embed.set_footer(text="アニメアワード (Anime Awards) · Official sources only")
    return embed


# ── Command group ─────────────────────────────────────────────────────────────

class AnimeGroup(app_commands.Group):
    def __init__(self, data_dir: str):
        super().__init__(name="anime", description="Anime & animation award winners")
        self._data_dir = data_dir

    # /anime awards ────────────────────────────────────────────────────────────

    @app_commands.command(
        name="awards",
        description="Browse anime & animation award winners",
    )
    @app_commands.describe(
        type="Filter by animation type",
        award_show="Filter by award show",
        year="Filter by year (e.g. 1988)",
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
                "Awards registry could not be loaded. "
                "Please ask an admin to check `data/anime_awards_registry.json`.",
                ephemeral=True,
            )
            return

        winners    = data.get("winners", [])
        show_index = {s["id"]: s for s in data.get("award_shows", [])}

        filters: List[str] = []

        if type:
            winners = [w for w in winners if w.get("type", "").lower() == type.lower()]
            filters.append(_TYPE_LABELS.get(type.lower(), type.title()))

        if award_show:
            winners = [w for w in winners if w.get("award_show_id") == award_show]
            show_info = show_index.get(award_show, {})
            filters.append(show_info.get("short", award_show))

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
                f"No results found for **{hint}**.\n"
                "Try removing a filter or broadening your search.",
                ephemeral=True,
            )
            return

        winners = sorted(winners, key=lambda w: (-w.get("year", 0), w.get("award_show_id", "")))
        embed   = _build_embed(winners, filters, total=len(winners))
        await interaction.followup.send(embed=embed)

    # /anime info ──────────────────────────────────────────────────────────────

    @app_commands.command(
        name="info",
        description="Full details for a single anime title",
    )
    @app_commands.describe(title="Film title (partial match)")
    async def info(
        self,
        interaction: discord.Interaction,
        title: str,
    ) -> None:
        await interaction.response.defer()

        data = _load(self._data_dir)
        if not data:
            await interaction.followup.send(
                "Awards registry could not be loaded.", ephemeral=True
            )
            return

        needle  = title.lower().strip()
        winners = data.get("winners", [])
        matches = [w for w in winners if needle in w.get("title", "").lower()]

        if not matches:
            await interaction.followup.send(
                f"No entry found matching **\"{title}\"**.", ephemeral=True
            )
            return

        # If multiple matches, show the most recent
        matches = sorted(matches, key=lambda w: -w.get("year", 0))
        await interaction.followup.send(embed=_build_detail_embed(matches[0]))

    # /anime shows ─────────────────────────────────────────────────────────────

    @app_commands.command(
        name="shows",
        description="List all tracked award shows",
    )
    async def shows(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        data = _load(self._data_dir)
        if not data:
            await interaction.followup.send(
                "Awards registry could not be loaded.", ephemeral=True
            )
            return

        shows = data.get("award_shows", [])
        embed = discord.Embed(title="アニメアワード (Anime Awards) — Shows", color=0xFFF9C4)

        for show in shows:
            name   = show.get("name", "Unknown")
            since  = show.get("since")
            region = show.get("region", "").title()
            kind   = show.get("kind", "").title()
            org    = show.get("organizer", "")
            url    = show.get("url", "")

            parts = []
            if since:  parts.append(f"Since {since}")
            if region: parts.append(region)
            if kind:   parts.append(kind)
            if org:    parts.append(org)
            if url:    parts.append(f"[Official site]({url})")

            embed.add_field(
                name=f"🏅 {name}",
                value=" · ".join(parts),
                inline=False,
            )

        embed.set_footer(text=f"{len(shows)} award shows tracked · Official sources only")
        await interaction.followup.send(embed=embed)


# ── Registration ──────────────────────────────────────────────────────────────

async def register(bot: discord.Client, data_dir: str) -> None:
    """Register /anime commands. Called by main.py loader."""
    if bot.tree.get_command("anime"):
        return
    bot.tree.add_command(AnimeGroup(data_dir))

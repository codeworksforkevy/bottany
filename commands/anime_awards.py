from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import discord
from discord import app_commands

log = logging.getLogger(__name__)

ANIME_AWARDS_FILENAME = "anime_awards_registry.json"

# ---------------------------------------------------------------------------
# Path resolution — resolves relative to this file so it works regardless of
# the working directory the bot is launched from.
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _awards_path(data_dir: str) -> str:
    """Absolute path to the anime awards registry JSON."""
    return os.path.join(os.path.abspath(data_dir), ANIME_AWARDS_FILENAME)


def _load_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        log.error("Anime awards registry not found at %s", path)
        return default
    except json.JSONDecodeError as exc:
        log.error("Anime awards registry malformed (%s): %s", path, exc)
        return default
    except OSError as exc:
        log.error("Could not read anime awards registry (%s): %s", path, exc)
        return default


def _load_awards(data_dir: str) -> List[Dict[str, Any]]:
    obj = _load_json(
        _awards_path(data_dir),
        {"version": 1, "updated_utc": _utc_now(), "awards": []},
    )
    awards = obj.get("awards") if isinstance(obj, dict) else []
    if not isinstance(awards, list):
        return []
    out: List[Dict[str, Any]] = []
    for a in awards:
        # Require at minimum id, name, and url
        if isinstance(a, dict) and a.get("id") and a.get("name") and a.get("url"):
            out.append(a)
    return out


# ---------------------------------------------------------------------------
# Autocomplete choices
# ---------------------------------------------------------------------------

_REGION_CHOICES = [
    app_commands.Choice(name="Japan",         value="japan"),
    app_commands.Choice(name="International", value="international"),
]

_KIND_CHOICES = [
    app_commands.Choice(name="Industry",  value="industry"),
    app_commands.Choice(name="Festival",  value="festival"),
    app_commands.Choice(name="Fan Vote",  value="fan"),
]


# ---------------------------------------------------------------------------
# Group
# ---------------------------------------------------------------------------

class AnimeGroup(app_commands.Group):
    def __init__(self, data_dir: str) -> None:
        super().__init__(
            name="anime",
            description="Anime/animation awards — official & trusted links only.",
        )
        self._data_dir = data_dir

    @app_commands.command(
        name="awards",
        description="List prestigious anime/animation awards with official links.",
    )
    @app_commands.describe(
        region="Filter by region",
        kind="Filter by award type",
    )
    @app_commands.choices(region=_REGION_CHOICES, kind=_KIND_CHOICES)
    async def awards(
        self,
        interaction: discord.Interaction,
        region: Optional[str] = None,
        kind: Optional[str] = None,
    ) -> None:

        await interaction.response.defer()

        region_n = (region or "").strip().lower() or None
        kind_n   = (kind   or "").strip().lower() or None

        all_awards = _load_awards(self._data_dir)

        if not all_awards:
            await interaction.followup.send(
                "⚠️ Anime awards registry could not be loaded or is empty. "
                "Please ask an admin to check `data/anime_awards_registry.json`.",
                ephemeral=True,
            )
            return

        def ok(a: Dict[str, Any]) -> bool:
            if region_n and str(a.get("region") or "").lower() != region_n:
                return False
            if kind_n and str(a.get("kind") or "").lower() != kind_n:
                return False
            return True

        picks = [a for a in all_awards if ok(a)]
        picks.sort(key=lambda x: (int(x.get("since") or 9999), str(x.get("name") or "")))

        # --- build title ----------------------------------------------------
        title_parts: List[str] = []
        if region_n:
            title_parts.append(f"region:{region_n}")
        if kind_n:
            title_parts.append(f"kind:{kind_n}")
        title = "🎌 Anime / Animation Awards"
        if title_parts:
            title += " (" + ", ".join(title_parts) + ")"

        embed = discord.Embed(title=title, color=0xE74C3C)

        if not picks:
            embed.description = (
                "😕 No awards matched your filters.\n"
                "Try removing the **region** or **kind** filter."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # --- build body (max 10 entries to stay within Discord limits) ------
        lines: List[str] = []
        for a in picks[:10]:
            name      = a.get("name", "Unknown")
            url       = a.get("url", "")
            since     = a.get("since")
            organizer = a.get("organizer")
            note      = (a.get("note") or "").strip()

            meta: List[str] = []
            if since:
                meta.append(f"since {since}")
            if organizer:
                meta.append(str(organizer))
            if a.get("region"):
                meta.append(str(a["region"]).capitalize())
            if a.get("kind"):
                meta.append(str(a["kind"]).capitalize())
            meta_txt = " · ".join(meta)

            # Hyperlink the award name to its URL
            entry = f"**[{name}]({url})**"
            if note:
                entry += f"\n> {note}"
            if meta_txt:
                entry += f"\n_{meta_txt}_"

            lines.append(entry)

        embed.description = "\n\n".join(lines)

        shown = len(picks[:10])
        total = len(picks)
        footer = f"Showing {shown} of {total}"
        if total > 10:
            footer += " — use region/kind filters to narrow results"
        embed.set_footer(text=footer + " · Official/trusted links only.")

        await interaction.followup.send(embed=embed)


# ---------------------------------------------------------------------------
# Registration helper
# ---------------------------------------------------------------------------

async def register_anime_awards(bot: discord.Client, data_dir: str) -> None:
    """Add the /anime command group to the bot and sync the tree."""
    bot.tree.add_command(AnimeGroup(data_dir))
    try:
        await bot.tree.sync()
    except discord.HTTPException as exc:
        log.warning("Tree sync failed (will retry on reconnect): %s", exc)
    except Exception as exc:
        log.error("Unexpected error during tree sync: %s", exc)

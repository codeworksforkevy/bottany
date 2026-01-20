import os
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import discord
from discord import app_commands

ANIME_AWARDS_FILENAME = "anime_awards_registry.json"


def _utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _awards_path(data_dir: str) -> str:
    return os.path.join(data_dir, ANIME_AWARDS_FILENAME)


def _load_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _load_awards(data_dir: str) -> List[Dict[str, Any]]:
    obj = _load_json(_awards_path(data_dir), {"version": 1, "updated_utc": _utc_now(), "awards": []})
    awards = obj.get("awards") if isinstance(obj, dict) else []
    if not isinstance(awards, list):
        return []
    out: List[Dict[str, Any]] = []
    for a in awards:
        if isinstance(a, dict) and a.get("id") and a.get("name") and a.get("url"):
            out.append(a)
    return out


class AnimeGroup(app_commands.Group):
    def __init__(self, data_dir: str):
        super().__init__(name="anime", description="Anime/animation awards (official/trusted links)")
        self._data_dir = data_dir

    @app_commands.command(name="awards", description="List prestigious anime/animation awards (official/trusted links)")
    @app_commands.describe(region="Optional region filter (japan/international)", kind="Optional kind filter (industry/festival)")
    async def awards(self, interaction: discord.Interaction, region: Optional[str] = None, kind: Optional[str] = None):
        region_n = (region or "").strip().lower() or None
        kind_n = (kind or "").strip().lower() or None

        awards = _load_awards(self._data_dir)

        def ok(a: Dict[str, Any]) -> bool:
            if region_n and str(a.get("region") or "").lower() != region_n:
                return False
            if kind_n and str(a.get("kind") or "").lower() != kind_n:
                return False
            return True

        picks = [a for a in awards if ok(a)]
        picks.sort(key=lambda x: (int(x.get("since") or 9999), str(x.get("name") or "")))

        title = "/anime awards"
        f = []
        if region_n:
            f.append(f"region:{region_n}")
        if kind_n:
            f.append(f"kind:{kind_n}")
        if f:
            title += " (" + ", ".join(f) + ")"

        embed = discord.Embed(title=title, color=0x2F3136)
        if not picks:
            embed.description = "No awards matched your filters. Try removing region/kind."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        lines: List[str] = []
        for a in picks[:12]:
            name = a.get("name")
            url = a.get("url")
            since = a.get("since")
            organizer = a.get("organizer")
            note = (a.get("note") or "").strip()
            meta = []
            if since:
                meta.append(f"since {since}")
            if organizer:
                meta.append(str(organizer))
            if a.get("region"):
                meta.append(str(a.get("region")))
            if a.get("kind"):
                meta.append(str(a.get("kind")))
            meta_txt = " — ".join(meta)
            if note:
                lines.append(f"• **{name}**\n  {note}\n  {url}\n  _{meta_txt}_")
            else:
                lines.append(f"• **{name}**\n  {url}\n  _{meta_txt}_")

        embed.description = "\n\n".join(lines)[:4096]
        embed.set_footer(text="Official/trusted links only.")
        await interaction.response.send_message(embed=embed)



async def register_anime_awards(bot: discord.Client, data_dir: str) -> None:
    """Register /anime awards commands and sync the app command tree."""
    bot.tree.add_command(AnimeGroup(data_dir))
    try:
        await bot.tree.sync()
    except Exception:
        # Safe fallback: syncing can fail temporarily during reconnects.
        pass

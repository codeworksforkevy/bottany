import os
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import discord
from discord import app_commands

logger = logging.getLogger(__name__)

BASE_GUILD_ID = 1446560723122520207

SOURCES_FILENAME = "theory_sources_registry.json"
QUOTES_FILENAME = "theory_quotes_registry.json"


def _load_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _norm(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s2 = str(s).strip()
    return s2 if s2 else None


def _to_lower(s: Optional[str]) -> Optional[str]:
    s2 = _norm(s)
    return s2.lower() if s2 else None


TOPIC_ALIASES = {
    "sim": "simulation",
    "simulation_theory": "simulation",
    "simulation hypothesis": "simulation",
    "sim hypothesis": "simulation",
    "simhyp": "simulation",
    "game": "game_theory",
    "games": "game_theory",
    "gt": "game_theory",
}


def _norm_topic(topic: Optional[str]) -> Optional[str]:
    t = _to_lower(topic)
    if not t:
        return None
    return TOPIC_ALIASES.get(t, t)


def _load_registries(data_dir: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    sources_path = os.path.join(data_dir, SOURCES_FILENAME)
    quotes_path = os.path.join(data_dir, QUOTES_FILENAME)
    sources_obj = _load_json(sources_path, {"sources": []})
    quotes_obj = _load_json(quotes_path, {"quotes": []})
    return sources_obj.get("sources", []), quotes_obj.get("quotes", [])


class TheoryGroup(app_commands.Group):
    def __init__(self, data_dir: str):
        super().__init__(
            name="theory",
            description="Academic explainers and curated quotes"
        )
        self._data_dir = data_dir

    @app_commands.command(
        name="simulation",
        description="Explain simulation theory using academic sources"
    )
    async def simulation(self, interaction: discord.Interaction):
        sources, _ = _load_registries(self._data_dir)

        embed = discord.Embed(
            title="Simulation theory (academic overview)",
            description="Curated overview using official/academic registries.",
            color=0x2F3136
        )

        embed.add_field(
            name="Core idea",
            value="The simulation hypothesis suggests reality may be an advanced computational simulation.",
            inline=False
        )

        if sources:
            lines = []
            for s in sources[:6]:
                title = s.get("title", "(untitled)")
                url = s.get("url", "")
                lines.append(f"• **{title}**\n{url}")

            embed.add_field(
                name="Sources",
                value="\n".join(lines)[:1024],
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="quotes",
        description="Curated theory quotes"
    )
    async def quotes(self, interaction: discord.Interaction):
        _, quotes = _load_registries(self._data_dir)

        if not quotes:
            await interaction.response.send_message(
                "No quotes found.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="Theory Quotes",
            description="Short curated quotes.",
            color=0x2F3136
        )

        for q in quotes[:6]:
            text = q.get("quote", "")
            author = q.get("author", "Unknown")
            embed.add_field(
                name=author,
                value=f"“{text}”"[:1024],
                inline=False
            )

        await interaction.response.send_message(embed=embed)


async def register(bot: discord.Client, data_dir: str) -> None:

    guild = discord.Object(id=BASE_GUILD_ID)

    if getattr(bot, "_theory_registered", False):
        return

    group = TheoryGroup(data_dir)

    bot.tree.add_command(group, guild=guild)

    bot._theory_registered = True
    logger.info("Registered /theory (guild-only)")

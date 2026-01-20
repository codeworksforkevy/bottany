import os
import json
import random
from typing import Any, Dict, List, Optional

import discord
from discord import app_commands

SOURCES_FILENAME = "theory_sources_registry.json"
QUOTES_FILENAME = "theory_quotes_registry.json"


def _load_json(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _norm_topic(topic: Optional[str]) -> str:
    t = (topic or "").strip().lower()
    if t in {"sim", "simulation", "simulation_theory", "simulation_hypothesis"}:
        return "simulation"
    if t in {"game", "game_theory", "gametheory"}:
        return "game"
    return t


def _pick_quotes(quotes: List[Dict[str, Any]], topic: str, author: Optional[str], k: int = 3) -> List[Dict[str, Any]]:
    a = (author or "").strip().lower()
    filt = []
    for q in quotes:
        if _norm_topic(q.get("topic")) != topic:
            continue
        if a and a not in str(q.get("author", "")).lower():
            continue
        filt.append(q)
    if not filt:
        return []
    random.shuffle(filt)
    return filt[:k]


class TheoryGroup(app_commands.Group):
    def __init__(self, data_dir: str):
        super().__init__(name="theory", description="Academic explainers and primary-source quotes")
        self._data_dir = data_dir

    @app_commands.command(name="simulation", description="Explain the simulation argument with academic pointers")
    @app_commands.describe(focus="Optional: argument | epistemology | ethics")
    async def simulation(self, interaction: discord.Interaction, focus: Optional[str] = None):
        focus_n = (focus or "").strip().lower()
        if focus_n not in {"", "argument", "epistemology", "ethics"}:
            focus_n = ""

        parts: List[str] = []
        parts.append("Simulation argument (high-level):")
        parts.append("- The thesis is not that we are certainly simulated; it is a disjunction-style argument under explicit assumptions.")
        parts.append("- Common framing: (1) civilizations rarely reach posthuman compute, OR (2) they reach it but rarely run ancestor simulations, OR (3) we are almost certainly in a simulation.")
        if focus_n == "epistemology":
            parts.append("\nEpistemology: what could count as evidence, how credences should update, and what observation means under possible constraints.")
        elif focus_n == "ethics":
            parts.append("\nEthics: moral status of simulated agents and obligations of creators/participants.")

        embed = discord.Embed(title="Theory - Simulation", description="\n".join(parts)[:4096])

        reg = _load_json(os.path.join(self._data_dir, SOURCES_FILENAME))
        sources = reg.get("sources", []) if isinstance(reg.get("sources"), list) else []
        sim_sources = []
        for s in sources:
            topics = [str(x).strip().lower() for x in (s.get("topics") or [])]
            if "simulation" in topics:
                sim_sources.append(s)

        if sim_sources:
            lines = []
            for s in sim_sources[:6]:
                name = s.get("name") or s.get("title") or "Source"
                year = s.get("year")
                url = s.get("url") or ""
                tag = f" ({year})" if year else ""
                if url:
                    lines.append(f"- {name}{tag}: {url}")
                else:
                    lines.append(f"- {name}{tag}")
            embed.add_field(name="Primary / academic sources", value="\n".join(lines)[:1024], inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="quotes", description="Primary-source quotes (paper/lecture) for simulation or game theory")
    @app_commands.describe(topic="simulation|game", author="Optional author filter")
    async def quotes(self, interaction: discord.Interaction, topic: str, author: Optional[str] = None):
        topic_n = _norm_topic(topic)
        if topic_n not in {"simulation", "game"}:
            await interaction.response.send_message("Topic must be: simulation or game.", ephemeral=True)
            return

        reg = _load_json(os.path.join(self._data_dir, QUOTES_FILENAME))
        quotes = reg.get("quotes", []) if isinstance(reg.get("quotes"), list) else []
        picks = _pick_quotes(quotes, topic_n, author, k=3)
        if not picks:
            await interaction.response.send_message("No quotes matched that filter.", ephemeral=True)
            return

        embed = discord.Embed(title=f"Theory - Quotes ({topic_n})")
        for q in picks:
            author_s = q.get("author", "(unknown)")
            work = q.get("work", "")
            year = q.get("year")
            url = q.get("source_url", "")
            quote = (q.get("quote") or "").strip()
            meta = " - ".join([x for x in [work, str(year) if year else ""] if x])
            if meta:
                name = f"{author_s} - {meta}"
            else:
                name = f"{author_s}"
            value = quote
            if url:
                value += f"\nSource: {url}"
            embed.add_field(name=name[:256], value=value[:1024], inline=False)

        await interaction.response.send_message(embed=embed)


async def register_theory(bot: discord.Client, data_dir: str) -> None:
    # Avoid duplicate registration on reconnect
    existing = [c.name for c in bot.tree.get_commands()]
    if "theory" in existing:
        return
    bot.tree.add_command(TheoryGroup(data_dir))
    try:
        await bot.tree.sync()
    except Exception:
        # Sync may fail on global rate limits; commands can still appear later
        pass

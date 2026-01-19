import os
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import discord
from discord import app_commands

logger = logging.getLogger(__name__)

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


def _score_source(src: Dict[str, Any], focus: Optional[str]) -> int:
    score = 0
    if src.get("source_type") == "official":
        score += 30
    elif src.get("source_type") == "academic_reference":
        score += 25
    elif src.get("source_type") == "repository":
        score += 20
    else:
        score += 10

    if focus:
        tags = [str(x).lower() for x in (src.get("tags") or [])]
        if focus.lower() in tags:
            score += 20

    # Prefer primary/seminal works
    if src.get("is_seminal"):
        score += 10

    return score


def _format_source_line(src: Dict[str, Any]) -> str:
    title = src.get("title") or "(untitled)"
    url = src.get("url") or ""
    year = src.get("year")
    author = src.get("author")
    parts = []
    if author:
        parts.append(str(author))
    if year:
        parts.append(str(year))
    meta = " · ".join(parts)
    if meta:
        return f"• **{title}** ({meta})\n  {url}"
    return f"• **{title}**\n  {url}"


def _pick_sources(sources: List[Dict[str, Any]], focus: Optional[str], limit: int = 6) -> List[Dict[str, Any]]:
    scored = [( _score_source(s, focus), s) for s in sources]
    scored.sort(key=lambda x: x[0], reverse=True)

    picked: List[Dict[str, Any]] = []
    used_domains: set = set()

    for _, s in scored:
        if len(picked) >= limit:
            break
        url = (s.get("url") or "").strip()
        dom = ""
        try:
            dom = url.split("/")[2].lower() if url.startswith("http") else ""
        except Exception:
            dom = ""

        # Diversity: avoid more than 2 from same domain
        if dom and sum(1 for p in picked if (p.get("url") or "").find(dom) != -1) >= 2:
            continue

        picked.append(s)
        if dom:
            used_domains.add(dom)

    return picked


def _load_registries(data_dir: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    sources_path = os.path.join(data_dir, SOURCES_FILENAME)
    quotes_path = os.path.join(data_dir, QUOTES_FILENAME)
    sources_obj = _load_json(sources_path, {"sources": []})
    quotes_obj = _load_json(quotes_path, {"quotes": []})
    return sources_obj.get("sources", []), quotes_obj.get("quotes", [])


class TheoryGroup(app_commands.Group):
    def __init__(self, data_dir: str):
        super().__init__(name="theory", description="Academic explainers and curated quotes (simulation theory, game theory)")
        self._data_dir = data_dir

    @app_commands.command(name="simulation", description="Explain simulation theory using academic sources")
    @app_commands.describe(focus="Optional: simulation (default), science, mind")
    async def simulation(self, interaction: discord.Interaction, focus: Optional[str] = "simulation"):
        sources, _quotes = _load_registries(self._data_dir)
        focus_n = _norm_topic(focus) or "simulation"

        # Build explanation skeleton
        embed = discord.Embed(
            title="Simulation theory (academic overview)",
            description=(
                "A curated, citation-first overview. Use `focus` to switch lenses.\n\n"
                "**Important note:** 'simulation theory' is used in multiple literatures.\n"
                "This command focuses on the *simulation hypothesis* (philosophy) unless you choose `science` or `mind`."
            ),
            color=0x2F3136,
        )

        if focus_n == "simulation":
            embed.add_field(
                name="Core idea",
                value=(
                    "The simulation hypothesis suggests that what we experience as reality might be an artificial simulation run by an advanced civilization.\n"
                    "In academic philosophy, the best-known formal argument is Bostrom's trilemma, which claims at least one of three propositions must hold."
                )[:1024],
                inline=False,
            )
            embed.add_field(
                name="What it does and does not claim",
                value=(
                    "It is not a scientific confirmation claim; it is primarily an argument about conditional probabilities, future civilizations, and observer-selection reasoning.\n"
                    "Empirical tests are controversial and generally not decisive." 
                )[:1024],
                inline=False,
            )
        elif focus_n == "science":
            embed.title = "Computer simulation in science (academic overview)"
            embed.description = "A curated, citation-first overview of computer simulation as a scientific method."
            embed.add_field(
                name="Core idea",
                value=(
                    "In philosophy of science, 'simulation' typically means computational exploration of a model to study system behavior.\n"
                    "Key issues include validation, idealization, error, and the epistemic status of simulation results."
                )[:1024],
                inline=False,
            )
        elif focus_n == "mind":
            embed.title = "Mental simulation theory (academic overview)"
            embed.description = "A curated, citation-first overview of simulation-based accounts in philosophy of mind/cognitive science."
            embed.add_field(
                name="Core idea",
                value=(
                    "Simulation theory in mindreading argues that we understand others by simulating their mental states in ourselves.\n"
                    "It is distinct from the simulation hypothesis about reality."
                )[:1024],
                inline=False,
            )
        else:
            embed.add_field(
                name="Focus not recognized",
                value="Valid values: simulation (default), science, mind.",
                inline=False,
            )

        # Select relevant sources
        picked = _pick_sources(sources, focus_n, limit=6)
        if picked:
            embed.add_field(
                name="Academic/official sources",
                value=("\n".join(_format_source_line(s) for s in picked))[:1024],
                inline=False,
            )

        embed.set_footer(text="Bottany: curated registries (no scraping). Use /theory quotes for short quotations + provenance.")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="quotes", description="Curated quotes (simulation theory and game theory) with provenance")
    @app_commands.describe(topic="simulation or game_theory", author="Optional: filter by author")
    async def quotes(self, interaction: discord.Interaction, topic: str, author: Optional[str] = None):
        _sources, quotes = _load_registries(self._data_dir)
        topic_n = _norm_topic(topic)
        if topic_n not in ("simulation", "game_theory"):
            await interaction.response.send_message("Topic must be `simulation` or `game_theory`.", ephemeral=True)
            return

        auth_f = _to_lower(author)
        pool = []
        for q in quotes:
            if _to_lower(q.get("topic")) != topic_n:
                continue
            if auth_f and auth_f not in _to_lower(q.get("author") or ""):
                continue
            pool.append(q)

        if not pool:
            await interaction.response.send_message("No quotes found for that filter.", ephemeral=True)
            return

        # Limit to avoid spam
        pool = pool[:8]

        title = "Simulation theory quotes" if topic_n == "simulation" else "Game theory quotes"
        embed = discord.Embed(title=title, description="Short quotes with sources. (Quotes are intentionally brief.)", color=0x2F3136)

        for q in pool:
            text = (q.get("quote") or "").strip()
            auth = q.get("author") or "Unknown"
            src = q.get("source_title") or "Source"
            url = q.get("source_url") or ""
            year = q.get("year")
            meta = f"— {auth}"
            if year:
                meta += f" ({year})"
            value = f"“{text}”\n{meta}\n{src}\n{url}"
            embed.add_field(name=q.get("id") or "quote", value=value[:1024], inline=False)

        await interaction.response.send_message(embed=embed)


async def register_theory(bot: discord.Client, data_dir: str) -> None:
    """Register /theory command group."""
    group = TheoryGroup(data_dir)

    # Avoid duplicate registration on reconnect
    existing = [c.name for c in bot.tree.get_commands()]
    if group.name in existing:
        raise RuntimeError("already registered")

    bot.tree.add_command(group)
    logger.info("Registered /theory command group")
PY
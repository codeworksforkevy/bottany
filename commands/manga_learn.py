import os
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import discord
from discord import app_commands


REGISTRY_FILENAME = "manga_drawing_sources_registry.json"


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in items:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def _match_any(needles: List[str], hay: List[str]) -> bool:
    if not needles:
        return True
    hs = {_norm(x) for x in hay if x}
    for n in needles:
        if _norm(n) in hs:
            return True
    return False


def _extract_tools(it: Dict[str, Any]) -> List[str]:
    """Return normalized tool identifiers for an item.

    Supports both the preferred `tools` list and legacy fields like `tool_focus`.
    """
    tools: List[str] = []
    tools.extend(list(it.get("tools", []) or []))
    tf = it.get("tool_focus") or it.get("tool") or ""
    if tf:
        tools.append(str(tf))
    prov = it.get("provider") or ""
    if prov:
        tools.append(str(prov))

    # Normalize into a small set of predictable tokens
    normed: List[str] = []
    for t in tools:
        t_n = _norm(str(t))
        if not t_n:
            continue
        if "clip" in t_n or "csp" in t_n:
            normed.append("clip-studio")
        elif "wacom" in t_n:
            normed.append("wacom")
        elif "medibang" in t_n or "jump paint" in t_n:
            normed.append("medibang")
        elif "procreate" in t_n:
            normed.append("procreate")
        elif "too" in t_n:
            normed.append("too")
        else:
            normed.append(t_n)

    return _dedupe_keep_order(normed)


def _norm_mode(mode: str) -> str:
    m = _norm(mode)
    if m in ("both", "either"):
        return "hybrid"
    return m


def _pick(items: List[Dict[str, Any]], limit: int = 8) -> List[Dict[str, Any]]:
    # stable sort: prioritize official/curated labels first, then shorter titles
    def score(it: Dict[str, Any]) -> Tuple[int, int]:
        src = _norm(it.get("source_type", ""))
        # 0 is best
        pri = 2
        if src in ("official", "official_platform"):
            pri = 0
        elif src in ("trusted_platform", "curated"):
            pri = 1
        return (pri, len(it.get("title", "")))

    items2 = sorted(items, key=score)
    return items2[:limit]


def _fmt_entry(it: Dict[str, Any]) -> str:
    title = it.get("title", "(untitled)")
    url = it.get("url") or it.get("official_url", "")
    summary = it.get("summary", "").strip()
    level = ", ".join(it.get("levels", []) or [])
    mode = ", ".join(it.get("modes", []) or [])
    topics = ", ".join(it.get("topics", []) or [])
    tags = " | ".join([x for x in [level, mode, topics] if x])

    line1 = f"[{title}]({url})" if url else title
    if summary:
        line2 = f"{summary}"
        return f"• {line1}\n  {line2}\n  _{tags}_" if tags else f"• {line1}\n  {line2}"
    return f"• {line1}\n  _{tags}_" if tags else f"• {line1}"


async def register_manga_learn(bot, data_dir: str) -> None:
    """Register /manga commands.

    Design goals:
    - Link-first: we do NOT scrape paywalled/tutorial content. We surface official/trusted links.
    - Filterable: topic / level / mode / tool.
    """

    reg_path = os.path.join(data_dir, REGISTRY_FILENAME)
    reg: Dict[str, Any] = {}
    try:
        reg = _load_json(reg_path)
    except Exception as e:
        # Keep the module non-fatal; expose a helpful error at runtime.
        reg = {"error": f"Could not load {REGISTRY_FILENAME}: {e}"}

    sources: List[Dict[str, Any]] = list(reg.get("sources", []) or [])

    # Precompute filters
    all_topics = _dedupe_keep_order(
        sorted({t for s in sources for t in (s.get("topics", []) or []) if t})
    )
    all_levels = _dedupe_keep_order(
        sorted({t for s in sources for t in (s.get("levels", []) or []) if t})
    )
    all_modes = _dedupe_keep_order(
        sorted({t for s in sources for t in (s.get("modes", []) or []) if t})
    )
    all_tools = _dedupe_keep_order(
        sorted({t for s in sources for t in _extract_tools(s) if t})
    )

    manga_group = app_commands.Group(
        name="manga",
        description="Manga learning hub (official/trusted links; filterable).",
    )

    @manga_group.command(name="learn", description="Find manga drawing learning resources (filterable).")
    @app_commands.describe(
        topic="workflow | composition | perspective | values | atmospheric_perspective | architecture | props | materials | backgrounds | environments | paneling | anatomy | lineart | screentone | lighting | lettering | tools",
        level="Beginner | Intermediate | Advanced",
        mode="Digital | Traditional | Hybrid",
        tool="Optional tool focus (e.g., clip-studio, wacom, medibang)",
    )
    async def manga_learn(
        interaction: discord.Interaction,
        topic: Optional[str] = None,
        level: Optional[str] = None,
        mode: Optional[str] = None,
        tool: Optional[str] = None,
    ):
        # Defensive: registry load errors
        if reg.get("error"):
            await interaction.response.send_message(
                f"Manga registry is not available. {reg['error']}",
                ephemeral=True,
            )
            return

        topic_n = _norm(topic) if topic else ""
        level_n = _norm(level) if level else ""
        mode_n = _norm_mode(mode) if mode else ""
        tool_n = _norm(tool) if tool else ""

        # Filter
        filtered: List[Dict[str, Any]] = []
        for s in sources:
            if topic_n and topic_n not in {_norm(x) for x in (s.get("topics", []) or [])}:
                continue
            if level_n and level_n not in {_norm(x) for x in (s.get("levels", []) or [])}:
                continue
            if mode_n and mode_n not in {_norm(x) for x in (s.get("modes", []) or [])}:
                continue
            if tool_n and tool_n not in {_norm(x) for x in _extract_tools(s)}:
                continue
            filtered.append(s)

        picked = _pick(filtered, limit=8)

        title_parts = ["Manga Learn"]
        if topic:
            title_parts.append(f"topic:{topic}")
        if level:
            title_parts.append(f"level:{level}")
        if mode:
            title_parts.append(f"mode:{mode}")
        if tool:
            title_parts.append(f"tool:{tool}")
        title = " — ".join(title_parts)

        embed = discord.Embed(title=title)
        if not filtered:
            embed.description = (
                "No matches for those filters. Try loosening filters or use **/manga filters** to see supported values."
            )
        else:
            embed.description = "\n\n".join(_fmt_entry(x) for x in picked)

        # If the user is exploring scene/background topics, show a mini-path
        if topic_n in ("composition", "perspective", "values", "atmospheric_perspective", "materials", "props", "architecture", "backgrounds", "environments", "lighting"):
            embed.add_field(
                name="Scene & Background Mini-Path",
                value=(
                    "1) composition (thumbnails) → 2) perspective → 3) values → 4) atmospheric_perspective\n"
                    "5) architecture/props → 6) materials/textures → 7) backgrounds/environments → 8) lighting/finishing\n\n"
                    "Tip: use **/manga path** for the full sequence, or refine with filters like `topic:perspective` and `level:Beginner`."
                ),
                inline=False,
            )

        embed.add_field(
            name="How to use",
            value=(
                "• **/manga learn** (no filters) shows a curated starter set\n"
                "• Add filters: `topic:lineart` `level:Beginner` `mode:Digital` `tool:clip-studio`\n"
                "• Use **/manga filters** to see available values\n"
                "• Want a structured sequence? Use **/manga path**"
            ),
            inline=False,
        )

        embed.set_footer(text="Link-first policy: the bot surfaces official/trusted tutorials and entry points; it does not copy/paste paywalled content.")

        await interaction.response.send_message(embed=embed)

    @manga_group.command(name="filters", description="Show available filters for /manga learn.")
    async def manga_filters(interaction: discord.Interaction):
        if reg.get("error"):
            await interaction.response.send_message(
                f"Manga registry is not available. {reg['error']}",
                ephemeral=True,
            )
            return

        embed = discord.Embed(title="/manga learn — available filters")
        embed.add_field(name="Topics", value=", ".join(all_topics) if all_topics else "(none)", inline=False)
        embed.add_field(name="Levels", value=", ".join(all_levels) if all_levels else "(none)", inline=False)
        embed.add_field(name="Modes", value=", ".join(all_modes) if all_modes else "(none)", inline=False)
        embed.add_field(name="Tools", value=", ".join(all_tools) if all_tools else "(none)", inline=False)
        embed.set_footer(text=f"Registry: {REGISTRY_FILENAME} | Updated: {reg.get('generated_utc','unknown')}")
        await interaction.response.send_message(embed=embed)

    @manga_group.command(name="topics", description="Alias for /manga filters (shows available filter values).")
    async def manga_topics(interaction: discord.Interaction):
        await manga_filters(interaction)

    @manga_group.command(name="path", description="Get a recommended step-by-step learning path (with links).")
    @app_commands.describe(
        level="Beginner | Intermediate | Advanced",
        mode="Digital | Traditional | Hybrid",
        tool="Optional tool focus (e.g., clip-studio, wacom, medibang)",
    )
    async def manga_path(
        interaction: discord.Interaction,
        level: Optional[str] = None,
        mode: Optional[str] = None,
        tool: Optional[str] = None,
    ):
        if reg.get("error"):
            await interaction.response.send_message(
                f"Manga registry is not available. {reg['error']}",
                ephemeral=True,
            )
            return

        level_n = _norm(level) if level else ""
        mode_n = _norm_mode(mode) if mode else ""
        tool_n = _norm(tool) if tool else ""

        # A conservative, generally applicable progression.
        # Each step is mapped to one or more registry topics.
        # Expanded: explicitly covers backgrounds & perspective (scene-setting).
        steps: List[Tuple[str, List[str], str]] = [
            (
                "Step 1 — Workflow & pages (planning → rough)",
                ["workflow"],
                "Goal: understand the end-to-end pipeline and page setup.",
            ),
            (
                "Step 2 — Composition & thumbnails",
                ["composition", "workflow"],
                "Goal: plan focal points, readability, and shot choices.",
            ),
            (
                "Step 3 — Perspective basics (1–3 point)",
                ["perspective"],
                "Goal: consistent depth so backgrounds feel believable.",
            ),
            (
                "Step 4 — Values (readability in black & white)",
                ["values"],
                "Goal: control contrast and depth before screentones/shading.",
            ),
            (
                "Step 5 — Atmospheric perspective (depth with air & haze)",
                ["atmospheric_perspective"],
                "Goal: push distance with reduced contrast/detail and lighter values.",
            ),
            (
                "Step 6 — Materials & texture (surfaces, fabrics, finishes)",
                ["materials"],
                "Goal: make environments feel tactile; keep textures readable.",
            ),
            (
                "Step 7 — Props & objects (vehicles, furniture, hard-surface)",
                ["props"],
                "Goal: draw repeatable objects that sell the scene.",
            ),
            (
                "Step 8 — Architecture (buildings, interiors)",
                ["architecture", "backgrounds"],
                "Goal: construct believable spaces with perspective tools.",
            ),
            (
                "Step 9 — Backgrounds & environments",
                ["backgrounds", "environments"],
                "Goal: place characters in a scene and support storytelling.",
            ),
            (
                "Step 10 — Paneling & page flow",
                ["paneling"],
                "Goal: readable layouts, pacing, and eye flow.",
            ),
            (
                "Step 11 — Anatomy & figure basics",
                ["anatomy"],
                "Goal: believable bodies/poses for characters.",
            ),
            (
                "Step 12 — Lineart & inking",
                ["lineart"],
                "Goal: confident lines and clean inks.",
            ),
            (
                "Step 13 — Screentone, fills & finishing",
                ["screentone", "lighting"],
                "Goal: value control, shading, and manga-style finishing.",
            ),
            (
                "Step 14 — Lettering & balloons",
                ["lettering"],
                "Goal: readable text, balloons, and sound effects.",
            ),
        ]

        embed = discord.Embed(title="Manga Learning Path")
        if level:
            embed.title += f" — level:{level}"
        if mode:
            embed.title += f" — mode:{mode}"
        if tool:
            embed.title += f" — tool:{tool}"

        for step_title, step_topics, goal in steps:
            # Filter candidates by step topic(s) and user filters
            candidates: List[Dict[str, Any]] = []
            for s in sources:
                if not _match_any(step_topics, s.get("topics", []) or []):
                    continue
                if level_n and level_n not in {_norm(x) for x in (s.get("levels", []) or [])}:
                    continue
                if mode_n and mode_n not in {_norm(x) for x in (s.get("modes", []) or [])}:
                    continue
                if tool_n and tool_n not in {_norm(x) for x in _extract_tools(s)}:
                    continue
                candidates.append(s)

            picks = _pick(candidates, limit=2)
            if picks:
                value = f"{goal}\n\n" + "\n\n".join(_fmt_entry(x) for x in picks)
            else:
                value = f"{goal}\n\n_No matching resources for these filters._"

            embed.add_field(name=step_title, value=value, inline=False)

        embed.set_footer(
            text=(
                "Tip: use /manga learn with topic filters (e.g., topic:lineart) to expand each step. "
                "Link-first policy: short summaries + official/trusted links."
            )
        )

        await interaction.response.send_message(embed=embed)

    # Register group once
    bot.tree.add_command(manga_group)

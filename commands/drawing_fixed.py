# commands/drawing.py
from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import discord
from discord import app_commands
from discord.ext import commands


def _load_json(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _safe_pick(items: List[Dict[str, Any]], seed_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if not items:
        return None
    # Deterministic-ish per call key if desired; otherwise random.
    if seed_key:
        rnd = random.Random(seed_key)
        return rnd.choice(items)
    return random.choice(items)


def _format_refs(refs: List[str]) -> str:
    if not refs:
        return "References: (curated registry)"
    # Keep it short: up to 2 refs in output
    slim = refs[:2]
    return "References: " + "; ".join(slim)


def _format_bullets(lines: List[str], max_items: int = 3) -> str:
    use = [ln for ln in lines if ln][:max_items]
    if not use:
        return ""
    return "\n".join([f"• {ln}" for ln in use])


@dataclass
class DrawingRegistry:
    techniques: List[Dict[str, Any]]
    tools: List[Dict[str, Any]]
    animation_concepts: List[Dict[str, Any]]
    academic_topics: List[Dict[str, Any]]
    meta: Dict[str, Any]

    @classmethod
    def from_file(cls, path: str) -> "DrawingRegistry":
        obj = _load_json(path)
        return cls(
            techniques=obj.get("techniques", []),
            tools=obj.get("tools", []),
            animation_concepts=obj.get("animation_concepts", []),
            academic_topics=obj.get("academic_topics", []),
            meta=obj.get("meta", {}),
        )


class DrawingCog(commands.Cog):
    def __init__(self, bot: commands.Bot, data_dir: str):
        self.bot = bot
        self.data_dir = data_dir
        self.registry_path = os.path.join(self.data_dir, "drawing_registry.json")
        self.reg = DrawingRegistry.from_file(self.registry_path)

    drawing_group = app_commands.Group(
        name="drawing",
        description="Academic drawing & animation fundamentals (curated, reference-based).",
    )

    @drawing_group.command(name="technique", description="Get one curated drawing technique (definition, usage, references).")
    @app_commands.describe(topic="Optional filter keyword (e.g., shading, perspective, gesture)")
    async def technique(self, interaction: discord.Interaction, topic: Optional[str] = None):
        items = self.reg.techniques

        if topic:
            t = topic.lower().strip()
            items = [
                it for it in items
                if t in (it.get("name", "").lower())
                or t in (it.get("category", "").lower())
                or any(t in s.lower() for s in it.get("use_cases", []))
            ]

        pick = _safe_pick(items)
        if not pick:
            await interaction.response.send_message(
                "No matching technique found in the curated registry. Try a different keyword.",
                ephemeral=True,
            )
            return

        name = pick.get("name", "Technique")
        cat = pick.get("category", "Drawing")
        definition = pick.get("definition", "")
        use_cases = pick.get("use_cases", [])
        tips = pick.get("tips", [])
        refs = pick.get("references", [])

        msg = (
            f"**{name}**  _(Category: {cat})_\n"
            f"{definition}\n\n"
            f"**Where it’s used**\n{_format_bullets(use_cases)}\n\n"
            f"**Practice tips**\n{_format_bullets(tips)}\n\n"
            f"{_format_refs(refs)}"
        )

        await interaction.response.send_message(msg)

    @drawing_group.command(name="tool", description="Get one curated drawing tool/material (what it is, why it’s used, references).")
    @app_commands.describe(category="Optional filter keyword (e.g., paper, charcoal, ink, eraser)")
    async def tool(self, interaction: discord.Interaction, category: Optional[str] = None):
        items = self.reg.tools

        if category:
            c = category.lower().strip()
            items = [
                it for it in items
                if c in (it.get("name", "").lower())
                or c in (it.get("category", "").lower())
                or any(c in s.lower() for s in it.get("best_for", []))
            ]

        pick = _safe_pick(items)
        if not pick:
            await interaction.response.send_message(
                "No matching tool found in the curated registry. Try a different keyword.",
                ephemeral=True,
            )
            return

        name = pick.get("name", "Tool")
        cat = pick.get("category", "Materials")
        desc = pick.get("description", "")
        best_for = pick.get("best_for", [])
        notes = pick.get("notes", [])
        refs = pick.get("references", [])

        msg = (
            f"**{name}**  _(Category: {cat})_\n"
            f"{desc}\n\n"
            f"**Best for**\n{_format_bullets(best_for)}\n\n"
            f"**Notes**\n{_format_bullets(notes)}\n\n"
            f"{_format_refs(refs)}"
        )
        await interaction.response.send_message(msg)

    @drawing_group.command(name="animation", description="Get one animation/drawing-for-animation concept (definition, use, references).")
    @app_commands.describe(topic="Optional filter keyword (e.g., timing, arcs, anticipation)")
    async def animation(self, interaction: discord.Interaction, topic: Optional[str] = None):
        items = self.reg.animation_concepts

        if topic:
            t = topic.lower().strip()
            items = [
                it for it in items
                if t in (it.get("name", "").lower())
                or t in (it.get("category", "").lower())
                or any(t in s.lower() for s in it.get("use_cases", []))
            ]

        pick = _safe_pick(items)
        if not pick:
            await interaction.response.send_message(
                "No matching animation concept found in the curated registry. Try a different keyword.",
                ephemeral=True,
            )
            return

        name = pick.get("name", "Animation concept")
        cat = pick.get("category", "Animation")
        definition = pick.get("definition", "")
        use_cases = pick.get("use_cases", [])
        tips = pick.get("tips", [])
        refs = pick.get("references", [])

        msg = (
            f"**{name}**  _(Category: {cat})_\n"
            f"{definition}\n\n"
            f"**Where it’s used**\n{_format_bullets(use_cases)}\n\n"
            f"**Practical tips**\n{_format_bullets(tips)}\n\n"
            f"{_format_refs(refs)}"
        )
        await interaction.response.send_message(msg)

    @drawing_group.command(name="academic", description="Get one academic topic/drill set (observation, value, perspective).")
    @app_commands.describe(topic="Optional filter keyword (e.g., proportion, value, perspective)")
    async def academic(self, interaction: discord.Interaction, topic: Optional[str] = None):
        items = self.reg.academic_topics

        if topic:
            t = topic.lower().strip()
            items = [
                it for it in items
                if t in (it.get("name", "").lower())
                or t in (it.get("category", "").lower())
                or t in (it.get("summary", "").lower())
            ]

        pick = _safe_pick(items)
        if not pick:
            await interaction.response.send_message(
                "No matching academic topic found in the curated registry. Try a different keyword.",
                ephemeral=True,
            )
            return

        name = pick.get("name", "Academic topic")
        cat = pick.get("category", "Academic drawing")
        summary = pick.get("summary", "")
        drills = pick.get("drills", [])
        refs = pick.get("references", [])

        msg = (
            f"**{name}**  _(Category: {cat})_\n"
            f"{summary}\n\n"
            f"**Suggested drills**\n{_format_bullets(drills)}\n\n"
            f"{_format_refs(refs)}"
        )
        await interaction.response.send_message(msg)


async def register_drawing(bot: commands.Bot, data_dir: str) -> None:
    """
    Minimal integration surface:
    - Adds a Cog
    - Registers the /drawing group to the bot's app command tree
    """
    cog = DrawingCog(bot, data_dir)
    await bot.add_cog(cog)

    # Attach the group once (avoid duplicate registration if reload patterns exist)
    try:
        bot.tree.add_command(cog.drawing_group)
    except Exception:
        # If already added, ignore
        pass

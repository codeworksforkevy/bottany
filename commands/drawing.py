# commands/drawing.py
from __future__ import annotations

import json
import os
import random
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import discord
from discord import app_commands
from discord.ext import commands


logger = logging.getLogger("bottany.drawing")


# -------------------------------------------------
# SAFE JSON LOADER
# -------------------------------------------------

def _load_json(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        logger.warning(f"[drawing] Registry not found: {path}")
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.exception(f"[drawing] Failed to load registry: {e}")
        return {}


# -------------------------------------------------
# UTILITIES
# -------------------------------------------------

def _safe_pick(items: List[Dict[str, Any]], seed_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if not items:
        return None

    if seed_key:
        rnd = random.Random(seed_key)
        return rnd.choice(items)

    return random.choice(items)


def _format_refs(refs: List[str]) -> str:
    if not refs:
        return "Curated internal registry"
    return "; ".join(refs[:2])


def _format_bullets(lines: List[str], max_items: int = 3) -> str:
    use = [ln for ln in lines if ln][:max_items]
    if not use:
        return "—"
    return "\n".join([f"• {ln}" for ln in use])


# -------------------------------------------------
# REGISTRY MODEL
# -------------------------------------------------

@dataclass
class DrawingRegistry:
    techniques: List[Dict[str, Any]]
    tools: List[Dict[str, Any]]
    animation_concepts: List[Dict[str, Any]]
    academic_topics: List[Dict[str, Any]]

    @classmethod
    def from_file(cls, path: str) -> "DrawingRegistry":
        obj = _load_json(path)
        return cls(
            techniques=obj.get("techniques", []),
            tools=obj.get("tools", []),
            animation_concepts=obj.get("animation_concepts", []),
            academic_topics=obj.get("academic_topics", []),
        )


# -------------------------------------------------
# COG
# -------------------------------------------------

class DrawingCog(commands.Cog):
    def __init__(self, bot: commands.Bot, data_dir: str):
        self.bot = bot
        self.registry_path = os.path.join(data_dir, "drawing_registry.json")
        self.reg = DrawingRegistry.from_file(self.registry_path)

    # -------------------------------------------------
    # GROUP
    # -------------------------------------------------

    drawing_group = app_commands.Group(
        name="drawing",
        description="Academic drawing & animation fundamentals.",
    )

    # -------------------------------------------------
    # TECHNIQUE
    # -------------------------------------------------

    @drawing_group.command(name="technique")
    @app_commands.describe(topic="Optional filter (shading, gesture, perspective)")
    async def technique(self, interaction: discord.Interaction, topic: Optional[str] = None):

        items = self.reg.techniques

        if topic:
            t = topic.lower().strip()
            items = [
                it for it in items
                if t in it.get("name", "").lower()
                or t in it.get("category", "").lower()
                or any(t in s.lower() for s in it.get("use_cases", []))
            ]

        pick = _safe_pick(items, seed_key=str(interaction.user.id))

        if not pick:
            await interaction.response.send_message(
                "No matching technique found.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=pick.get("name", "Technique"),
            description=pick.get("definition", "—"),
            color=discord.Color.blurple(),
        )

        embed.add_field(
            name="Category",
            value=pick.get("category", "Drawing"),
            inline=False,
        )

        embed.add_field(
            name="Where it’s used",
            value=_format_bullets(pick.get("use_cases", [])),
            inline=False,
        )

        embed.add_field(
            name="Practice tips",
            value=_format_bullets(pick.get("tips", [])),
            inline=False,
        )

        embed.set_footer(text=_format_refs(pick.get("references", [])))

        await interaction.response.send_message(embed=embed)

    # -------------------------------------------------
    # TOOL
    # -------------------------------------------------

    @drawing_group.command(name="tool")
    @app_commands.describe(category="Optional filter (ink, charcoal, paper)")
    async def tool(self, interaction: discord.Interaction, category: Optional[str] = None):

        items = self.reg.tools

        if category:
            c = category.lower().strip()
            items = [
                it for it in items
                if c in it.get("name", "").lower()
                or c in it.get("category", "").lower()
                or any(c in s.lower() for s in it.get("best_for", []))
            ]

        pick = _safe_pick(items, seed_key=str(interaction.user.id))

        if not pick:
            await interaction.response.send_message(
                "No matching tool found.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=pick.get("name", "Tool"),
            description=pick.get("description", "—"),
            color=discord.Color.green(),
        )

        embed.add_field(
            name="Best for",
            value=_format_bullets(pick.get("best_for", [])),
            inline=False,
        )

        embed.add_field(
            name="Notes",
            value=_format_bullets(pick.get("notes", [])),
            inline=False,
        )

        embed.set_footer(text=_format_refs(pick.get("references", [])))

        await interaction.response.send_message(embed=embed)

    # -------------------------------------------------
    # ANIMATION
    # -------------------------------------------------

    @drawing_group.command(name="animation")
    @app_commands.describe(topic="Optional filter (timing, arcs, anticipation)")
    async def animation(self, interaction: discord.Interaction, topic: Optional[str] = None):

        items = self.reg.animation_concepts

        if topic:
            t = topic.lower().strip()
            items = [
                it for it in items
                if t in it.get("name", "").lower()
                or t in it.get("category", "").lower()
                or any(t in s.lower() for s in it.get("use_cases", []))
            ]

        pick = _safe_pick(items, seed_key=str(interaction.user.id))

        if not pick:
            await interaction.response.send_message(
                "No matching animation concept found.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=pick.get("name", "Animation Concept"),
            description=pick.get("definition", "—"),
            color=discord.Color.orange(),
        )

        embed.add_field(
            name="Where it’s used",
            value=_format_bullets(pick.get("use_cases", [])),
            inline=False,
        )

        embed.add_field(
            name="Practical tips",
            value=_format_bullets(pick.get("tips", [])),
            inline=False,
        )

        embed.set_footer(text=_format_refs(pick.get("references", [])))

        await interaction.response.send_message(embed=embed)

    # -------------------------------------------------
    # ACADEMIC
    # -------------------------------------------------

    @drawing_group.command(name="academic")
    @app_commands.describe(topic="Optional filter (value, proportion, perspective)")
    async def academic(self, interaction: discord.Interaction, topic: Optional[str] = None):

        items = self.reg.academic_topics

        if topic:
            t = topic.lower().strip()
            items = [
                it for it in items
                if t in it.get("name", "").lower()
                or t in it.get("category", "").lower()
                or t in it.get("summary", "").lower()
            ]

        pick = _safe_pick(items, seed_key=str(interaction.user.id))

        if not pick:
            await interaction.response.send_message(
                "No matching academic topic found.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=pick.get("name", "Academic Topic"),
            description=pick.get("summary", "—"),
            color=discord.Color.purple(),
        )

        embed.add_field(
            name="Suggested drills",
            value=_format_bullets(pick.get("drills", [])),
            inline=False,
        )

        embed.set_footer(text=_format_refs(pick.get("references", [])))

        await interaction.response.send_message(embed=embed)


# -------------------------------------------------
# REGISTER FUNCTION (MAIN.PY SAFE)
# -------------------------------------------------

async def register_drawing(bot: commands.Bot, data_dir: str) -> None:
    cog = DrawingCog(bot, data_dir)
    await bot.add_cog(cog)

    # Avoid duplicate group registration
    if not bot.tree.get_command("drawing"):
        bot.tree.add_command(cog.drawing_group)

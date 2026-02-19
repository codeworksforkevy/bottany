
from __future__ import annotations

import json
import os
import random
import logging
from typing import Any, Dict, List, Optional

import discord
from discord import app_commands
from discord.ext import commands

logger = logging.getLogger("bottany.drawing")


# -------------------------------------------------
# UTILITIES
# -------------------------------------------------

def _load_json(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        logger.warning(f"[drawing] Registry not found: {path}")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _safe_pick(items: List[Dict[str, Any]], seed_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if not items:
        return None
    if seed_key:
        rnd = random.Random(seed_key)
        return rnd.choice(items)
    return random.choice(items)


def _format_bullets(lines: List[str]) -> str:
    if not lines:
        return "—"
    return "\n".join([f"• {ln}" for ln in lines])


# -------------------------------------------------
# COG
# -------------------------------------------------

class DrawingCog(commands.Cog):
    def __init__(self, bot: commands.Bot, data_dir: str):
        self.bot = bot
        self.registry_path = os.path.join(data_dir, "drawing_registry.json")
        self.reg = _load_json(self.registry_path)

    drawing_group = app_commands.Group(
        name="drawing",
        description="Academic Mastery + Studio Benchmark System",
    )

    # -------------------------------------------------
    # CORE PRINCIPLES
    # -------------------------------------------------

    @drawing_group.command(name="core")
    async def core(self, interaction: discord.Interaction):

        items = self.reg.get("academic_core", [])
        pick = _safe_pick(items, seed_key=str(interaction.user.id))

        if not pick:
            await interaction.response.send_message("No core principles found.", ephemeral=True)
            return

        embed = discord.Embed(
            title=pick.get("name", "Core Principle"),
            description="Academic Foundation",
            color=discord.Color.blue(),
        )

        embed.add_field(name="Drills", value=_format_bullets(pick.get("drill_protocol", [])), inline=False)
        embed.add_field(name="Assessment", value=_format_bullets(pick.get("assessment_criteria", [])), inline=False)
        embed.add_field(name="Common Failures", value=_format_bullets(pick.get("common_failures", [])), inline=False)

        await interaction.response.send_message(embed=embed)

    # -------------------------------------------------
    # STUDIO CHECKLIST
    # -------------------------------------------------

    @drawing_group.command(name="studio")
    async def studio(self, interaction: discord.Interaction):

        items = self.reg.get("studio_pipeline", [])
        pick = _safe_pick(items, seed_key=str(interaction.user.id))

        if not pick:
            await interaction.response.send_message("No studio modules found.", ephemeral=True)
            return

        embed = discord.Embed(
            title=pick.get("name", "Studio Module"),
            description="Studio Benchmark Checklist",
            color=discord.Color.green(),
        )

        embed.add_field(name="Deliverables", value=_format_bullets(pick.get("deliverables", [])), inline=False)
        embed.add_field(name="Engine Considerations", value=_format_bullets(pick.get("engine_considerations", [])), inline=False)
        embed.add_field(name="Portfolio Evaluation", value=_format_bullets(pick.get("portfolio_evaluation", [])), inline=False)

        await interaction.response.send_message(embed=embed)

    # -------------------------------------------------
    # INDUSTRY MODE CHECKLIST
    # -------------------------------------------------

    @drawing_group.command(name="industry")
    async def industry(self, interaction: discord.Interaction):

        items = self.reg.get("game_industry_mode", [])
        pick = _safe_pick(items, seed_key=str(interaction.user.id))

        if not pick:
            await interaction.response.send_message("No industry benchmarks found.", ephemeral=True)
            return

        embed = discord.Embed(
            title=pick.get("name", "Industry Mode"),
            description="AAA Studio Checklist",
            color=discord.Color.purple(),
        )

        embed.add_field(name="Technical Checks", value=_format_bullets(pick.get("technical_checks", [])), inline=False)
        embed.add_field(name="Red Flags", value=_format_bullets(pick.get("portfolio_red_flags", [])), inline=False)

        await interaction.response.send_message(embed=embed)


async def register_drawing(bot: commands.Bot, data_dir: str) -> None:
    cog = DrawingCog(bot, data_dir)
    await bot.add_cog(cog)

    if not bot.tree.get_command("drawing"):
        bot.tree.add_command(cog.drawing_group)

import json
import os
from typing import Any, Dict, List

import discord
from discord import app_commands

REGISTRY_FILENAME = "belgian_chocolate_registry.json"


def _load_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _registry_path(data_dir: str) -> str:
    return os.path.join(data_dir, REGISTRY_FILENAME)


def _chunk(lines: List[str], max_len: int = 900) -> str:
    out: List[str] = []
    n = 0
    for line in lines:
        if n + len(line) + 1 > max_len:
            break
        out.append(line)
        n += len(line) + 1
    return "\n".join(out)


async def register_belgium_chocolate(bot: discord.Client, data_dir: str) -> None:
    """
    Attach chocolate commands to existing /belgium group.
    DOES NOT create a new group.
    """

    group = bot.tree.get_command("belgium")
    if not group:
        return  # beverages henüz register edilmemiş

    reg = _load_json(_registry_path(data_dir), {})

    @app_commands.command(name="chocolate", description="Explain Belgian chocolate-making.")
    async def chocolate(interaction: discord.Interaction):
        embed = discord.Embed(
            title="Belgian chocolate-making (overview)",
            description="High-level overview of Belgian chocolate craftsmanship."
        )

        steps = [
            "Ingredients & couverture",
            "Refining & conching",
            "Tempering",
            "Molding & shelling",
            "Fillings",
            "Finishing",
            "Storage",
        ]

        embed.add_field(name="Process", value=_chunk(steps), inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="chocolate_brands", description="Belgian chocolate brands.")
    async def chocolate_brands(interaction: discord.Interaction):
        brands = reg.get("brands", [])
        lines = [f"• {b.get('name')}" for b in brands[:20] if isinstance(b, dict)]

        embed = discord.Embed(
            title="Belgian chocolate brands",
            description="\n".join(lines)[:4096] if lines else "No data available."
        )

        await interaction.response.send_message(embed=embed)

    # Prevent duplicate registration
    if not group.get_command("chocolate"):
        group.add_command(chocolate)

    if not group.get_command("chocolate_brands"):
        group.add_command(chocolate_brands)



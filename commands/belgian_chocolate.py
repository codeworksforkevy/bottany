import os
import json
from typing import List, Dict, Any

import discord
from discord import app_commands


DATA_FILE = "belgium_beverages_cocoa.json"


# -------------------------------------------------
# LOAD COCOA DATASET
# -------------------------------------------------
def _load_cocoa(data_dir: str) -> List[Dict[str, Any]]:
    path = os.path.join(data_dir, DATA_FILE)

    if not os.path.exists(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("items", [])
    except Exception:
        return []


# -------------------------------------------------
# FORMATTER
# -------------------------------------------------
def _format_item(it: Dict[str, Any]) -> str:
    name = it.get("name", "")
    producer = it.get("producer", "")
    region = it.get("region", "")
    year = it.get("foundation_year")
    cert = it.get("certification")

    line = f"• **{name}**"

    if year:
        line += f" _(est. {year})_"

    if cert:
        line += f" 🏷 {cert}"

    if producer:
        line += f"\n  Producer: {producer}"

    if region:
        line += f"\n  Region: {region}"

    line += f"\n  `id: {it.get('id','')}`"

    return line


# -------------------------------------------------
# REGISTER
# -------------------------------------------------
async def register_belgium_chocolate(bot: discord.Client, data_dir: str) -> None:
    """
    Attach chocolate commands to existing /belgium group.
    """

    group = bot.tree.get_command("belgium")
    if not group:
        return  # beverages not registered yet

    # -------------------------------------------------
    # PROCESS OVERVIEW
    # -------------------------------------------------
    @app_commands.command(
        name="chocolate",
        description="Explain Belgian chocolate-making."
    )
    async def chocolate(interaction: discord.Interaction):

        embed = discord.Embed(
            title="Belgian chocolate-making (academic overview)",
            description="Structured overview of Belgian chocolate craftsmanship."
        )

        steps = [
            "Ingredient sourcing (cocoa mass, cocoa butter, sugar)",
            "Refining & particle size reduction",
            "Conching (flavor development & texture refinement)",
            "Tempering (crystal stabilization)",
            "Molding / enrobing",
            "Filling (ganache, praline, liqueur)",
            "Cooling & finishing",
            "Storage & distribution standards"
        ]

        embed.add_field(
            name="Production Stages",
            value="\n".join(f"• {s}" for s in steps),
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    # -------------------------------------------------
    # BRANDS LIST
    # -------------------------------------------------
    @app_commands.command(
        name="chocolate_brands",
        description="Belgian chocolate houses and producers"
    )
    async def chocolate_brands(interaction: discord.Interaction):

        items = _load_cocoa(data_dir)

        if not items:
            await interaction.response.send_message(
                "Cocoa dataset not found.",
                ephemeral=True
            )
            return

        description = "\n\n".join(
            _format_item(i) for i in items[:20]
        )

        embed = discord.Embed(
            title="Belgian Chocolate Houses",
            description=description[:4096],
            color=0x4B2E2E
        )

        await interaction.response.send_message(embed=embed)

    # Prevent duplicate registration
    if not group.get_command("chocolate"):
        group.add_command(chocolate)

    if not group.get_command("chocolate_brands"):
        group.add_command(chocolate_brands)

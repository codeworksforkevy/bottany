import os
import json
from typing import List, Dict, Any, Optional

import discord
from discord import app_commands


DATA_FILE = "belgian_chocolate_professional.json"


# -------------------------------------------------
# LOAD DATASET
# -------------------------------------------------
def _load_dataset(data_dir: str) -> List[Dict[str, Any]]:
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
    year = it.get("foundation_year")
    region = it.get("region", "")
    model = it.get("production_model", "")
    typ = it.get("type", "")
    certifications = it.get("certifications", [])

    line = f"• **{name}**"

    if year:
        line += f" _(est. {year})_"

    if certifications:
        line += " 🏷 " + ", ".join(certifications[:2])

    if model:
        line += f"\n  Model: {model}"

    if typ:
        line += f"\n  Type: {typ}"

    if region:
        line += f"\n  Region: {region}"

    line += f"\n  `id: {it.get('id','')}`"

    return line


# -------------------------------------------------
# REGISTER
# -------------------------------------------------
async def register_belgium_chocolate(bot: discord.Client, data_dir: str) -> None:

    group = bot.tree.get_command("belgium")
    if not group:
        return

    # =================================================
    # THEORY COMMAND
    # =================================================
    @app_commands.command(
        name="chocolate_theory",
        description="Academic theory of Belgian chocolate production"
    )
    async def chocolate_theory(interaction: discord.Interaction):

        embed = discord.Embed(
            title="Belgian Chocolate – Academic Theory",
            description="Structural differences in production systems."
        )

        embed.add_field(
            name="Bean-to-Bar",
            value=(
                "• Full control from cocoa bean roasting to final bar\n"
                "• Origin-based flavor profiling\n"
                "• Small-batch production\n"
                "• Emphasis on terroir and direct trade"
            ),
            inline=False
        )

        embed.add_field(
            name="Couverture System",
            value=(
                "• High cocoa butter content (>31%)\n"
                "• Used by praline houses\n"
                "• Industrial chocolate mass supplied to artisans\n"
                "• Requires precise tempering"
            ),
            inline=False
        )

        embed.add_field(
            name="Crystal Polymorphism",
            value=(
                "• Stable Form V (β2) crystals desired\n"
                "• Tempering ensures gloss and snap\n"
                "• Prevents fat bloom"
            ),
            inline=False
        )

        embed.add_field(
            name="Regulatory Framework",
            value=(
                "• EU Chocolate Directive compliance\n"
                "• Labeling standards\n"
                "• Sustainability certifications"
            ),
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    # =================================================
    # FILTERED BRANDS
    # =================================================
    @app_commands.command(
        name="chocolate_brands",
        description="Filter Belgian chocolate houses"
    )
    @app_commands.describe(
        year_before="Show brands founded before this year",
        year_after="Show brands founded after this year",
        certification="Filter by certification keyword",
        production_model="bean_to_bar | couverture | hybrid"
    )
    async def chocolate_brands(
        interaction: discord.Interaction,
        year_before: Optional[int] = None,
        year_after: Optional[int] = None,
        certification: Optional[str] = None,
        production_model: Optional[str] = None,
    ):

        items = _load_dataset(data_dir)

        if not items:
            await interaction.response.send_message(
                "Chocolate dataset not found.",
                ephemeral=True
            )
            return

        # ---- Year filters ----
        if year_before:
            items = [
                i for i in items
                if i.get("foundation_year") and i["foundation_year"] < year_before
            ]

        if year_after:
            items = [
                i for i in items
                if i.get("foundation_year") and i["foundation_year"] > year_after
            ]

        # ---- Certification filter ----
        if certification:
            cert_lower = certification.lower()
            items = [
                i for i in items
                if any(cert_lower in c.lower() for c in i.get("certifications", []))
            ]

        # ---- Production model filter ----
        if production_model:
            items = [
                i for i in items
                if (i.get("production_model") or "").lower() == production_model.lower()
            ]

        if not items:
            await interaction.response.send_message(
                "No brands matched your filters.",
                ephemeral=True
            )
            return

        description = "\n\n".join(
            _format_item(i) for i in items[:25]
        )

        embed = discord.Embed(
            title="Belgian Chocolate Houses (Filtered)",
            description=description[:4096],
            color=0x4B2E2E
        )

        await interaction.response.send_message(embed=embed)

    # Prevent duplicates
    for cmd in ("chocolate_theory", "chocolate_brands"):
        if not group.get_command(cmd):
            group.add_command(locals()[cmd])

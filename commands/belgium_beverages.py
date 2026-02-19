import os
import json
from typing import Any, Dict, List, Optional, Tuple

import discord
from discord import app_commands


DATA_FILES = {
    "water": "belgium_beverages_water.json",
    "coffee": "belgium_beverages_coffee.json",
    "soft_drinks": "belgium_beverages_soft_drinks.json",
    "cocoa": "belgium_beverages_cocoa.json",
}


# =================================================
# LOAD ALL CATEGORY FILES
# =================================================

def _load_all(data_dir: str) -> List[Dict[str, Any]]:
    all_items: List[Dict[str, Any]] = []

    for category, filename in DATA_FILES.items():
        path = os.path.join(data_dir, filename)
        if not os.path.exists(path):
            continue

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        for item in data.get("items", []):
            item["category"] = category
            all_items.append(item)

    return all_items


# =================================================
# HELPERS
# =================================================

def _norm_category(x: Optional[str]) -> Optional[str]:
    if not x:
        return None
    return x.strip().lower()


def _sort_key(item: Dict[str, Any]) -> Tuple[str, str]:
    return (
        item.get("category", ""),
        item.get("name", "").lower(),
    )


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


# =================================================
# REGISTER (HYBRID LOADER COMPATIBLE)
# =================================================

async def register(bot, data_dir: str):

    root = bot.tree.get_command("belgium")

    if not isinstance(root, app_commands.Group):
        return  # belgium group henüz yoksa çık

    if getattr(bot, "_belgium_beverages_registered", False):
        return

    @app_commands.command(
        name="beverages",
        description="Belgian beverage registry"
    )
    @app_commands.describe(
        category="Filter by category (water, coffee, soft_drinks, cocoa)"
    )
    async def beverages(
        interaction: discord.Interaction,
        category: Optional[str] = None
    ):

        items = _load_all(data_dir)

        cat = _norm_category(category)

        if cat:
            items = [
                i for i in items
                if i.get("category") == cat
            ]

        items.sort(key=_sort_key)

        if not items:
            await interaction.response.send_message(
                "No items found.",
                ephemeral=True
            )
            return

        description = "\n\n".join(
            [_format_item(i) for i in items[:20]]
        )

        embed = discord.Embed(
            title="Belgian Beverage Registry",
            description=description[:4096],
            color=0x2B2D31
        )

        await interaction.response.send_message(embed=embed)

    if not root.get_command("beverages"):
        root.add_command(beverages)

    bot._belgium_beverages_registered = True

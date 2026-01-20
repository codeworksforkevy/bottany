import os
import json
from typing import Any, Dict, List, Optional

import discord
from discord import app_commands

REGISTRY_FILENAME = "belgium_beverages_registry.json"


def _load_registry(data_dir: str) -> Dict[str, Any]:
    path = os.path.join(data_dir, REGISTRY_FILENAME)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _norm_category(x: Optional[str]) -> Optional[str]:
    if not x:
        return None
    x = x.strip().lower()
    aliases = {
        "beer": "beer",
        "beers": "beer",
        "soft": "soft_drinks",
        "soft_drink": "soft_drinks",
        "soft_drinks": "soft_drinks",
        "soda": "soft_drinks",
        "sodas": "soft_drinks",
        "coffee": "coffee",
        "cafe": "coffee",
        "cocoa": "cocoa",
        "hot_chocolate": "cocoa",
        "chocolate": "cocoa",
        "water": "water",
        "mineral_water": "water",
    }
    return aliases.get(x, x)


def _build_embed(title: str, items: List[Dict[str, Any]], category: Optional[str]) -> discord.Embed:
    desc = []
    if category:
        desc.append(f"Category: **{category}**")
    desc.append("\n")

    for it in items[:12]:
        brands = it.get("notable_brands") or []
        brands_txt = ", ".join(brands[:6])
        url = it.get("url") or ""
        summary = (it.get("summary") or "").strip()
        line = f"• **{it.get('name','')}**"
        if brands_txt:
            line += f" — {brands_txt}"
        if summary:
            line += f"\n  {summary}"
        if url:
            line += f"\n  {url}"
        desc.append(line)

    embed = discord.Embed(title=title, description="\n".join(desc)[:4096])
    embed.set_footer(text="Curated list. Use /belgium beverages_show for a single entry by id.")
    return embed


class BelgiumBeveragesGroup(app_commands.Group):
    def __init__(self, data_dir: str):
        super().__init__(name="belgium", description="Belgium: curated culture and brands")
        self._data_dir = data_dir

    @app_commands.command(name="beverages", description="Leading Belgian beverage brands (beer, soft drinks, coffee, cocoa, water)")
    @app_commands.describe(category="Filter by category (beer, soft_drinks, coffee, cocoa, water)")
    async def beverages(self, interaction: discord.Interaction, category: Optional[str] = None):
        reg = _load_registry(self._data_dir)
        items = reg.get("items", [])
        cat = _norm_category(category)
        if cat:
            items = [i for i in items if (i.get("category") or "").lower() == cat]

        # light ordering: beer/soft/water/coffee/cocoa; within category alphabetical
        priority = {"beer": 0, "soft_drinks": 1, "water": 2, "coffee": 3, "cocoa": 4}
        items.sort(key=lambda x: (priority.get((x.get("category") or "").lower(), 99), (x.get("name") or "").lower()))

        if not items:
            await interaction.response.send_message("No items found for that category. Try: beer, soft_drinks, coffee, cocoa, water.", ephemeral=True)
            return

        embed = _build_embed("Belgian beverage brands", items, cat)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="beverages_show", description="Show one curated Belgian beverage entry by id")
    @app_commands.describe(item_id="Registry id, e.g. beer_duvel")
    async def beverages_show(self, interaction: discord.Interaction, item_id: str):
        reg = _load_registry(self._data_dir)
        items = reg.get("items", [])
        target = None
        for it in items:
            if (it.get("id") or "").lower() == (item_id or "").strip().lower():
                target = it
                break
        if not target:
            await interaction.response.send_message("ID not found. Use /belgium beverages to see the curated list.", ephemeral=True)
            return

        brands = ", ".join((target.get("notable_brands") or [])[:12])
        embed = discord.Embed(title=target.get("name", "Belgium beverage"), description=(target.get("summary") or "")[:4096])
        if brands:
            embed.add_field(name="Notable brands/products", value=brands[:1024], inline=False)
        if target.get("url"):
            embed.add_field(name="Official site", value=target["url"], inline=False)
        embed.add_field(name="Category", value=(target.get("category") or "").strip(), inline=True)
        embed.add_field(name="ID", value=(target.get("id") or "").strip(), inline=True)
        await interaction.response.send_message(embed=embed)


async def register_belgium_beverages(bot: discord.Client, data_dir: str) -> None:
    """Register /belgium beverages commands. If /belgium group already exists, attach commands to it."""
    # If there is already a /belgium group, add just the commands as children.
    existing = bot.tree.get_command("belgium")
    if existing and isinstance(existing, app_commands.Group):
        # Avoid duplicates
        if not existing.get_command("beverages"):
            existing.add_command(BelgiumBeveragesGroup(data_dir).get_command("beverages"))
        if not existing.get_command("beverages_show"):
            existing.add_command(BelgiumBeveragesGroup(data_dir).get_command("beverages_show"))
    else:
        bot.tree.add_command(BelgiumBeveragesGroup(data_dir))

    # Sync (best-effort)
    try:
        await bot.tree.sync()
    except Exception:
        pass

import os
import json
from typing import Any, Dict, List, Optional, Tuple

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
        "bier": "beer",
        "soft": "soft_drinks",
        "soft_drink": "soft_drinks",
        "soft_drinks": "soft_drinks",
        "soda": "soft_drinks",
        "sodas": "soft_drinks",
        "lemonade": "soft_drinks",
        "juice": "soft_drinks",
        "juices": "soft_drinks",
        "coffee": "coffee",
        "cafe": "coffee",
        "cocoa": "cocoa",
        "hot_chocolate": "cocoa",
        "chocolate_milk": "cocoa",
        "water": "water",
        "mineral_water": "water",
        "sparkling_water": "water",
    }
    return aliases.get(x, x)


def _norm_tier(x: Optional[str]) -> Optional[str]:
    if not x:
        return None
    x = x.strip().lower()
    aliases = {
        "main": "mainstream",
        "mainstream": "mainstream",
        "mass": "mainstream",
        "craft": "craft",
        "artisan": "craft",
        "heritage": "heritage",
        "classic": "heritage",
        "industry": "industry",
        "b2b": "industry",
    }
    return aliases.get(x, x)


def _matches_query(item: Dict[str, Any], q: str) -> bool:
    q = (q or "").strip().lower()
    if not q:
        return True
    hay = " ".join(
        [
            str(item.get("id") or ""),
            str(item.get("name") or ""),
            " ".join(item.get("notable_brands") or []),
            " ".join(item.get("tags") or []),
        ]
    ).lower()
    return q in hay


def _sort_key(item: Dict[str, Any]) -> Tuple[int, int, str]:
    cat = (item.get("category") or "").lower()
    tier = (item.get("tier") or "").lower()
    category_priority = {"beer": 0, "soft_drinks": 1, "water": 2, "coffee": 3, "cocoa": 4}
    tier_priority = {"mainstream": 0, "heritage": 1, "craft": 2, "industry": 3}
    return (
        category_priority.get(cat, 99),
        tier_priority.get(tier, 99),
        (item.get("name") or "").lower(),
    )


def _chunk(items: List[Dict[str, Any]], size: int = 10) -> List[List[Dict[str, Any]]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _format_item_line(it: Dict[str, Any]) -> str:
    brands = it.get("notable_brands") or []
    brands_txt = ", ".join(brands[:6])
    tier = (it.get("tier") or "").strip()
    summary = (it.get("summary") or "").strip()
    url = (it.get("url") or "").strip()

    line = f"• **{it.get('name','').strip()}**"
    if tier:
        line += f" _(tier: {tier})_"
    if brands_txt:
        line += f" — {brands_txt}"
    if summary:
        line += f"\n  {summary}"
    if url:
        line += f"\n  {url}"
    line += f"\n  `id: {it.get('id','')}`"
    return line


def _build_embed(reg: Dict[str, Any], items: List[Dict[str, Any]], category: Optional[str], tier: Optional[str], q: Optional[str]) -> discord.Embed:
    title = "Belgian beverage brands (curated)"
    desc_lines: List[str] = []

    filters = []
    if category:
        filters.append(f"category=**{category}**")
    if tier:
        filters.append(f"tier=**{tier}**")
    if q:
        filters.append(f"q=**{q.strip()}**")
    if filters:
        desc_lines.append("Filters: " + ", ".join(filters))

    desc_lines.append(
        "Available categories: `beer`, `soft_drinks`, `water`, `coffee`, `cocoa`\n"
        "Available tiers: `mainstream`, `heritage`, `craft`, `industry`\n"
        "Tip: use `/belgium beverages_show item_id:<id>` for a single entry."
    )
    desc_lines.append("\n")

    # Show up to 25 items, chunked for readability
    for it in items[:25]:
        desc_lines.append(_format_item_line(it))

    embed = discord.Embed(title=title, description="\n".join(desc_lines)[:4096])
    updated = (reg.get("updated_utc") or "").strip()
    if updated:
        embed.set_footer(text=f"Curated list • updated {updated}")
    else:
        embed.set_footer(text="Curated list")
    return embed


def _build_filters_embed(reg: Dict[str, Any]) -> discord.Embed:
    cats = reg.get("categories") or []
    tiers = reg.get("tiers") or []
    embed = discord.Embed(title="/belgium beverages filters")
    embed.add_field(name="Categories", value=", ".join([f"`{c}`" for c in cats])[:1024] or "(none)", inline=False)
    embed.add_field(name="Tiers", value=", ".join([f"`{t}`" for t in tiers])[:1024] or "(none)", inline=False)
    embed.add_field(
        name="Examples",
        value=(
            "• `/belgium beverages category:beer tier:heritage`\n"
            "• `/belgium beverages category:soft_drinks q:looza`\n"
            "• `/belgium beverages q:westvleteren`"
        ),
        inline=False,
    )
    return embed


class BelgiumBeveragesGroup(app_commands.Group):
    def __init__(self, data_dir: str):
        super().__init__(name="belgium", description="Belgium: curated culture and brands")
        self._data_dir = data_dir

    @app_commands.command(name="beverages", description="Leading Belgian beverage brands (beer, soft drinks, coffee, cocoa, water)")
    @app_commands.describe(
        category="Filter by category (beer, soft_drinks, water, coffee, cocoa)",
        tier="Filter by tier (mainstream, heritage, craft, industry)",
        q="Search within the curated list (name, brands, tags)",
    )
    async def beverages(self, interaction: discord.Interaction, category: Optional[str] = None, tier: Optional[str] = None, q: Optional[str] = None):
        reg = _load_registry(self._data_dir)
        items = list(reg.get("items", []))

        cat = _norm_category(category)
        tr = _norm_tier(tier)

        if cat:
            items = [i for i in items if (i.get("category") or "").lower() == cat]
        if tr:
            items = [i for i in items if (i.get("tier") or "").lower() == tr]
        if q:
            items = [i for i in items if _matches_query(i, q)]

        items.sort(key=_sort_key)

        if not items:
            await interaction.response.send_message(
                "No items found. Try `/belgium beverages_filters` to see valid filters.",
                ephemeral=True,
            )
            return

        embed = _build_embed(reg, items, cat, tr, q)
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

        embed = discord.Embed(title=target.get("name", "Belgium beverage"), description=(target.get("summary") or "")[:4096])

        brands = ", ".join((target.get("notable_brands") or [])[:20])
        if brands:
            embed.add_field(name="Notable brands/products", value=brands[:1024], inline=False)

        tags = ", ".join((target.get("tags") or [])[:20])
        if tags:
            embed.add_field(name="Tags", value=tags[:1024], inline=False)

        if target.get("url"):
            embed.add_field(name="Official site", value=str(target["url"])[:1024], inline=False)

        embed.add_field(name="Category", value=(target.get("category") or "").strip(), inline=True)
        embed.add_field(name="Tier", value=(target.get("tier") or "").strip(), inline=True)
        embed.add_field(name="ID", value=(target.get("id") or "").strip(), inline=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="beverages_filters", description="Show available filters for /belgium beverages")
    async def beverages_filters(self, interaction: discord.Interaction):
        reg = _load_registry(self._data_dir)
        embed = _build_filters_embed(reg)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def register_belgium_beverages(bot: discord.Client, data_dir: str) -> None:
    """Register /belgium beverages commands. If /belgium group already exists, attach commands to it."""
    existing = bot.tree.get_command("belgium")
    group = BelgiumBeveragesGroup(data_dir)

    if existing and isinstance(existing, app_commands.Group):
        for cmd_name in ("beverages", "beverages_show", "beverages_filters"):
            if not existing.get_command(cmd_name):
                existing.add_command(group.get_command(cmd_name))
    else:
        bot.tree.add_command(group)

    try:
        await bot.tree.sync()
    except Exception:
        pass

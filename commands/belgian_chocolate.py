# belgian_chocolate.py
from __future__ import annotations

import json
import logging
import os
import random
from typing import Any, Dict, List, Optional

import discord
from discord import app_commands

log = logging.getLogger(__name__)

# ── Choices built from what actually exists in the data ──────────────────────

_TYPE_CHOICES = [
    app_commands.Choice(name="Chocolate",     value="chocolate"),
    app_commands.Choice(name="Dessert",       value="dessert"),
    app_commands.Choice(name="Artisan",       value="artisan"),
    app_commands.Choice(name="Industrial",    value="industrial"),
    app_commands.Choice(name="Praline House", value="praline_house"),
]

_PRODUCTION_CHOICES = [
    app_commands.Choice(name="Bean to Bar", value="bean_to_bar"),
    app_commands.Choice(name="Couverture",  value="couverture"),
    app_commands.Choice(name="Hybrid",      value="hybrid"),
]

_CERT_CHOICES = [
    app_commands.Choice(name="Belgian Chocolate Code",           value="Belgian Chocolate Code"),
    app_commands.Choice(name="BRC Global Standard",              value="BRC Global Standard"),
    app_commands.Choice(name="Direct Trade",                     value="Direct Trade"),
    app_commands.Choice(name="EU Chocolate Directive Compliant", value="EU Chocolate Directive Compliant"),
    app_commands.Choice(name="EU Organic",                       value="EU Organic"),
    app_commands.Choice(name="Fairtrade",                        value="Fairtrade"),
    app_commands.Choice(name="ISO 22000",                        value="ISO 22000"),
    app_commands.Choice(name="Rainforest Alliance",              value="Rainforest Alliance"),
    app_commands.Choice(name="Single Origin Certified",          value="Single Origin Certified"),
    app_commands.Choice(name="UTZ Certified",                    value="UTZ Certified"),
]


# ── Loader ────────────────────────────────────────────────────────────────────

def _load_dataset(data_dir: str) -> List[Dict[str, Any]]:
    primary_files = [
        "belgium_chocolate_desserts_dataset.json",
        "belgian_chocolate_professional.json",
    ]
    merged: List[Dict[str, Any]] = []
    for filename in primary_files:
        path = os.path.join(data_dir, filename)
        if not os.path.exists(path):
            log.warning("Chocolate data file not found: %s", path)
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            log.error("Error loading %s: %s", filename, exc)
            continue
        items = raw if isinstance(raw, list) else raw.get("items", [])
        for item in items:
            if isinstance(item, dict):
                merged.append(item)

    seen: set[str] = set()
    unique: List[Dict[str, Any]] = []
    index: Dict[str, Dict[str, Any]] = {}
    for item in merged:
        key = (item.get("name") or "").lower().strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(item)
            index[key] = item

    cocoa_path = os.path.join(data_dir, "belgium_beverages_cocoa.json")
    if os.path.exists(cocoa_path):
        try:
            with open(cocoa_path, "r", encoding="utf-8") as f:
                cocoa_raw = json.load(f)
            cocoa_items = cocoa_raw.get("items", [])
            for cocoa_item in cocoa_items:
                key = (cocoa_item.get("name") or "").lower().strip()
                if key in index:
                    target = index[key]
                    if cocoa_item.get("producer") and not target.get("producer"):
                        target["producer"] = cocoa_item["producer"]
                    if cocoa_item.get("foundation_year") and not target.get("foundation_year"):
                        target["foundation_year"] = cocoa_item["foundation_year"]
                else:
                    unique.append(cocoa_item)
        except (json.JSONDecodeError, OSError):
            pass

    return unique


# ── Helpers ───────────────────────────────────────────────────────────────────

def _unified_type(item: Dict[str, Any]) -> str:
    return item.get("category") or item.get("type") or "chocolate"

def _get_dynamic_description(item: Dict[str, Any]) -> str:
    """Generates varied intro sentences to avoid repetitive 'X is a brand' phrasing."""
    name = item.get("name", "This brand")
    itype = _unified_type(item).replace("_", " ").lower()
    year = item.get("foundation_year")
    
    # Selection of different sentence structures
    templates = [
        f"Discover the craft of **{name}**, a renowned Belgian {itype}.",
        f"Proudly representing Belgium's culinary heritage, **{name}** specializes in premium {itype} production.",
        f"**{name}** has been a key player in the Belgian {itype} scene" + (f" since {year}." if year else "."),
        f"Exploring the exquisite flavors of **{name}**, a distinguished name among Belgian {itype} houses."
    ]
    
    intro = random.choice(templates)
    # Append the official notes/summary if they exist
    body = item.get("summary") or item.get("notes") or ""
    
    full_text = f"{intro}\n\n{body}"
    return full_text[:1024] # Discord limit check


# ── Embed builders ────────────────────────────────────────────────────────────

def _list_embed(items: List[Dict[str, Any]], filters_applied: List[str]) -> discord.Embed:
    title = "Belgian Chocolate & Sweets"
    if filters_applied:
        title += f" — {', '.join(filters_applied)}"

    embed = discord.Embed(title=title, color=0x3B1A08)

    for item in items:
        name    = item.get("name", "Unknown")
        url     = item.get("url")
        itype   = _unified_type(item)
        year    = item.get("foundation_year")
        
        parts = [itype.replace("_", " ").title()]
        if year: parts.append(f"est. {year}")

        field_name = f"**[{name}]({url})**" if url else f"**{name}**"
        embed.add_field(name=field_name, value=" | ".join(parts), inline=True)

    embed.set_footer(text=f"{len(items)} result(s) · Use /belgium chocolate_info for details")
    return embed

def _detail_embed(item: Dict[str, Any]) -> discord.Embed:
    """Detailed view for a single brand with dynamic text and automatic thumbnails."""
    name  = item.get("name", "Unknown")
    url   = item.get("url")
    certs = item.get("certifications", [])

    embed = discord.Embed(title=name, color=0x3B1A08)
    if url:
        embed.url = url

    # 1. Dynamic Description (Replacing the boring 'X is a brand' line)
    embed.description = _get_dynamic_description(item)

    # 2. Auto-Thumbnail (Avatar size, copyright-free)
    image_url = item.get("image_url")
    if not image_url:
        # Fallback to Unsplash curated IDs (Square crop)
        itype = _unified_type(item).lower()
        if "dessert" in itype:
            # Delicious pastry image
            image_url = "https://images.unsplash.com/photo-1551024601-bec78aea704b?w=200&h=200&fit=crop"
        elif "artisan" in itype or "praline" in itype:
            # Handmade chocolate image
            image_url = "https://images.unsplash.com/photo-1548907040-4baa42d10919?w=200&h=200&fit=crop"
        else:
            # General cocoa beans/bars
            image_url = "https://images.unsplash.com/photo-1547517023-7ca0c162f816?w=200&h=200&fit=crop"
    
    embed.set_thumbnail(url=image_url)

    # 3. Official Source & Details
    region    = item.get("region") or item.get("area")
    year      = item.get("foundation_year")
    prod      = item.get("production_model")
    warrant   = item.get("royal_warrant", False)

    if region:
        embed.add_field(name="Region",     value=region,                          inline=True)
    if year:
        embed.add_field(name="Founded",    value=str(year),                       inline=True)
    if prod:
        embed.add_field(name="Production", value=prod.replace("_", " ").title(),  inline=True)
    
    if warrant:
        embed.add_field(name="Status",     value="🏅 Belgian Royal Warrant Holder", inline=False)
    
    if certs:
        embed.add_field(name="Certifications", value="\n".join(f"• {c}" for c in certs), inline=False)

    if url:
        # Emphasizing the official nature of the source
        embed.add_field(name="Official Source", value=f"🔗 [Visit Official Website]({url})", inline=False)

    # Footer attribution
    footer = item.get("image_credit") or "Verified Belgian Heritage Data"
    embed.set_footer(text=footer)

    return embed


# ── Registration ──────────────────────────────────────────────────────────────

async def register(bot: discord.Client, data_dir: str) -> None:
    root = bot.tree.get_command("belgium")
    if not isinstance(root, app_commands.Group):
        log.error("belgian_chocolate: '/belgium' group not found.")
        return

    if not root.get_command("chocolate_brands"):
        @app_commands.command(name="chocolate_brands", description="Browse Belgian chocolate houses.")
        @app_commands.choices(type=_TYPE_CHOICES, production_model=_PRODUCTION_CHOICES, certification=_CERT_CHOICES)
        async def chocolate_brands(
            interaction: discord.Interaction,
            type: Optional[str] = None,
            production_model: Optional[str] = None,
            certification: Optional[str] = None,
            random_pick: bool = False,
        ) -> None:
            await interaction.response.defer()
            items = _load_dataset(data_dir)
            if not items:
                await interaction.followup.send("Dataset error.", ephemeral=True)
                return

            if type: items = [i for i in items if _unified_type(i).lower() == type.lower()]
            if production_model: items = [i for i in items if (i.get("production_model") or "").lower() == production_model.lower()]
            if certification: items = [i for i in items if certification in i.get("certifications", [])]

            if not items:
                await interaction.followup.send("No results found.", ephemeral=True)
                return

            if random_pick:
                await interaction.followup.send(embed=_detail_embed(random.choice(items)))
                return

            await interaction.followup.send(embed=_list_embed(items, []))

        root.add_command(chocolate_brands)

    if not root.get_command("chocolate_info"):
        async def _brand_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
            items = _load_dataset(data_dir)
            needle = current.lower().strip()
            matches = list(set(i.get("name", "") for i in items if needle in (i.get("name") or "").lower()))
            return [app_commands.Choice(name=n, value=n.lower()) for n in sorted(matches)[:25]]

        @app_commands.command(name="chocolate_info", description="Details for a specific brand.")
        @app_commands.autocomplete(name=_brand_autocomplete)
        async def chocolate_info(interaction: discord.Interaction, name: str) -> None:
            await interaction.response.defer()
            items = _load_dataset(data_dir)
            match = next((i for i in items if (i.get("name") or "").lower().strip() == name.lower().strip()), None)

            if not match:
                await interaction.followup.send(f"Brand **{name}** not found.", ephemeral=True)
                return

            await interaction.followup.send(embed=_detail_embed(match))

        root.add_command(chocolate_info)

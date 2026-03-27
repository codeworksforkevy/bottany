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
    app_commands.Choice(name="🍫 Chocolate",     value="chocolate"),
    app_commands.Choice(name="🧇 Dessert",       value="dessert"),
    app_commands.Choice(name="🎨 Artisan",       value="artisan"),
    app_commands.Choice(name="🏭 Industrial",    value="industrial"),
    app_commands.Choice(name="🎁 Praline House", value="praline_house"),
]

_PRODUCTION_CHOICES = [
    app_commands.Choice(name="🌱 Bean to Bar", value="bean_to_bar"),
    app_commands.Choice(name="🍶 Couverture",  value="couverture"),
    app_commands.Choice(name="🔀 Hybrid",      value="hybrid"),
]

_CERT_CHOICES = [
    app_commands.Choice(name="🏅 Belgian Chocolate Code",           value="Belgian Chocolate Code"),
    app_commands.Choice(name="✅ BRC Global Standard",              value="BRC Global Standard"),
    app_commands.Choice(name="🤝 Direct Trade",                     value="Direct Trade"),
    app_commands.Choice(name="🇪🇺 EU Chocolate Directive Compliant", value="EU Chocolate Directive Compliant"),
    app_commands.Choice(name="🌿 EU Organic",                       value="EU Organic"),
    app_commands.Choice(name="⚖️ Fairtrade",                        value="Fairtrade"),
    app_commands.Choice(name="📋 ISO 22000",                        value="ISO 22000"),
    app_commands.Choice(name="🌲 Rainforest Alliance",              value="Rainforest Alliance"),
    app_commands.Choice(name="🗺️ Single Origin Certified",          value="Single Origin Certified"),
    app_commands.Choice(name="☑️ UTZ Certified",                    value="UTZ Certified"),
]

# All brands across all three datasets — 30 unique names
_BRAND_CHOICES = [
    app_commands.Choice(name="Belcolade",          value="belcolade"),
    app_commands.Choice(name="Belgian Waffle",     value="belgian waffle"),
    app_commands.Choice(name="Belvas",             value="belvas"),
    app_commands.Choice(name="Bruyerre",           value="bruyerre"),
    app_commands.Choice(name="Brussels Waffle",    value="brussels waffle"),
    app_commands.Choice(name="Callebaut",          value="callebaut"),
    app_commands.Choice(name="Chocolat Jacques",   value="chocolat jacques"),
    app_commands.Choice(name="Corné Port-Royal",   value="corné port-royal"),
    app_commands.Choice(name="Cuberdon",           value="cuberdon"),
    app_commands.Choice(name="Côte d'Or",          value="côte d'or"),
    app_commands.Choice(name="Dolfin",             value="dolfin"),
    app_commands.Choice(name="Dumon",              value="dumon"),
    app_commands.Choice(name="Galler",             value="galler"),
    app_commands.Choice(name="Godiva",             value="godiva"),
    app_commands.Choice(name="Guylian",            value="guylian"),
    app_commands.Choice(name="Leonidas",           value="leonidas"),
    app_commands.Choice(name="Liège Waffle",       value="liège waffle"),
    app_commands.Choice(name="Mary Chocolatier",   value="mary chocolatier"),
    app_commands.Choice(name="Mattentaart",        value="mattentaart"),
    app_commands.Choice(name="Merveilleux",        value="merveilleux"),
    app_commands.Choice(name="Meurisse",           value="meurisse"),
    app_commands.Choice(name="Neuhaus",            value="neuhaus"),
    app_commands.Choice(name="Pierre Marcolini",   value="pierre marcolini"),
    app_commands.Choice(name="Planète Chocolat",   value="planète chocolat"),
    app_commands.Choice(name="Rijsttaart",         value="rijsttaart"),
    app_commands.Choice(name="Speculoos",          value="speculoos"),
    app_commands.Choice(name="Tarte au Riz",       value="tarte au riz"),
    app_commands.Choice(name="The Chocolate Line", value="the chocolate line"),
    app_commands.Choice(name="Wittamer",           value="wittamer"),
]


# ── Loader ────────────────────────────────────────────────────────────────────

def _load_dataset(data_dir: str) -> List[Dict[str, Any]]:
    """
    Load and merge all three JSON files, deduplicating by name.

    Load order matters:
      1. Desserts  — category, summary, url, tags
      2. Professional — foundation_year, production_model, type, certifications, notes
      3. Cocoa — producer, region (more precise), foundation_year

    Because all 10 cocoa brands already exist in datasets 1 or 2, simple
    name-based dedup would silently drop every cocoa entry and lose the
    'producer' field entirely. Instead the cocoa dataset is used as an
    enrichment layer: its fields are merged INTO the already-deduped item
    rather than appended as a new record.
    """
    # ── Step 1: load desserts + professional, dedup by name ──────────────────
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
        except json.JSONDecodeError as exc:
            log.error("Malformed JSON in %s: %s", filename, exc)
            continue
        except OSError as exc:
            log.error("Could not read %s: %s", filename, exc)
            continue
        items = raw if isinstance(raw, list) else raw.get("items", [])
        for item in items:
            if isinstance(item, dict):
                merged.append(item)

    seen: set[str] = set()
    unique: List[Dict[str, Any]] = []
    index: Dict[str, Dict[str, Any]] = {}   # name.lower() → item ref
    for item in merged:
        key = (item.get("name") or "").lower().strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(item)
            index[key] = item

    # ── Step 2: load cocoa and ENRICH existing items ──────────────────────────
    cocoa_path = os.path.join(data_dir, "belgium_beverages_cocoa.json")
    if os.path.exists(cocoa_path):
        try:
            with open(cocoa_path, "r", encoding="utf-8") as f:
                cocoa_raw = json.load(f)
            cocoa_items = cocoa_raw.get("items", [])
            for cocoa_item in cocoa_items:
                if not isinstance(cocoa_item, dict):
                    continue
                key = (cocoa_item.get("name") or "").lower().strip()
                if key in index:
                    # Enrich: add producer and fill any missing fields
                    target = index[key]
                    if cocoa_item.get("producer") and not target.get("producer"):
                        target["producer"] = cocoa_item["producer"]
                    if cocoa_item.get("foundation_year") and not target.get("foundation_year"):
                        target["foundation_year"] = cocoa_item["foundation_year"]
                    if cocoa_item.get("region") and not target.get("region"):
                        target["region"] = cocoa_item["region"]
                else:
                    # Brand only in cocoa — add it as a new entry
                    cert = cocoa_item.pop("certification", None)
                    if "certifications" not in cocoa_item:
                        cocoa_item["certifications"] = [cert] if cert else []
                    unique.append(cocoa_item)
                    index[key] = cocoa_item
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("Could not load cocoa enrichment data: %s", exc)

    return unique


# ── Helpers ───────────────────────────────────────────────────────────────────

def _unified_type(item: Dict[str, Any]) -> str:
    """Normalised type/category regardless of which dataset the item came from."""
    return item.get("category") or item.get("type") or "—"


# ── Embed builders ────────────────────────────────────────────────────────────

def _list_embed(items: List[Dict[str, Any]], filters_applied: List[str]) -> discord.Embed:
    """Single embed listing all matching brands with key details inline."""
    title = "🍫 Belgian Chocolate & Sweets"
    if filters_applied:
        title += f" — {', '.join(filters_applied)}"

    embed = discord.Embed(title=title, color=0x4B2E2E)

    for item in items:
        name    = item.get("name", "Unknown")
        emoji   = item.get("emoji", "🍫")
        url     = item.get("url")
        itype   = _unified_type(item)
        year    = item.get("foundation_year")
        prod    = item.get("production_model")
        certs   = item.get("certifications", [])
        warrant = item.get("royal_warrant", False)

        parts: List[str] = []
        if itype and itype != "—":
            parts.append(itype.replace("_", " ").title())
        if year:
            parts.append(f"est. {year}")
        if prod:
            parts.append(prod.replace("_", " ").title())

        value = ", ".join(parts) if parts else "Belgian classic"
        if warrant:
            value += "\n👑 Royal Warrant Holder"
        if certs:
            value += f"\n✅ {', '.join(certs[:2])}"

        field_name = f"{emoji} [{name}]({url})" if url else f"{emoji} {name}"
        embed.add_field(name=field_name, value=value, inline=True)

    embed.set_footer(
        text=f"{len(items)} result(s) · Use /belgium chocolate_info <n> for full details"
    )
    return embed

def _detail_embed(item: Dict[str, Any]) -> discord.Embed:
    """Full detail embed for a single brand — used by /belgium chocolate_info."""
    name  = item.get("name", "Unknown")
    url   = item.get("url")
    text  = item.get("summary") or item.get("notes") or ""
    certs = item.get("certifications", [])

    item_emoji = item.get("emoji", "🍫")
    embed = discord.Embed(title=f"{item_emoji} {name}", color=0x4B2E2E)
    if url:
        embed.url = url

    region    = item.get("region") or item.get("area")
    year      = item.get("foundation_year")
    prod      = item.get("production_model")
    producer  = item.get("producer")          # cocoa dataset field
    itype     = _unified_type(item)

    warrant      = item.get("royal_warrant", False)
    image_url    = item.get("image_url")
    image_credit = item.get("image_credit", "")

    if region:
        embed.add_field(name="📍 Region",     value=region,                          inline=True)
    if producer:
        embed.add_field(name="🏢 Producer",   value=producer,                        inline=True)
    if year:
        embed.add_field(name="📅 Founded",    value=str(year),                       inline=True)
    if itype and itype != "—":
        embed.add_field(name="🏷 Type",       value=itype.replace("_", " ").title(), inline=True)
    if prod:
        embed.add_field(name="🏭 Production", value=prod.replace("_", " ").title(),  inline=True)
    if warrant:
        embed.add_field(name="👑 Status",     value="Belgian Royal Warrant Holder",  inline=True)
    if certs:
        embed.add_field(name="✅ Certifications", value="\n".join(f"• {c}" for c in certs), inline=False)
    if text:
        embed.add_field(name="📖 About",      value=text[:1024],                     inline=False)
    if url:
        embed.add_field(name="🔗 Source",     value=f"[Visit website]({url})",       inline=False)

    if image_url:
        embed.set_image(url=image_url)
        # CC license requires attribution — shown in footer
        footer = image_credit if image_credit else "Image: Wikimedia Commons"
        embed.set_footer(text=f"🖼️ {footer}")

    return embed


# ── Registration ──────────────────────────────────────────────────────────────

async def register(bot: discord.Client, data_dir: str) -> None:
    """
    Registers two subcommands under /belgium:
      /belgium chocolate_brands  — filterable list of all brands
      /belgium chocolate_info    — full detail view for one specific brand
    """
    root = bot.tree.get_command("belgium")
    if not isinstance(root, app_commands.Group):
        log.error(
            "belgian_chocolate: '/belgium' group not found. "
            "Make sure _belgium.py loads before belgian_chocolate.py."
        )
        return

    # ── /belgium chocolate_brands ─────────────────────────────────────────────

    if not root.get_command("chocolate_brands"):

        @app_commands.command(
            name="chocolate_brands",
            description="Browse Belgian chocolate houses and sweets with optional filters.",
        )
        @app_commands.describe(
            type="Filter by product type",
            production_model="Filter by production model (professional brands only)",
            certification="Filter by quality certification (professional brands only)",
            year_before="Brands founded before this year (professional brands only)",
            year_after="Brands founded after this year (professional brands only)",
            random_pick="Return one random brand with full details",
        )
        @app_commands.choices(
            type=_TYPE_CHOICES,
            production_model=_PRODUCTION_CHOICES,
            certification=_CERT_CHOICES,
        )
        async def chocolate_brands(
            interaction: discord.Interaction,
            type: Optional[str] = None,
            production_model: Optional[str] = None,
            certification: Optional[str] = None,
            year_before: Optional[int] = None,
            year_after: Optional[int] = None,
            random_pick: bool = False,
        ) -> None:

            await interaction.response.defer()

            items = _load_dataset(data_dir)
            if not items:
                await interaction.followup.send(
                    "⚠️ Chocolate dataset could not be loaded. "
                    "Please ask an admin to check the `data/` directory.",
                    ephemeral=True,
                )
                return

            filters_applied: List[str] = []

            if type:
                items = [i for i in items if _unified_type(i).lower() == type.lower()]
                filters_applied.append(type.replace("_", " ").title())

            if production_model:
                items = [
                    i for i in items
                    if (i.get("production_model") or "").lower() == production_model.lower()
                ]
                filters_applied.append(production_model.replace("_", " ").title())

            if certification:
                items = [i for i in items if certification in i.get("certifications", [])]
                filters_applied.append(certification)

            if year_before is not None:
                items = [
                    i for i in items
                    if isinstance(i.get("foundation_year"), int)
                    and i["foundation_year"] < year_before
                ]
                filters_applied.append(f"before {year_before}")

            if year_after is not None:
                items = [
                    i for i in items
                    if isinstance(i.get("foundation_year"), int)
                    and i["foundation_year"] > year_after
                ]
                filters_applied.append(f"after {year_after}")

            if not items:
                await interaction.followup.send(
                    "😕 No brands matched your filters.\n"
                    "**Tips:**\n"
                    "• `production_model` and `certification` only apply to professional brands\n"
                    "• `year_before` / `year_after` only apply to brands with a known founding year\n"
                    "• Try removing one filter at a time",
                    ephemeral=True,
                )
                return

            if random_pick:
                await interaction.followup.send(embed=_detail_embed(random.choice(items)))
                return

            await interaction.followup.send(embed=_list_embed(items, filters_applied))

        root.add_command(chocolate_brands)
        log.info("Registered /belgium chocolate_brands")

    # ── /belgium chocolate_info ───────────────────────────────────────────────

    if not root.get_command("chocolate_info"):

        @app_commands.command(
            name="chocolate_info",
            description="Get full details for a specific Belgian chocolate brand or sweet.",
        )
        @app_commands.describe(name="Brand or product name")
        @app_commands.choices(name=_BRAND_CHOICES)
        async def chocolate_info(
            interaction: discord.Interaction,
            name: str,
        ) -> None:

            await interaction.response.defer()

            items = _load_dataset(data_dir)
            if not items:
                await interaction.followup.send(
                    "⚠️ Chocolate dataset could not be loaded.", ephemeral=True
                )
                return

            match = next(
                (i for i in items if (i.get("name") or "").lower().strip() == name.lower().strip()),
                None,
            )

            if not match:
                await interaction.followup.send(
                    f"😕 No brand found matching **\"{name}\"**.\n"
                    "Use the autocomplete dropdown to pick a valid name.",
                    ephemeral=True,
                )
                return

            await interaction.followup.send(embed=_detail_embed(match))

        root.add_command(chocolate_info)
        log.info("Registered /belgium chocolate_info")

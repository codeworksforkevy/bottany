# belgium_commands.py
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

import discord
from discord import app_commands

log = logging.getLogger(__name__)

# ── Data files ────────────────────────────────────────────────────────────────
# All Belgian datasets that /belgium_search should cover.
# Each entry: (filename, dataset_type, category_field)
_SOURCES = [
    ("belgium_chocolate_desserts_dataset.json", "chocolate",   "category"),
    ("belgian_chocolate_professional.json",      "chocolate",   "type"),
    ("belgium_beverages_cocoa.json",             "cocoa",       None),
    ("belgium_beverages_water.json",             "beverage",    None),
    ("belgium_beverages_coffee.json",            "beverage",    None),
    ("belgium_beverages_soft_drinks.json",       "beverage",    None),
]


# ── Dataset badge ─────────────────────────────────────────────────────────────

def _dataset_badge(item: Dict[str, Any]) -> str:
    dtype    = (item.get("dataset_type") or "").lower()
    category = (item.get("category")     or "").lower()
    itype    = (item.get("type")         or "").lower()

    if dtype == "chocolate" or category in ("chocolate", "praline", "dessert", "waffle", "speculoos"):
        return "🍫"
    if dtype == "cocoa":
        return "🍫"
    if category == "beer":
        return "🍺"
    if category == "soft_drinks":
        return "🥤"
    if category == "water":
        return "🚰"
    if category == "coffee":
        return "☕"
    if itype in ("artisan", "praline_house", "industrial"):
        return "🍫"
    return "📦"


# ── Footer helper ─────────────────────────────────────────────────────────────

def _apply_footer(embed: discord.Embed, page: int, pages: int, source: str) -> None:
    embed.set_footer(text=f"Page {page}/{pages} · {source}")


# ── Loader ────────────────────────────────────────────────────────────────────

def _load_all_belgium(data_dir: str) -> List[Dict[str, Any]]:
    """Load and merge all Belgian datasets into a flat searchable list."""
    all_items: List[Dict[str, Any]] = []

    for filename, dataset_type, cat_field in _SOURCES:
        path = os.path.join(str(data_dir), filename)
        if not os.path.exists(path):
            log.debug("Belgium search: skipping missing file %s", filename)
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("Belgium search: could not load %s: %s", filename, exc)
            continue

        items = raw if isinstance(raw, list) else raw.get("items", [])
        for item in items:
            if not isinstance(item, dict):
                continue
            # Tag each item with its dataset type so the badge function works
            item = dict(item)
            item["dataset_type"] = dataset_type
            all_items.append(item)

    return all_items


# ── Fuzzy search ──────────────────────────────────────────────────────────────

def _fuzzy_search(query: str, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Case-insensitive substring search across name, summary/notes, category,
    region, and tags. Returns items sorted by match quality:
      1. Name starts with query  (best)
      2. Name contains query
      3. Any other field contains query
    """
    q = query.lower().strip()
    if not q:
        return []

    tier1: List[Dict[str, Any]] = []
    tier2: List[Dict[str, Any]] = []
    tier3: List[Dict[str, Any]] = []
    seen: set[str] = set()

    for item in items:
        name = (item.get("name") or "").lower()
        key  = name  # use name as dedup key

        # Build a searchable blob from all text fields
        blob = " ".join(filter(None, [
            item.get("name", ""),
            item.get("summary", ""),
            item.get("notes", ""),
            item.get("category", ""),
            item.get("type", ""),
            item.get("region", ""),
            item.get("producer", ""),
            " ".join(item.get("tags", [])),
            " ".join(item.get("certifications", [])),
        ])).lower()

        if q not in blob:
            continue
        if key in seen:
            continue
        seen.add(key)

        if name.startswith(q):
            tier1.append(item)
        elif q in name:
            tier2.append(item)
        else:
            tier3.append(item)

    return tier1 + tier2 + tier3


# ── Pagination view ───────────────────────────────────────────────────────────

class PaginationView(discord.ui.View):
    """Prev/Next paginator for a pre-built list of embeds."""

    def __init__(self, embeds: List[discord.Embed]) -> None:
        super().__init__(timeout=120)
        self._embeds = embeds
        self._page   = 0
        self._refresh()

    def _refresh(self) -> None:
        self.prev_btn.disabled = self._page == 0
        self.next_btn.disabled = self._page >= len(self._embeds) - 1

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
    async def prev_btn(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self._page -= 1
        self._refresh()
        await interaction.response.edit_message(embed=self._embeds[self._page], view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next_btn(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self._page += 1
        self._refresh()
        await interaction.response.edit_message(embed=self._embeds[self._page], view=self)


# ── Registration ──────────────────────────────────────────────────────────────

async def register(bot, data_dir) -> None:

    @bot.tree.command(
        name="belgium_search",
        description="Search across all Belgian cultural datasets (chocolate, beverages, desserts…)",
    )
    @app_commands.describe(query="What to search for — brand name, region, certification, category…")
    async def belgium_search(
        interaction: discord.Interaction,
        query: str,
    ) -> None:

        await interaction.response.defer()

        if len(query.strip()) < 2:
            await interaction.followup.send(
                "😕 Please enter at least 2 characters to search.", ephemeral=True
            )
            return

        items = _load_all_belgium(data_dir)

        if not items:
            await interaction.followup.send(
                "⚠️ No Belgian datasets could be loaded. "
                "Please ask an admin to check the `data/` directory.",
                ephemeral=True,
            )
            return

        results = _fuzzy_search(query, items)

        if not results:
            await interaction.followup.send(
                f"😕 No results for **\"{query}\"** across Belgian datasets.\n"
                "Try a brand name, region, category, or certification keyword.",
                ephemeral=True,
            )
            return

        # Build paginated embeds — 5 results per page
        chunks = [results[i:i + 5] for i in range(0, min(len(results), 50), 5)]
        pages  = len(chunks)
        embeds: List[discord.Embed] = []

        for page_num, chunk in enumerate(chunks, start=1):
            embed = discord.Embed(
                title=f"🇧🇪 Belgium Search — \"{query}\"",
                description=f"**{len(results)}** result(s) found · showing {len(results[:50])}",
                color=0x5865F2,
            )

            for item in chunk:
                badge    = _dataset_badge(item)
                name     = item.get("name", "Unknown")
                category = item.get("category") or item.get("type") or "—"
                region   = item.get("region") or "—"
                year     = item.get("foundation_year")
                producer = item.get("producer")
                url      = item.get("url")

                value_parts = [f"📂 {category.replace('_', ' ').title()}"]
                if region and region != "—":
                    value_parts.append(f"📍 {region}")
                if year:
                    value_parts.append(f"📅 est. {year}")
                if producer:
                    value_parts.append(f"🏢 {producer}")

                value = "\n".join(value_parts)
                field_name = f"{badge} [{name}]({url})" if url else f"{badge} {name}"
                embed.add_field(name=field_name, value=value, inline=False)

            _apply_footer(embed, page_num, pages, source="Belgium Cultural Registry")
            embeds.append(embed)

        view = PaginationView(embeds) if len(embeds) > 1 else None
        await interaction.followup.send(embed=embeds[0], view=view)

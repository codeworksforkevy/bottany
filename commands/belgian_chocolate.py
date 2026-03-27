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

# ── Data files (both datasets are merged at load time) ──────────────────────
_DATA_FILES = [
    "belgium_chocolate_desserts_dataset.json",
    "belgian_chocolate_professional.json",
]

# ── Autocomplete choices ─────────────────────────────────────────────────────
_PRODUCTION_CHOICES = [
    app_commands.Choice(name="Bean to Bar",  value="bean_to_bar"),
    app_commands.Choice(name="Couverture",   value="couverture"),
    app_commands.Choice(name="Hybrid",       value="hybrid"),
]

_CATEGORY_CHOICES = [
    app_commands.Choice(name="Chocolate",  value="chocolate"),
    app_commands.Choice(name="Praline",    value="praline"),
    app_commands.Choice(name="Dessert",    value="dessert"),
    app_commands.Choice(name="Waffle",     value="waffle"),
    app_commands.Choice(name="Speculoos",  value="speculoos"),
]


# ── Loaders ──────────────────────────────────────────────────────────────────

def _load_dataset(data_dir: str) -> List[Dict[str, Any]]:
    """Load and merge both chocolate JSON files. Returns a flat list of items."""
    merged: List[Dict[str, Any]] = []

    for filename in _DATA_FILES:
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

        # Both files store records under an "items" key
        items = raw if isinstance(raw, list) else raw.get("items", [])
        for item in items:
            if isinstance(item, dict):
                merged.append(item)

    return merged


# ── Formatting ───────────────────────────────────────────────────────────────

def _format_item(item: Dict[str, Any]) -> str:
    lines: List[str] = []

    region = item.get("region") or item.get("area")
    if region:
        lines.append(f"📍 {region}")

    year = item.get("foundation_year")
    if year:
        lines.append(f"📅 Founded: {year}")

    prod = item.get("production_model")
    if prod:
        lines.append(f"🏭 Production: {prod}")

    category = item.get("category") or item.get("type")
    if category:
        lines.append(f"🏷 Category: {category}")

    certs: List[str] = item.get("certifications", [])
    if certs:
        lines.append(f"✅ Certifications: {', '.join(certs)}")

    summary = item.get("summary") or item.get("notes")
    if summary:
        # Trim long notes to keep embed tidy
        lines.append(f"\n_{summary[:180]}{'…' if len(summary) > 180 else ''}_")

    return "\n".join(lines) or "No details available."


def _build_embed(item: Dict[str, Any], index: int, total: int) -> discord.Embed:
    embed = discord.Embed(
        title=f"🍫 {item.get('name', 'Unknown')}",
        description=_format_item(item),
        color=0x4B2E2E,
    )
    image_url = item.get("logo_url") or item.get("image_url")
    if image_url:
        embed.set_thumbnail(url=image_url)

    url = item.get("url")
    if url:
        embed.url = url

    embed.set_footer(text=f"Result {index + 1} of {total}")
    return embed


# ── Pagination view ───────────────────────────────────────────────────────────

class ChocolatePager(discord.ui.View):
    """Simple prev/next paginator for chocolate results."""

    def __init__(self, items: List[Dict[str, Any]]) -> None:
        super().__init__(timeout=120)
        self.items = items
        self.page = 0
        self._update_buttons()

    def _update_buttons(self) -> None:
        self.prev_btn.disabled = self.page == 0
        self.next_btn.disabled = self.page >= len(self.items) - 1

    def current_embed(self) -> discord.Embed:
        return _build_embed(self.items[self.page], self.page, len(self.items))

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.page -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.current_embed(), view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.page += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.current_embed(), view=self)

    async def on_timeout(self) -> None:
        # Disable buttons when the view expires
        for child in self.children:
            child.disabled = True  # type: ignore[union-attr]


# ── Registration (hybrid loader compatible) ──────────────────────────────────

async def register(bot: discord.Client, data_dir: str) -> None:
    """
    Adds /belgium chocolate_brands as a subcommand of the existing
    /belgium Group registered by belgium.py.

    Must be loaded AFTER belgium.py so the parent group already exists.
    """

    root = bot.tree.get_command("belgium")
    if not isinstance(root, app_commands.Group):
        log.error(
            "belgian_chocolate: '/belgium' group not found. "
            "Make sure belgium.py is loaded before belgian_chocolate.py."
        )
        return

    # Guard against double-registration on reconnect
    if root.get_command("chocolate_brands"):
        return

    @app_commands.command(
        name="chocolate_brands",
        description="Explore Belgian chocolate houses — filter, browse, or get a random pick.",
    )
    @app_commands.describe(
        year_before="Brands founded before this year",
        year_after="Brands founded after this year",
        certification="Filter by certification keyword (e.g. ISO, Fairtrade)",
        production_model="Filter by production model",
        category="Filter by product category",
        random_choice="Return one random brand instead of browsing all results",
    )
    @app_commands.choices(
        production_model=_PRODUCTION_CHOICES,
        category=_CATEGORY_CHOICES,
    )
    async def chocolate_brands(
        interaction: discord.Interaction,
        year_before: Optional[int] = None,
        year_after: Optional[int] = None,
        certification: Optional[str] = None,
        production_model: Optional[str] = None,
        category: Optional[str] = None,
        random_choice: bool = False,
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

        # ── Apply filters ────────────────────────────────────────────────────
        if year_before is not None:
            items = [i for i in items if isinstance(i.get("foundation_year"), int) and i["foundation_year"] < year_before]

        if year_after is not None:
            items = [i for i in items if isinstance(i.get("foundation_year"), int) and i["foundation_year"] > year_after]

        if certification:
            needle = certification.lower()
            items = [
                i for i in items
                if any(needle in c.lower() for c in i.get("certifications", []))
            ]

        if production_model:
            items = [
                i for i in items
                if (i.get("production_model") or "").lower() == production_model.lower()
            ]

        if category:
            items = [
                i for i in items
                if (i.get("category") or i.get("type") or "").lower() == category.lower()
            ]

        if not items:
            await interaction.followup.send(
                "😕 No chocolate brands matched your filters. Try relaxing one of the criteria.",
                ephemeral=True,
            )
            return

        if random_choice:
            items = [random.choice(items)]

        # ── Deduplicate by name (the professional dataset has duplicate entries) ─
        seen: set[str] = set()
        unique: List[Dict[str, Any]] = []
        for i in items:
            key = (i.get("name") or "").lower().strip()
            if key and key not in seen:
                seen.add(key)
                unique.append(i)
        items = unique

        # ── Send paginated result ────────────────────────────────────────────
        view = ChocolatePager(items)
        await interaction.followup.send(
            embed=view.current_embed(),
            view=view if len(items) > 1 else None,
        )

    root.add_command(chocolate_brands)
    log.info("Registered /belgium chocolate_brands")

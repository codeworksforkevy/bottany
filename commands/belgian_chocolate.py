import json
import os
from typing import Any, Dict, List, Optional

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
    # Discord field value limit is 1024; keep buffer for safety.
    out: List[str] = []
    n = 0
    for line in lines:
        if n + len(line) + 1 > max_len:
            break
        out.append(line)
        n += len(line) + 1
    return "\n".join(out)


def _format_brand(b: Dict[str, Any]) -> str:
    name = b.get("name", "(unknown)")
    url = b.get("url", "")
    note = b.get("note", "")
    parts = [f"**{name}**"]
    if note:
        parts.append(note)
    if url:
        parts.append(url)
    return " — ".join(parts)


def _select_brands(reg: Dict[str, Any], category: str, limit: int = 12) -> List[Dict[str, Any]]:
    items = (reg.get("brands", {}) or {}).get(category, []) or []
    out: List[Dict[str, Any]] = []
    for b in items:
        if not isinstance(b, dict):
            continue
        out.append(b)
    return out[: max(1, min(limit, 25))]


class BelgiumGroup(app_commands.Group):
    def __init__(self, data_dir: str):
        super().__init__(name="belgium", description="Belgium: curated culture & food facts (official/trusted links).")
        self._data_dir = data_dir
        self._reg = _load_json(_registry_path(data_dir), {})

    @app_commands.command(name="chocolate", description="Explain Belgian chocolate-making (craft process + official/trusted references).")
    async def chocolate(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Belgian chocolate-making (overview)",
            description=(
                "A practical overview of how Belgian-style pralines and couverture-based chocolates are typically made, "
                "with a focus on technique (tempering, fillings, finishing) and quality cues."
            ),
        )
        steps = [
            "**1) Ingredients & couverture**: high-quality cocoa mass, cocoa butter, sugar (and milk solids for milk chocolate).",
            "**2) Refining & conching**: reduce particle size; develop flavor and smooth mouthfeel.",
            "**3) Tempering**: controlled crystallization (stable cocoa-butter crystals) for snap, gloss, and shelf stability.",
            "**4) Molding & shelling**: cast shells for pralines; drain excess; let set.",
            "**5) Fillings**: ganache, praline paste, caramel, fruit, liqueur; manage water activity for shelf life.",
            "**6) Closing & finishing**: cap molds, demold, enrobe, decorate (cocoa powder, nuts, transfer sheets).",
            "**7) Storage**: cool, dry, stable temperature; avoid condensation and odor absorption.",
        ]
        embed.add_field(name="Process (high level)", value=_chunk(steps), inline=False)

        quality = [
            "**Gloss + clean snap** usually indicates good tempering.",
            "**Bloom** (gray/white haze) often comes from poor tempering or temperature swings.",
            "**Balanced sweetness** and distinct cocoa aroma are common quality targets.",
        ]
        embed.add_field(name="Quality cues", value=_chunk(quality), inline=False)

        src = self._reg.get("sources", {}) or {}
        sources = []
        for s in (src.get("making", []) or []):
            if isinstance(s, str) and s.strip():
                sources.append(s.strip())
        if sources:
            embed.add_field(name="References (official/trusted)", value=_chunk(sources), inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="chocolate_brands", description="Leading Belgian chocolate and chocolate-drink brands (curated, with official/trusted links).")
    @app_commands.describe(category="Which category to list")
    async def chocolate_brands(self, interaction: discord.Interaction, category: Optional[str] = None):
        category = (category or "").strip().lower()
        valid = ["chocolatiers", "mass_market", "industry", "drinks"]
        if category and category not in valid:
            await interaction.response.send_message(
                "Invalid category. Use one of: chocolatiers, mass_market, industry, drinks", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="Belgian chocolate & chocolate-drink brands",
            description=(
                "Curated list of notable Belgian chocolate brands and chocolate beverages. "
                "Use the category option to filter."
            ),
        )

        def add_cat(cat: str, title: str):
            brands = _select_brands(self._reg, cat, limit=12)
            if not brands:
                return
            lines = [_format_brand(b) for b in brands]
            embed.add_field(name=title, value=_chunk(lines), inline=False)

        if not category:
            add_cat("chocolatiers", "Chocolatiers / pralines")
            add_cat("mass_market", "Mass-market chocolate")
            add_cat("industry", "Cocoa/chocolate industry (ingredients)")
            add_cat("drinks", "Chocolate drinks")
        else:
            titles = {
                "chocolatiers": "Chocolatiers / pralines",
                "mass_market": "Mass-market chocolate",
                "industry": "Cocoa/chocolate industry (ingredients)",
                "drinks": "Chocolate drinks",
            }
            add_cat(category, titles[category])

        src = self._reg.get("sources", {}) or {}
        refs = []
        for s in (src.get("brands", []) or []):
            if isinstance(s, str) and s.strip():
                refs.append(s.strip())
        if refs:
            embed.add_field(name="Curation sources", value=_chunk(refs), inline=False)

        await interaction.response.send_message(embed=embed)


async def register_belgium_chocolate(bot: discord.Client, data_dir: str) -> None:
    """Register /belgium commands."""
    grp = BelgiumGroup(data_dir)
    try:
        bot.tree.add_command(grp)
    except Exception:
        # If already registered, ignore.
        pass

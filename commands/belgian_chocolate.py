
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
        if isinstance(b, dict):
            out.append(b)
    return out[: max(1, min(limit, 25))]

class BelgiumGroup(app_commands.Group):
    def __init__(self, data_dir: str):
        super().__init__(name="belgium", description="Belgium: curated culture & food facts.")
        self._data_dir = data_dir
        self._reg = _load_json(_registry_path(data_dir), {})

    @app_commands.command(name="chocolate", description="Explain Belgian chocolate-making.")
    async def chocolate(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Belgian chocolate-making (overview)",
            description="High-level overview of Belgian chocolate craftsmanship."
        )
        steps = [
            "Ingredients & couverture",
            "Refining & conching",
            "Tempering",
            "Molding & shelling",
            "Fillings",
            "Finishing",
            "Storage",
        ]
        embed.add_field(name="Process", value=_chunk(steps), inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="chocolate_brands", description="Belgian chocolate brands.")
    async def chocolate_brands(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Belgian chocolate brands")
        await interaction.response.send_message(embed=embed)

async def register_belgium_chocolate(bot: discord.Client, data_dir: str) -> None:
    grp = BelgiumGroup(data_dir)
    try:
        bot.tree.add_command(grp)
    except Exception:
        pass

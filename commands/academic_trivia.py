import secrets
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List

import discord
from discord import app_commands

from src.utils import safe_join, load_json, validate_pool


def _daily_index(n: int, day_str: str) -> int:
    h = hashlib.sha256(day_str.encode("utf-8")).hexdigest()
    return int(h, 16) % n


def register_academic_trivia(tree: app_commands.CommandTree, data_dir: str) -> None:
    """Register /academictrivia on the provided CommandTree."""
    pool_path = safe_join(data_dir, "academic_trivia_pool.json")

    @app_commands.command(
        name="academictrivia",
        description="Open-licensed academic trivia: daily (deterministic) or random."
    )
    @app_commands.describe(mode="Choose 'daily' (same each day) or 'random'")
    async def academictrivia(interaction: discord.Interaction, mode: str = "daily"):
        pool: Dict[str, Any] = load_json(pool_path, {"version": "1.0.0", "items": []})
        issues = validate_pool(pool)
        if issues:
            await interaction.response.send_message(
                "Pool validation error: " + "; ".join(issues),
                ephemeral=True
            )
            return

        items: List[Dict[str, Any]] = pool.get("items", [])
        if len(items) < 1:
            await interaction.response.send_message(
                "Trivia pool is empty. Build/fill `data/academic_trivia_pool.json` first.",
                ephemeral=True
            )
            return

        mode = (mode or "daily").strip().lower()
        if mode not in ("daily", "random"):
            await interaction.response.send_message(
                "Invalid mode. Use `daily` or `random`.",
                ephemeral=True
            )
            return

        if mode == "daily":
            day_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            idx = _daily_index(len(items), day_str)
            picked = items[idx]
            title = "Academic Daily Trivia"
            footer = f"UTC day: {day_str} • Pool size: {len(items)}"
        else:
            picked = items[secrets.randbelow(len(items))]
            title = "Academic Trivia (Random)"
            footer = f"Pool size: {len(items)}"

        text = (picked.get("text") or "").strip()
        if not text:
            await interaction.response.send_message(
                "Selected trivia item had empty text. Rebuild your pool.",
                ephemeral=True
            )
            return

        emb = discord.Embed(title=title, description=text)
        src_org = picked.get("source_org", "Unknown")
        src_title = picked.get("source_title", "")
        src_url = picked.get("source_url", "")

        if src_title:
            emb.add_field(name="Source", value=f"{src_org} — {src_title}", inline=False)
        else:
            emb.add_field(name="Source", value=src_org, inline=False)

        lic = picked.get("license", "(unknown)")
        emb.add_field(name="License", value=lic, inline=True)

        if src_url:
            emb.add_field(name="Open", value=src_url, inline=False)

        emb.set_footer(text=footer)

        await interaction.response.send_message(embed=emb)

    tree.add_command(academictrivia)

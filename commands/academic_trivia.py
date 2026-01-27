from __future__ import annotations
import os, json, secrets, hashlib
from datetime import datetime, timezone

import discord
from discord import app_commands


def _load_json(path: str, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _daily_index(n: int, day_str: str) -> int:
    h = hashlib.sha256(day_str.encode("utf-8")).hexdigest()
    return int(h, 16) % n

def register_academic_trivia(client: discord.Client, tree: app_commands.CommandTree, data_dir: str) -> None:
    pool_path = os.path.join(data_dir, "academic_trivia_pool.json")

    @app_commands.command(name="academictrivia", description="Open-licensed academic trivia: daily or random.")
    @app_commands.describe(mode="daily (deterministic per UTC day) or random")
    async def academictrivia(interaction: discord.Interaction, mode: str = "daily"):
        pool = _load_json(pool_path, {"items": []})
        items = pool.get("items", []) or []
        if not items:
            await interaction.response.send_message(
                "Trivia pool is empty. Run scripts/build_academic_trivia_pool.py to generate data/academic_trivia_pool.json.",
                ephemeral=True
            )
            return

        mode = (mode or "daily").strip().lower()
        if mode not in ("daily", "random"):
            await interaction.response.send_message("Invalid mode. Use daily or random.", ephemeral=True)
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
            await interaction.response.send_message("Selected item is empty. Rebuild your pool.", ephemeral=True)
            return

        emb = discord.Embed(title=title, description=text)
        src_org = picked.get("source_org","Unknown")
        src_title = picked.get("source_title","")
        src_line = (f"{src_org} — {src_title}").strip(" —")
        emb.add_field(name="Source", value=src_line if src_line else src_org, inline=False)
        lic = picked.get("license","(unknown)")
        emb.add_field(name="License", value=lic[:1024], inline=True)
        if picked.get("source_url"):
            emb.add_field(name="URL", value=picked["source_url"], inline=False)
        emb.set_footer(text=footer)

        await interaction.response.send_message(embed=emb)

    tree.add_command(academictrivia)

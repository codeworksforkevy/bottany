import os
import sys
import json
import asyncio
import hashlib
import secrets
from datetime import datetime, timezone

import discord
from discord import app_commands
from dotenv import load_dotenv


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def load_json(path: str, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_join(base_dir: str, *parts: str) -> str:
    joined = os.path.abspath(os.path.join(base_dir, *parts))
    base_abs = os.path.abspath(base_dir)
    if not joined.startswith(base_abs + os.sep) and joined != base_abs:
        raise ValueError("Unsafe path traversal detected.")
    return joined


def daily_index(n: int, day_str: str) -> int:
    h = hashlib.sha256(day_str.encode("utf-8")).hexdigest()
    return int(h, 16) % n


def get_env(name: str, default: str = "") -> str:
    val = os.getenv(name)
    return val if val else default


def make_command(tree: app_commands.CommandTree, data_dir: str) -> None:
    pool_path = safe_join(data_dir, "academic_trivia_pool.json")

    @app_commands.command(
        name="academictrivia",
        description="Open-licensed academic trivia: daily (deterministic) or random."
    )
    @app_commands.describe(mode="Choose 'daily' (same each day) or 'random'")
    async def academictrivia(interaction: discord.Interaction, mode: str = "daily"):
        pool = load_json(pool_path, {"version": "1.0.0", "items": []})
        items = pool.get("items", [])
        if not isinstance(items, list) or len(items) == 0:
            await interaction.response.send_message(
                "Trivia pool is empty. Fill data/academic_trivia_pool.json first.",
                ephemeral=True
            )
            return

        mode = (mode or "daily").strip().lower()
        if mode not in ("daily", "random"):
            await interaction.response.send_message("Invalid mode. Use daily or random.", ephemeral=True)
            return

        if mode == "daily":
            day_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            idx = daily_index(len(items), day_str)
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
        emb.add_field(name="Source", value=f'{picked.get("source_org","Unknown")} — {picked.get("source_title","")}'.strip(" —"), inline=False)
        emb.add_field(name="License", value=picked.get("license","(unknown)"), inline=True)
        if picked.get("source_url"):
            emb.add_field(name="Open", value=picked["source_url"], inline=False)
        emb.set_footer(text=footer)

        await interaction.response.send_message(embed=emb)

    tree.add_command(academictrivia)


async def run() -> None:
    load_dotenv()

    token = get_env("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("Missing DISCORD_TOKEN.")

    # DATA_DIR default: ./data relative to main.py location (more robust than CWD)
    here = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.abspath(get_env("DATA_DIR", os.path.join(here, "data")))
    ensure_dir(data_dir)

    intents = discord.Intents.none()
    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)

    make_command(tree, data_dir)

    @client.event
    async def on_ready():
        await tree.sync()
        print(f"Logged in as {client.user} (id={client.user.id})")
        print("Slash commands synced: /academictrivia")

    await client.start(token)


if __name__ == "__main__":
    asyncio.run(run())

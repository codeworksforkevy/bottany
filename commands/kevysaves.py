from __future__ import annotations

import json
from pathlib import Path
import discord
from discord import app_commands


DATA_FILE = Path("data/kevysaves.json")


def load_counter():
    if not DATA_FILE.exists():
        return 0
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("count", 0)


def save_counter(value: int):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"count": value}, f)


def register(bot):

    @bot.tree.command(
        name="kevysavesapuppieagain",
        description="Kevy saves another puppie."
    )
    async def kevysaves(interaction: discord.Interaction):

        count = load_counter()
        count += 1
        save_counter(count)

        message = (
            "Kevy saved an another puppie. It wasn't a surprise.\n"
            f"Total saved puppies: {count}"
        )

        await interaction.response.send_message(message)


from __future__ import annotations

import os
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DATA_DIR = "data"

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN not set.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bottany")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

from freegames_enterprise_scheduler import (
    FreeGamesEnterprise,
    register_freegames_admin
)

@bot.event
async def on_ready():
    logger.info(f"Bot ready as {bot.user}")

    if not hasattr(bot, "_enterprise_started"):
        bot.freegames_enterprise = FreeGamesEnterprise(
            bot,
            registry_path=os.path.join(DATA_DIR, "freegames_registry.json")
        )

        register_freegames_admin(bot.tree, bot.freegames_enterprise)

        bot._enterprise_started = True

    await bot.tree.sync()

if __name__ == "__main__":
    bot.run(TOKEN)

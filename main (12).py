
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
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---- IMPORT ALL COMMAND MODULES HERE ----
from freegames_enterprise_scheduler import (
    FreeGamesEnterprise,
    register_freegames_admin
)

# IMPORTANT:
# If /kevy is defined in another module, make sure it is imported here
# Example:
# from kevy import register_kevy
# register_kevy(bot.tree)

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

    try:
        synced = await bot.tree.sync()
        logger.info(f"Slash commands synced: {[cmd.name for cmd in synced]}")
    except Exception as e:
        logger.exception(f"Slash sync failed: {e}")


if __name__ == "__main__":
    bot.run(TOKEN)


from __future__ import annotations

import os
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN not set.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bottany")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---- MANUAL COMMAND IMPORTS (NO load_extension) ----
# These imports ensure decorators run and slash commands register.

import commands.kevy
import commands.weather
import commands.history_of_the_consoles
import commands.free_games

# Add any other command modules here if needed


@bot.event
async def on_ready():
    logger.info(f"Bot ready as {bot.user}")

    try:
        synced = await bot.tree.sync()
        logger.info(f"Slash commands synced: {[cmd.name for cmd in synced]}")
    except Exception as e:
        logger.exception(f"Slash sync failed: {e}")


if __name__ == "__main__":
    bot.run(TOKEN)

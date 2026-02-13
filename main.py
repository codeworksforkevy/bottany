
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

# ---- IMPORT REGISTER FUNCTIONS ----
from commands.kevy import register_kevy
# If other commands use the same pattern, import them here:
# from commands.weather import register_weather
# from commands.history_of_the_consoles import register_history
# from commands.free_games import register_free_games


@bot.event
async def on_ready():
    logger.info(f"Bot ready as {bot.user}")

    # Prevent duplicate registration on reconnect
    if not hasattr(bot, "_commands_registered"):
        register_kevy(bot)
        # register_weather(bot)
        # register_history(bot)
        # register_free_games(bot)

        bot._commands_registered = True

    try:
        synced = await bot.tree.sync()
        logger.info(f"Slash commands synced: {[cmd.name for cmd in synced]}")
    except Exception as e:
        logger.exception(f"Slash sync failed: {e}")


if __name__ == "__main__":
    bot.run(TOKEN)

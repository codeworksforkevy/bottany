
from __future__ import annotations

import os
import logging
import asyncio
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

# ---- AUTO LOAD ALL COGS FROM commands/ ----
async def load_extensions():
    if not os.path.isdir("./commands"):
        logger.warning("No commands/ directory found.")
        return

    for filename in os.listdir("./commands"):
        if filename.endswith(".py"):
            module = filename[:-3]
            try:
                await bot.load_extension(f"commands.{module}")
                logger.info(f"Loaded extension: commands.{module}")
            except Exception as e:
                logger.exception(f"Failed to load extension {module}: {e}")


@bot.event
async def on_ready():
    logger.info(f"Bot ready as {bot.user}")
    try:
        synced = await bot.tree.sync()
        logger.info(f"Slash commands synced: {[cmd.name for cmd in synced]}")
    except Exception as e:
        logger.exception(f"Slash sync failed: {e}")


async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())

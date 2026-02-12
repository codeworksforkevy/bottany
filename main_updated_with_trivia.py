
from __future__ import annotations

import os
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv

# ---- Load environment ----
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DATA_DIR = "data"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bottany")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---- Free Games Enterprise ----
from freegames_enterprise_scheduler import (
    FreeGamesEnterprise,
    register_freegames_admin
)

# ---- Modular Commands ----
from commands.awards import register_awards
from commands.trivia import register_trivia  # NEW


@bot.event
async def on_ready():
    logger.info("Bot ready.")

    if not hasattr(bot, "_enterprise_started"):
        bot.freegames_enterprise = FreeGamesEnterprise(
            bot,
            registry_path=os.path.join(DATA_DIR, "freegames_registry.json")
        )

        # Register slash commands
        register_freegames_admin(bot.tree, bot.freegames_enterprise)
        register_awards(bot.tree)
        register_trivia(bot.tree)  # NEW

        bot._enterprise_started = True

    await bot.tree.sync()


if __name__ == "__main__":
    bot.run(TOKEN)

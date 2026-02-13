
from __future__ import annotations

import os
import logging
import importlib
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


def auto_register_commands(bot):
    if not os.path.isdir("commands"):
        logger.warning("commands/ directory not found.")
        return

    for file in os.listdir("commands"):
        if file.endswith(".py"):
            module_name = f"commands.{file[:-3]}"
            try:
                module = importlib.import_module(module_name)
                for attr in dir(module):
                    if attr.startswith("register"):
                        register_func = getattr(module, attr)
                        if callable(register_func):
                            register_func(bot)
                            logger.info(f"Registered via {attr} from {module_name}")
            except Exception as e:
                logger.exception(f"Failed loading {module_name}: {e}")


@bot.event
async def on_ready():
    logger.info(f"Bot ready as {bot.user}")

    if not hasattr(bot, "_commands_registered"):
        auto_register_commands(bot)
        bot._commands_registered = True

    try:
        synced = await bot.tree.sync()
        logger.info(f"Slash commands synced: {[cmd.name for cmd in synced]}")
    except Exception as e:
        logger.exception(f"Slash sync failed: {e}")


if __name__ == "__main__":
    bot.run(TOKEN)

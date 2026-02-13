
import os
import asyncio
import logging
import discord
from discord.ext import commands
import pkgutil
import importlib
import inspect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bottany")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


# -----------------------------
# SAFE REGISTER CALLER
# -----------------------------
async def safe_register(func, bot, data_dir):
    if not func:
        return

    try:
        sig = inspect.signature(func)
        params = sig.parameters

        if len(params) == 2:
            result = func(bot, data_dir)
        elif len(params) == 1:
            result = func(bot)
        else:
            result = func()

        if asyncio.iscoroutine(result):
            await result

    except Exception as e:
        logger.warning("Register failed for %s: %s", func.__name__, e)


# -----------------------------
# AUTO-LOADER (modular future-safe)
# -----------------------------
async def auto_load_command_modules(bot, data_dir):
    try:
        import commands
    except Exception:
        logger.warning("commands package not found.")
        return

    for _, module_name, _ in pkgutil.iter_modules(commands.__path__):
        try:
            module = importlib.import_module(f"commands.{module_name}")

            if hasattr(module, "register"):
                register_func = getattr(module, "register")
                await safe_register(register_func, bot, data_dir)
                logger.info("Auto-loaded module: commands.%s", module_name)

        except Exception as e:
            logger.warning("Auto-load failed for commands.%s: %s", module_name, e)


@bot.event
async def on_ready():
    logger.info("Bot ready as %s", bot.user)

    # Legacy compatibility imports (optional)
    try:
        from commands.belgium_beverages import register_belgium_beverages
        await safe_register(register_belgium_beverages, bot, DATA_DIR)
    except Exception:
        pass

    try:
        from commands.belgian_chocolate import register_belgium_chocolate
        await safe_register(register_belgium_chocolate, bot, DATA_DIR)
    except Exception:
        pass

    try:
        from commands.freegames import register
        await safe_register(register, bot, DATA_DIR)
    except Exception:
        pass

    try:
        from commands.awards import register_awards
        await safe_register(register_awards, bot, DATA_DIR)
    except Exception:
        pass

    # Auto-load any module with async def register(bot, data_dir)
    await auto_load_command_modules(bot, DATA_DIR)

    try:
        synced = await bot.tree.sync()
        logger.info("Synced %s commands.", len(synced))
    except Exception as e:
        logger.error("Sync failed: %s", e)


@bot.tree.command(name="ping", description="Health check")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong.")


if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"))

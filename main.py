
import os
import asyncio
import logging
import discord
from discord.ext import commands
import pkgutil
import importlib
import inspect

try:
    from commands.belgium_beverages import register_belgium_beverages
except Exception:
    register_belgium_beverages = None

try:
    from commands.belgian_chocolate import register_belgium_chocolate
except Exception:
    register_belgium_chocolate = None

try:
    from commands.free_games import register_free_games
except Exception:
    register_free_games = None

try:
    from commands.awards import register_awards
except Exception:
    register_awards = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bottany")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

async def _maybe_await(func, *args):
    if not func:
        return
    res = func(*args)
    if asyncio.iscoroutine(res):
        await res

# -----------------------------
# AUTO-LOADER (non-destructive)
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

                if inspect.iscoroutinefunction(register_func):
                    await register_func(bot, data_dir)
                else:
                    res = register_func(bot, data_dir)
                    if inspect.isawaitable(res):
                        await res

                logger.info("Auto-loaded module: commands.%s", module_name)

        except Exception as e:
            logger.warning("Auto-load failed for commands.%s: %s", module_name, e)

@bot.event
async def on_ready():
    logger.info("Bot ready as %s", bot.user)

    if register_belgium_beverages:
        await _maybe_await(register_belgium_beverages, bot, DATA_DIR)

    if register_belgium_chocolate:
        await _maybe_await(register_belgium_chocolate, bot, DATA_DIR)

    if register_free_games:
        await _maybe_await(register_free_games, bot, DATA_DIR)

    if register_awards:
        await _maybe_await(register_awards, bot, DATA_DIR)

    # 🔥 NEW: Auto-load future modules
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

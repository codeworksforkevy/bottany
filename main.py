
import os
import logging
import asyncio
import discord
from discord.ext import commands
from discord import app_commands

# --- Optional command imports ---
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

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bottany")

# --- Bot setup ---
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


async def _maybe_await(func, *args):
    if func is None:
        return
    res = func(*args)
    if asyncio.iscoroutine(res):
        await res


@bot.event
async def on_ready():
    logger.info("Bot ready as %s", bot.user)

    # --- Register Belgium (order matters) ---
    if register_belgium_beverages:
        await _maybe_await(register_belgium_beverages, bot, DATA_DIR)

    if register_belgium_chocolate:
        await _maybe_await(register_belgium_chocolate, bot, DATA_DIR)

    # --- Free Games ---
    if register_free_games:
        await _maybe_await(register_free_games, bot, DATA_DIR)

    # --- Awards ---
    if register_awards:
        await _maybe_await(register_awards, bot, DATA_DIR)

    # --- Global sync ---
    try:
        synced = await bot.tree.sync()
        logger.info("Synced %s global commands.", len(synced))
    except Exception as e:
        logger.error("Command sync failed: %s", e)


@bot.tree.command(name="ping", description="Health check")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong.")


if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    bot.run(TOKEN)

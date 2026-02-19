import os
import asyncio
import logging
import discord
from discord.ext import commands
import pkgutil
import importlib
import inspect
from pathlib import Path

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
ENV = os.getenv("ENV", "dev")
OWNER_ID = int(os.getenv("BOT_OWNER_ID", "0"))
GUILD_ID = int(os.getenv("DEV_GUILD_ID", "1446560723122520207"))

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL")

# -------------------------------------------------
# LOGGING
# -------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bottany")

# -------------------------------------------------
# POSTGRES INIT
# -------------------------------------------------
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set.")

from services.trivia_memory_pg import init_db
init_db()
logger.info("✅ PostgreSQL memory layer initialized.")

# -------------------------------------------------
# INTENTS
# -------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True


# -------------------------------------------------
# BOT CLASS
# -------------------------------------------------
class BottanyBot(commands.Bot):

    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents
        )

        self.twitch_layer = None

    # -------------------------------------------------
    # SAFE REGISTER
    # -------------------------------------------------
    async def safe_register(self, func):
        if not callable(func):
            return

        try:
            sig = inspect.signature(func)
            param_names = list(sig.parameters.keys())

            result = None

            if param_names == ["bot", "data_dir"]:
                result = func(self, DATA_DIR)
            elif param_names == ["bot"]:
                result = func(self)
            elif len(param_names) == 0:
                result = func()
            else:
                logger.info(
                    "Skipped register %s (unsupported signature: %s)",
                    func.__name__,
                    param_names
                )
                return

            if asyncio.iscoroutine(result):
                await result

        except Exception as e:
            logger.warning("Register failed for %s: %s", func.__name__, e)

    # -------------------------------------------------
    # AUTO MODULE LOADER
    # -------------------------------------------------
    async def auto_load_command_modules(self):
        try:
            import commands
        except Exception:
            logger.warning("commands package not found.")
            return

        for _, module_name, _ in pkgutil.iter_modules(commands.__path__):
            try:
                module = importlib.import_module(f"commands.{module_name}")

                for attr in dir(module):
                    if attr.startswith("register"):
                        register_func = getattr(module, attr)
                        await self.safe_register(register_func)
                        logger.info(
                            "Processed %s in commands.%s",
                            attr,
                            module_name
                        )

            except Exception as e:
                logger.warning(
                    "Auto-load failed for commands.%s: %s",
                    module_name,
                    e
                )

    # -------------------------------------------------
    # SETUP HOOK
    # -------------------------------------------------
    async def setup_hook(self):

        await self.auto_load_command_modules()

        try:
            if ENV == "dev":
                guild = discord.Object(id=GUILD_ID)
                synced = await self.tree.sync(guild=guild)
                logger.info("✅ Dev guild sync complete (%s commands).", len(synced))
            else:
                synced = await self.tree.sync()
                logger.info("🌍 Global sync complete (%s commands).", len(synced))

        except Exception as e:
            logger.error("Sync failed: %s", e)

    async def on_ready(self):
        logger.info("Bot ready as %s", self.user)


# -------------------------------------------------
# BOT INSTANCE
# -------------------------------------------------
bot = BottanyBot()


# -------------------------------------------------
# HEALTH CHECK
# -------------------------------------------------
@bot.tree.command(name="ping", description="Health check")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong.")


# -------------------------------------------------
# OWNER GLOBAL SYNC
# -------------------------------------------------
@bot.tree.command(name="sync_global", description="Owner: force global sync")
async def sync_global(interaction: discord.Interaction):

    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("Not authorized.", ephemeral=True)
        return

    synced = await bot.tree.sync()
    await interaction.response.send_message(
        f"🌍 Global sync complete ({len(synced)} commands).",
        ephemeral=True
    )


# -------------------------------------------------
# RUN
# -------------------------------------------------
if __name__ == "__main__":

    token = os.getenv("DISCORD_TOKEN")

    if not token:
        raise RuntimeError("DISCORD_TOKEN is not set.")

    bot.run(token)


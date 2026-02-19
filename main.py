from __future__ import annotations

import os
import asyncio
import logging
import signal
import pkgutil
import importlib
import inspect
from pathlib import Path

import discord
from discord.ext import commands
from aiohttp import web

# -------------------------------------------------
# ENV
# -------------------------------------------------

ENV = os.getenv("ENV", "dev").lower()
OWNER_ID = int(os.getenv("BOT_OWNER_ID", "0"))
GUILD_ID = int(os.getenv("DEV_GUILD_ID", "0"))

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set.")

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set.")

# -------------------------------------------------
# STRUCTURED LOGGING
# -------------------------------------------------

from services.logging_config import setup_logging
from services.telemetry import capture_exception

setup_logging()
logger = logging.getLogger("bottany")

logger.info(f"Booting Bottany | ENV={ENV}")

# -------------------------------------------------
# POSTGRES INIT
# -------------------------------------------------

from services.trivia_memory_pg import init_db
init_db()
logger.info("PostgreSQL memory layer initialized.")

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
        super().__init__(command_prefix="!", intents=intents)

        if ENV == "production":
            self._install_sync_guard()

    # -------------------------------------------------
    # SYNC GUARD (PRODUCTION ONLY)
    # -------------------------------------------------

    def _install_sync_guard(self):

        original_sync = self.tree.sync

        async def guarded_sync(*args, **kwargs):
            if not getattr(self, "_sync_allowed", False):
                logger.warning("Blocked tree.sync in production.")
                return []
            return await original_sync(*args, **kwargs)

        self.tree.sync = guarded_sync

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
            capture_exception(e, context="safe_register")

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
                        await self.safe_register(getattr(module, attr))

                logger.info("Loaded commands.%s", module_name)

            except Exception as e:
                capture_exception(e, context=f"auto_load:{module_name}")

    # -------------------------------------------------
    # SETUP HOOK
    # -------------------------------------------------

    async def setup_hook(self):

        await self.auto_load_command_modules()

        try:
            if ENV == "dev" and GUILD_ID:
                guild = discord.Object(id=GUILD_ID)
                synced = await self.tree.sync(guild=guild)
                logger.info("Dev guild sync (%s commands).", len(synced))
            elif ENV == "production":
                logger.info("Production mode — global sync guarded.")
            else:
                synced = await self.tree.sync()
                logger.info("Global sync (%s commands).", len(synced))

        except Exception as e:
            capture_exception(e, context="tree_sync")

        # GLOBAL TREE ERROR HANDLER
        @self.tree.error
        async def on_app_command_error(interaction, error):

            capture_exception(
                error,
                context="slash_command",
                user_id=interaction.user.id if interaction.user else None,
                guild_id=interaction.guild_id,
            )

            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "An internal error occurred.",
                    ephemeral=True
                )

    async def on_ready(self):
        logger.info("Bot ready as %s", self.user)


bot = BottanyBot()


# -------------------------------------------------
# BASIC HEALTH SLASH
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

    if ENV == "production":
        bot._sync_allowed = True

    synced = await bot.tree.sync()

    if ENV == "production":
        bot._sync_allowed = False

    await interaction.response.send_message(
        f"Global sync complete ({len(synced)} commands).",
        ephemeral=True
    )


# -------------------------------------------------
# HEALTH HTTP ENDPOINT (Railway)
# -------------------------------------------------

async def health(request):
    return web.json_response({"status": "ok", "env": ENV})

async def start_health_server():
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", "8080"))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Health endpoint running on port {port}")


# -------------------------------------------------
# GRACEFUL SHUTDOWN
# -------------------------------------------------

async def shutdown():
    logger.info("Graceful shutdown initiated.")
    await bot.close()

def install_signal_handlers():
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig,
            lambda: asyncio.create_task(shutdown())
        )


# -------------------------------------------------
# MAIN
# -------------------------------------------------

async def main():

    install_signal_handlers()
    await start_health_server()

    await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        capture_exception(e, context="main_boot")

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

# =================================================
# ENV
# =================================================

ENV = os.getenv("ENV", "dev").lower()
OWNER_ID = int(os.getenv("BOT_OWNER_ID", "0"))
GUILD_ID = int(os.getenv("DEV_GUILD_ID", "0"))
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set.")

# =================================================
# LOGGING
# =================================================

from services.logging_config import setup_logging
from services.telemetry import capture_exception

setup_logging()
logger = logging.getLogger("bottany")

logger.info("Booting Bottany Core | ENV=%s", ENV)

# =================================================
# INTENTS
# =================================================

intents = discord.Intents.default()
intents.message_content = True

# =================================================
# BOT CLASS
# =================================================

class BottanyBot(commands.Bot):

    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents
        )

    # -------------------------------------------------
    # AUTO MODULE LOADER
    # -------------------------------------------------

    async def load_command_modules(self):

        try:
            import commands
        except Exception:
            logger.warning("commands package not found.")
            return

        for _, module_name, _ in pkgutil.iter_modules(commands.__path__):

            full_name = f"commands.{module_name}"

            try:
                module = importlib.import_module(full_name)

                if not hasattr(module, "register"):
                    logger.warning("%s has no register() function", full_name)
                    continue

                func = module.register
                sig = list(inspect.signature(func).parameters.keys())

                result = None

                if sig == ["bot", "data_dir"]:
                    result = func(self, DATA_DIR)

                elif sig == ["bot"]:
                    result = func(self)

                elif sig == ["tree"]:
                    result = func(self.tree)

                elif len(sig) == 0:
                    result = func()

                else:
                    logger.warning(
                        "%s unsupported register signature: %s",
                        full_name,
                        sig
                    )
                    continue

                if asyncio.iscoroutine(result):
                    await result

                logger.info("Registered %s", full_name)

            except Exception as e:
                capture_exception(e, context=f"load:{full_name}")

    # -------------------------------------------------
    # SETUP HOOK
    # -------------------------------------------------

    async def setup_hook(self):

        await self.load_command_modules()

        try:
            if ENV == "dev" and GUILD_ID:
                guild = discord.Object(id=GUILD_ID)

                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)

                logger.info("Dev guild sync complete (%s commands).", len(synced))

            elif ENV == "production":
                logger.info("Production mode — global sync disabled by default.")

            else:
                synced = await self.tree.sync()
                logger.info("Global sync complete (%s commands).", len(synced))

        except Exception as e:
            capture_exception(e, context="tree_sync")

        # -------------------------------------------------
        # GLOBAL SLASH ERROR HANDLER
        # -------------------------------------------------

        @self.tree.error
        async def on_app_command_error(interaction, error):

            capture_exception(
                error,
                context="slash_command",
                user_id=interaction.user.id if interaction.user else None,
                guild_id=interaction.guild_id
            )

            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "An internal error occurred.",
                        ephemeral=True
                    )
            except Exception:
                pass

    async def on_ready(self):
        logger.info("Bot ready as %s", self.user)

# =================================================
# BOT INSTANCE
# =================================================

bot = BottanyBot()

# =================================================
# BASIC HEALTH COMMAND
# =================================================

@bot.tree.command(name="ping", description="Health check")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong.")

# =================================================
# OWNER GLOBAL SYNC
# =================================================

@bot.tree.command(name="sync_global", description="Owner: force global sync")
async def sync_global(interaction: discord.Interaction):

    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message(
            "Not authorized.",
            ephemeral=True
        )
        return

    if ENV != "production":
        await interaction.response.send_message(
            "Global sync is only relevant in production.",
            ephemeral=True
        )
        return

    try:
        synced = await bot.tree.sync()
        await interaction.response.send_message(
            f"Global sync complete ({len(synced)} commands).",
            ephemeral=True
        )
    except Exception as e:
        capture_exception(e, context="manual_sync")
        await interaction.response.send_message(
            "Sync failed. Check logs.",
            ephemeral=True
        )

# =================================================
# GRACEFUL SHUTDOWN
# =================================================

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

# =================================================
# MAIN
# =================================================

async def main():
    install_signal_handlers()
    await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        capture_exception(e, context="main_boot")

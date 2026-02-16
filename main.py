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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


class BottanyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents
        )

    # -----------------------------
    # SAFE REGISTER CALLER
    # -----------------------------
    async def safe_register(self, func):
        if not func:
            return

        try:
            sig = inspect.signature(func)
            params = sig.parameters

            if len(params) == 2:
                result = func(self, DATA_DIR)
            elif len(params) == 1:
                result = func(self)
            else:
                result = func()

            if asyncio.iscoroutine(result):
                await result

        except Exception as e:
            logger.warning("Register failed for %s: %s", func.__name__, e)

    # -----------------------------
    # AUTO-LOADER
    # -----------------------------
    async def auto_load_command_modules(self):
        try:
            import commands
        except Exception:
            logger.warning("commands package not found.")
            return

        for _, module_name, _ in pkgutil.iter_modules(commands.__path__):
            try:
                module = importlib.import_module(f"commands.{module_name}")

found_register = False

for attr in dir(module):
    if attr.startswith("register"):
        register_func = getattr(module, attr)
        await self.safe_register(register_func)
        logger.info(
            "Registered via %s in commands.%s",
            attr,
            module_name
        )
        found_register = True

if not found_register:
    logger.warning(
        "No register* function found in commands.%s",
        module_name
    )


            except Exception as e:
                logger.warning("Auto-load failed for commands.%s: %s", module_name, e)

    # -----------------------------
    # SETUP HOOK (CRITICAL)
    # -----------------------------
    async def setup_hook(self):
        # 1️⃣ Load all modules FIRST
        await self.auto_load_command_modules()

        # 2️⃣ THEN sync commands
        try:
            synced = await self.tree.sync()
            logger.info("Synced %s commands.", len(synced))
        except Exception as e:
            logger.error("Sync failed: %s", e)

    async def on_ready(self):
        logger.info("Bot ready as %s", self.user)


bot = BottanyBot()


# -----------------------------
# CORE HEALTH CHECK COMMAND
# -----------------------------
@bot.tree.command(name="ping", description="Health check")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong.")


if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"))

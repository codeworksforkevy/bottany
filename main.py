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

# 🔥 YOUR GUILD ID
GUILD_ID = 1446560723122520207


class BottanyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents
        )

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
            logger.warning(
                "Register failed for %s: %s",
                func.__name__,
                e
            )

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
                    if not attr.startswith("register"):
                        continue

                    register_func = getattr(module, attr)

                    if not callable(register_func):
                        continue

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
    # SETUP HOOK (GUILD SYNC)
    # -------------------------------------------------
    async def setup_hook(self):
        await self.auto_load_command_modules()

        guild = discord.Object(id=GUILD_ID)

        try:
            synced = await self.tree.sync(guild=guild)
            logger.info("Synced %s guild commands.", len(synced))
        except Exception as e:
            logger.error("Guild sync failed: %s", e)

    async def on_ready(self):
        logger.info("Bot ready as %s", self.user)


bot = BottanyBot()


# -------------------------------------------------
# CORE HEALTH CHECK
# -------------------------------------------------
@bot.tree.command(name="ping", description="Health check")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong.")


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")

    if not token:
        raise RuntimeError("DISCORD_TOKEN is not set.")

    bot.run(token)

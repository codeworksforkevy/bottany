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
ENV = os.getenv("ENV", "dev")  # dev | production
OWNER_ID = int(os.getenv("BOT_OWNER_ID", "0"))
GUILD_ID = int(os.getenv("DEV_GUILD_ID", "1446560723122520207"))

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------
# SQLITE MEMORY INIT
# -------------------------------------------------
try:
    from services.trivia_memory import init_db
    init_db()
except Exception as e:
    print(f"[WARN] SQLite init failed: {e}")

# -------------------------------------------------
# LOGGING
# -------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bottany")

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

        self._sync_done = False
        self._original_sync = self.tree.sync
        self._install_sync_guard()

        self.twitch_layer = None

    # -------------------------------------------------
    # 🔒 GLOBAL SYNC GUARD
    # -------------------------------------------------
    def _install_sync_guard(self):

        async def guarded_sync(*args, **kwargs):
            guild = kwargs.get("guild")

            if guild is None:
                logger.warning("🚨 BLOCKED global sync attempt.")
                return []

            return await self._original_sync(*args, **kwargs)

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
                    if not attr.startswith("register"):
                        continue

                    register_func = getattr(module, attr)

                    if callable(register_func):
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
    # TWITCH PRE-WARM
    # -------------------------------------------------
    async def _prewarm_twitch(self):

        if not self.twitch_layer:
            return

        cid = os.getenv("TWITCH_CLIENT_ID")
        tok = os.getenv("TWITCH_APP_TOKEN")

        if not cid or not tok:
            logger.info("Twitch prewarm skipped (missing credentials).")
            return

        headers = {
            "Client-ID": cid,
            "Authorization": f"Bearer {tok}"
        }

        url = "https://api.twitch.tv/helix/chat/badges/global"

        try:
            await self.twitch_layer.fetch("badges", url, headers)
            logger.info("🔥 Twitch badges pre-warmed.")
        except Exception as e:
            logger.warning("Prewarm failed: %s", e)

    # -------------------------------------------------
    # SETUP HOOK
    # -------------------------------------------------
    async def setup_hook(self):

        # Load Twitch data layer
        try:
            from services.twitch_data_layer import TwitchDataLayer
            self.twitch_layer = TwitchDataLayer(DATA_DIR)
        except Exception as e:
            logger.warning("TwitchDataLayer not available: %s", e)

        await self.auto_load_command_modules()

        if self._sync_done:
            return

        try:
            if ENV == "dev":
                guild = discord.Object(id=GUILD_ID)
                synced = await self._original_sync(guild=guild)
                logger.info("✅ Dev guild sync complete (%s commands).", len(synced))
            else:
                logger.info("🛡 Production mode: global sync disabled.")

            self._sync_done = True

        except Exception as e:
            logger.error("Sync failed: %s", e)

        await self._prewarm_twitch()

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
# OWNER-ONLY GLOBAL SYNC
# -------------------------------------------------
@bot.tree.command(name="sync_global", description="Owner: perform global sync")
async def sync_global(interaction: discord.Interaction):

    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("Not authorized.", ephemeral=True)
        return

    synced = await bot._original_sync()
    await interaction.response.send_message(
        f"🌍 Global sync complete ({len(synced)} commands).",
        ephemeral=True
    )


# -------------------------------------------------
# TWITCH METRICS
# -------------------------------------------------
@bot.tree.command(name="twitch_metrics", description="Owner: Twitch API metrics")
async def twitch_metrics(interaction: discord.Interaction):

    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("Not authorized.", ephemeral=True)
        return

    if not bot.twitch_layer:
        await interaction.response.send_message(
            "Twitch layer not initialized.",
            ephemeral=True
        )
        return

    metrics = bot.twitch_layer.metrics()

    embed = discord.Embed(title="Twitch API Metrics")

    for key, value in metrics.items():
        embed.add_field(name=key, value=str(value), inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)


# -------------------------------------------------
# RUN
# -------------------------------------------------
if __name__ == "__main__":

    token = os.getenv("DISCORD_TOKEN")

    if not token:
        raise RuntimeError("DISCORD_TOKEN is not set.")

    bot.run(token)




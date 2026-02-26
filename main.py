from __future__ import annotations

import os
import asyncio
import logging
import signal
import pkgutil
import importlib
import inspect
import time
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
# TWITCH INTELLIGENCE IMPORTS
# =================================================

from services.telemetry_service import TelemetryService
from services.twitch_api import TwitchAPI
from services.monitor import TwitchMonitor
from workers.background_scheduler import BackgroundScheduler
from core.structured_logger import StructuredLogger
from core.cache_manager import CacheManager

from services.stream_snapshot_engine import StreamSnapshotEngine
from services.drops_monitor import DropsLifecycleMonitor
from services.anomaly_detector import ViewerAnomalyDetector
from services.prediction_engine import PredictionEngine
from services.trend_analytics_engine import TrendAnalyticsEngine
from services.stream_intelligence_engine import StreamIntelligenceEngine
from services.adaptive_tracking_engine import AdaptiveTrackingEngine

# =================================================
# BOT CLASS
# =================================================

class BottanyBot(commands.Bot):

    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

        self.start_time = time.time()

        # -------------------------------------------------
        # CORE SERVICES
        # -------------------------------------------------

        self.telemetry = TelemetryService()
        self.twitch_api = TwitchAPI()
        self.intelligence_logger = StructuredLogger()

        # -------------------------------------------------
        # CACHE LAYERS
        # -------------------------------------------------

        self.stream_cache = CacheManager("data/stream_snapshot_cache.json")
        self.drops_cache = CacheManager("data/drops_cache.json")

        # -------------------------------------------------
        # ANALYTICS ENGINES
        # -------------------------------------------------

        self.anomaly_detector = ViewerAnomalyDetector(
            telemetry=self.telemetry,
            logger=self.intelligence_logger,
            threshold=2.5
        )

        self.snapshot_engine = StreamSnapshotEngine(
            api=self.twitch_api,
            telemetry=self.telemetry,
            cache=self.stream_cache,
            logger=self.intelligence_logger,
            anomaly_detector=self.anomaly_detector,
            snapshot_ttl=120
        )

        self.drops_monitor = DropsLifecycleMonitor(
            api=self.twitch_api,
            telemetry=self.telemetry,
            cache=self.drops_cache,
            logger=self.intelligence_logger

        )

        self.predictor = PredictionEngine()
        self.trend_engine = TrendAnalyticsEngine()
        self.adaptive_engine = AdaptiveTrackingEngine()

        self.intelligence_engine = StreamIntelligenceEngine(
            telemetry=self.telemetry,
            logger=self.intelligence_logger,
            predictor=self.predictor,
            trend_engine=self.trend_engine
        )

        # -------------------------------------------------
        # MONITOR (ORCHESTRATOR)
        # -------------------------------------------------

        self.monitor = TwitchMonitor(
            api=self.twitch_api,
            telemetry=self.telemetry,
            logger=self.intelligence_logger,
            snapshot_engine=self.snapshot_engine,
            drops_monitor=self.drops_monitor,
            intelligence_engine=self.intelligence_engine,
            adaptive_engine=self.adaptive_engine
        )

        # -------------------------------------------------
        # BACKGROUND SCHEDULER
        # -------------------------------------------------

        self.scheduler = BackgroundScheduler(
            monitor=self.monitor,
            interval=300
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
                logger.info("Production mode — global sync disabled.")
            else:
                synced = await self.tree.sync()
                logger.info("Global sync complete (%s commands).", len(synced))

        except Exception as e:
            capture_exception(e, context="tree_sync")

    # -------------------------------------------------
    # READY EVENT
    # -------------------------------------------------

    async def on_ready(self):

        logger.info("Bot ready as %s", self.user)
        logger.info("Guild count: %s", len(self.guilds))

        try:
            await self.telemetry.init()
            logger.info("Telemetry database connected.")

            self.loop.create_task(self.scheduler.start())
            logger.info("Twitch Intelligence scheduler started.")

        except Exception as e:
            capture_exception(e, context="intelligence_bootstrap")

# =================================================
# BOT INSTANCE
# =================================================

bot = BottanyBot()

# =================================================
# BASIC HEALTH COMMAND
# =================================================

@bot.tree.command(name="ping", description="Health check")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"Pong. Latency: {latency} ms")

# =================================================
# GRACEFUL SHUTDOWN
# =================================================

async def shutdown():
    logger.info("Graceful shutdown initiated.")

    try:
        await bot.twitch_api.close()
    except Exception:
        pass

    try:
        await bot.telemetry.close()
    except Exception:
        pass

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

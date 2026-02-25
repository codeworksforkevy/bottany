import time
from typing import List

from core.cache_manager import CacheManager
from services.stream_snapshot_engine import StreamSnapshotEngine
from services.anomaly_detector import ViewerAnomalyDetector
from services.drops_monitor import DropsLifecycleMonitor


class TwitchMonitor:

    def __init__(self, api, telemetry, logger):

        self.api = api
        self.telemetry = telemetry
        self.logger = logger

        # -------------------------------------------------
        # STREAM SNAPSHOT SYSTEM
        # -------------------------------------------------

        self.stream_cache = CacheManager("data/stream_snapshot_cache.json")

        self.anomaly_detector = ViewerAnomalyDetector(
            telemetry=telemetry,
            logger=logger,
            threshold=2.5
        )

        self.snapshot_engine = StreamSnapshotEngine(
            api=api,
            telemetry=telemetry,
            cache=self.stream_cache,
            logger=logger,
            anomaly_detector=self.anomaly_detector,
            snapshot_ttl=120
        )

        # -------------------------------------------------
        # DROPS LIFECYCLE SYSTEM
        # -------------------------------------------------

        self.drops_cache = CacheManager("data/drops_cache.json")

        self.drops_monitor = DropsLifecycleMonitor(
            api=api,
            cache=self.drops_cache,
            logger=logger
        )

        # -------------------------------------------------
        # TRACKED ENTITIES
        # -------------------------------------------------

        self.tracked_streams: List[str] = [
            "xqc",
            "tarik",
            "shroud"
        ]

        self.tracked_games: List[str] = [
            "Valorant",
            "League of Legends",
            "Fortnite"
        ]

    # -------------------------------------------------
    # MAIN CYCLE
    # -------------------------------------------------

    async def run_cycle(self):

        cycle_start = time.time()

        # -------------------------------------------------
        # STREAM SNAPSHOTS
        # -------------------------------------------------

        for user in self.tracked_streams:
            try:
                await self.snapshot_engine.process_stream(user)
            except Exception as e:
                self.logger.log(
                    "stream_monitor_error",
                    {"user": user, "error": str(e)}
                )

        # -------------------------------------------------
        # DROPS MONITORING
        # -------------------------------------------------

        for game in self.tracked_games:
            try:
                await self.drops_monitor.check_game(game)
            except Exception as e:
                self.logger.log(
                    "drops_monitor_error",
                    {"game": game, "error": str(e)}
                )

        # -------------------------------------------------
        # CYCLE METRICS
        # -------------------------------------------------

        duration = round(time.time() - cycle_start, 3)

        self.logger.log(
            "monitor_cycle",
            {
                "status": "completed",
                "streams_checked": len(self.tracked_streams),
                "games_checked": len(self.tracked_games),
                "duration_seconds": duration
            }
        )

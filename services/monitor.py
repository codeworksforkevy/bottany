import time
from typing import List


class TwitchMonitor:

    def __init__(
        self,
        api,
        telemetry,
        logger,
        snapshot_engine,
        drops_monitor,
        intelligence_engine,
        adaptive_engine
    ):

        self.api = api
        self.telemetry = telemetry
        self.logger = logger

        # Injected engines
        self.snapshot_engine = snapshot_engine
        self.drops_monitor = drops_monitor
        self.intelligence_engine = intelligence_engine
        self.adaptive_engine = adaptive_engine

        # Initial tracking lists
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
    # MAIN MONITORING CYCLE
    # -------------------------------------------------

    async def run_cycle(self):

        cycle_start = time.time()
        intelligence_results = []

        # -------------------------------------------------
        # STREAM SNAPSHOTS + INTELLIGENCE
        # -------------------------------------------------

        for user in self.tracked_streams:

            try:
                # Snapshot logging
                await self.snapshot_engine.process_stream(user)

                # Intelligence analysis (separate layer)
                result = await self.intelligence_engine.analyze(user)

                if result:
                    intelligence_results.append(result)

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
        # ADAPTIVE TRACKING
        # -------------------------------------------------

        try:
            self.tracked_streams = self.adaptive_engine.adjust(
                self.tracked_streams,
                intelligence_results
            )
        except Exception as e:
            self.logger.log(
                "adaptive_engine_error",
                {"error": str(e)}
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

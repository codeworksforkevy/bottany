import time
from services.prediction_engine import PredictionEngine
from services.trend_analytics_engine import TrendAnalyticsEngine
from services.adaptive_tracking_engine import AdaptiveTrackingEngine


class TwitchMonitor:

    def __init__(self, api, telemetry, logger, snapshot_engine, drops_monitor):

        self.api = api
        self.telemetry = telemetry
        self.logger = logger
        self.snapshot_engine = snapshot_engine
        self.drops_monitor = drops_monitor

        self.predictor = PredictionEngine()
        self.trend_engine = TrendAnalyticsEngine()
        self.adaptive_engine = AdaptiveTrackingEngine()

        self.tracked_streams = ["xqc", "tarik", "shroud"]
        self.tracked_games = ["Valorant", "League of Legends", "Fortnite"]

    async def run_cycle(self):

        cycle_start = time.time()
        intelligence_results = []

        for user in self.tracked_streams:
            try:
                await self.snapshot_engine.process_stream(user)
                result = await self.snapshot_engine.intelligence_engine.analyze(user)
                if result:
                    intelligence_results.append(result)
            except Exception as e:
                self.logger.log("stream_monitor_error", {"user": user, "error": str(e)})

        for game in self.tracked_games:
            try:
                await self.drops_monitor.check_game(game)
            except Exception as e:
                self.logger.log("drops_monitor_error", {"game": game, "error": str(e)})

        self.tracked_streams = self.adaptive_engine.adjust(
            self.tracked_streams,
            intelligence_results
        )

        duration = round(time.time() - cycle_start, 3)

        self.logger.log("monitor_cycle", {
            "status": "completed",
            "streams_checked": len(self.tracked_streams),
            "duration_seconds": duration
        })

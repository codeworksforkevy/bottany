from services.drops_monitor import DropsLifecycleMonitor
from core.cache_manager import CacheManager


class TwitchMonitor:

    def __init__(self, api, telemetry, logger):
        self.api = api
        self.telemetry = telemetry
        self.logger = logger
        self.cache = CacheManager("data/drops_cache.json")
        self.drops_monitor = DropsLifecycleMonitor(api, self.cache, logger)

        self.tracked_games = [
            "Valorant",
            "League of Legends",
            "Fortnite"
        ]

    async def run_cycle(self):

        for game in self.tracked_games:
            await self.drops_monitor.check_game(game)

        self.logger.log("monitor_cycle", {"status": "drops_checked"})

from services.diff_engine import generate_hash


class DropsLifecycleMonitor:

    def __init__(self, api, cache, logger, telemetry):
        self.api = api
        self.cache = cache
        self.logger = logger
        self.telemetry = telemetry

    async def check_game(self, game_name):

        key = f"drops_{game_name}"

        data = await self.api.get("streams", params={"game_name": game_name})
        streams = data.get("data", [])

        drops_active = any("drops" in s.get("title", "").lower() for s in streams)

        comparison_state = {
            "game": game_name,
            "drops_active": drops_active
        }

        previous = self.cache.get(key)

        if previous and generate_hash(previous) == generate_hash(comparison_state):
            return

        self.cache.set(key, comparison_state, ttl=300)

        await self.telemetry.log_drops_state(game_name, drops_active)

        self.logger.log("drops_state_changed", comparison_state)

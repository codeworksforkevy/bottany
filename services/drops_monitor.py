import time
from services.diff_engine import generate_hash

DROPS_TTL = 300


class DropsLifecycleMonitor:

    def __init__(self, api, cache, logger):
        self.api = api
        self.cache = cache
        self.logger = logger

    async def check_game(self, game_name: str):

        key = f"drops_{game_name}"

        # Streams çek
        data = await self.api.get(
            "streams",
            params={"game_name": game_name, "first": 20}
        )

        streams = data.get("data", [])

        drops_detected = any(
            "drops" in (stream.get("title", "").lower())
            for stream in streams
        )

        new_state = {
            "game": game_name,
            "drops_active": drops_detected,
            "timestamp": time.time()
        }

        old_state = self.cache.get(key)

        if not old_state:
            self.cache.set(key, new_state, DROPS_TTL)
            return

        if generate_hash(old_state) != generate_hash(new_state):
            self.logger.log(
                "drops_state_changed",
                {
                    "game": game_name,
                    "old": old_state,
                    "new": new_state
                }
            )

        self.cache.set(key, new_state, DROPS_TTL)

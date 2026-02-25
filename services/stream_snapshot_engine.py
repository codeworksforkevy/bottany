from services.diff_engine import generate_hash


class StreamSnapshotEngine:

    def __init__(self, api, telemetry, cache, logger):
        self.api = api
        self.telemetry = telemetry
        self.cache = cache
        self.logger = logger

    async def process_stream(self, user_login: str):

        key = f"stream_{user_login}"

        data = await self.api.get_stream_by_login(user_login)

        streams = data.get("data", [])

        if not streams:
            return  # offline → ignore

        stream = streams[0]

        snapshot = {
            "user_login": stream["user_login"],
            "viewer_count": stream["viewer_count"],
            "title": stream["title"],
            "game_name": stream["game_name"],
            "started_at": stream["started_at"]
        }

        previous = self.cache.get(key)

        if not previous:
            await self.telemetry.log_stream_snapshot(**snapshot)
            self.cache.set(key, snapshot, ttl=120)
            return

        if generate_hash(previous) != generate_hash(snapshot):

            await self.telemetry.log_stream_snapshot(**snapshot)

            self.logger.log(
                "stream_snapshot_updated",
                {
                    "user": user_login,
                    "viewer_delta": snapshot["viewer_count"] - previous["viewer_count"]
                }
            )

        self.cache.set(key, snapshot, ttl=120)

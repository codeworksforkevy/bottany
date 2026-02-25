from typing import Optional, Dict, Any
from services.diff_engine import generate_hash


class StreamSnapshotEngine:

    def __init__(
        self,
        api,
        telemetry,
        cache,
        logger,
        anomaly_detector=None,
        snapshot_ttl: int = 120
    ):
        self.api = api
        self.telemetry = telemetry
        self.cache = cache
        self.logger = logger
        self.anomaly_detector = anomaly_detector
        self.snapshot_ttl = snapshot_ttl

    # -------------------------------------------------
    # MAIN PROCESSOR
    # -------------------------------------------------

    async def process_stream(self, user_login: str):

        key = f"stream_{user_login}"

        try:
            data = await self.api.get_stream_by_login(user_login)
        except Exception as e:
            self.logger.log(
                "stream_api_error",
                {"user": user_login, "error": str(e)}
            )
            return

        streams = data.get("data", [])

        # -------------------------------------------------
        # OFFLINE CASE
        # -------------------------------------------------

        if not streams:
            # Optional: clear cache if stream went offline
            self.cache.set(key, {"offline": True}, ttl=60)
            return

        stream = streams[0]

        # Safe field extraction
        snapshot: Dict[str, Any] = {
            "user_login": stream.get("user_login"),
            "viewer_count": stream.get("viewer_count", 0),
            "title": stream.get("title", ""),
            "game_name": stream.get("game_name", ""),
            "started_at": stream.get("started_at")
        }

        previous: Optional[Dict[str, Any]] = self.cache.get(key)

        # -------------------------------------------------
        # FIRST SNAPSHOT
        # -------------------------------------------------

        if not previous or previous.get("offline"):

            await self.telemetry.log_stream_snapshot(**snapshot)

            if self.anomaly_detector:
                await self.anomaly_detector.check(
                    snapshot["user_login"],
                    snapshot["viewer_count"]
                )

            self.cache.set(key, snapshot, ttl=self.snapshot_ttl)
            return

        # -------------------------------------------------
        # CHANGE DETECTION
        # -------------------------------------------------

        if generate_hash(previous) != generate_hash(snapshot):

            await self.telemetry.log_stream_snapshot(**snapshot)

            viewer_delta = (
                snapshot["viewer_count"] - previous.get("viewer_count", 0)
            )

            self.logger.log(
                "stream_snapshot_updated",
                {
                    "user": user_login,
                    "viewer_delta": viewer_delta,
                    "new_viewers": snapshot["viewer_count"]
                }
            )

            if self.anomaly_detector:
                await self.anomaly_detector.check(
                    snapshot["user_login"],
                    snapshot["viewer_count"]
                )

        # -------------------------------------------------
        # CACHE UPDATE
        # -------------------------------------------------

        self.cache.set(key, snapshot, ttl=self.snapshot_ttl)

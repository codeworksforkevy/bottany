from services.stream_snapshot_engine import StreamSnapshotEngine
from core.cache_manager import CacheManager


class TwitchMonitor:

    def __init__(self, api, telemetry, logger):
        self.api = api
        self.telemetry = telemetry
        self.logger = logger

        self.stream_cache = CacheManager("data/stream_snapshot_cache.json")
        self.snapshot_engine = StreamSnapshotEngine(
            api,
            telemetry,
            self.stream_cache,
            logger
        )

        self.tracked_streams = [
            "xqc",
            "tarik",
            "shroud"
        ]

    async def run_cycle(self):

        for user in self.tracked_streams:
            await self.snapshot_engine.process_stream(user)

        self.logger.log("monitor_cycle", {"status": "stream_snapshots_checked"})

import os
import time
import json
import logging
from typing import Any, Dict, Optional

from services.http_client import http_client

logger = logging.getLogger("bottany.twitch.data")

class TwitchDataLayer:

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self._memory: Dict[str, Dict[str, Any]] = {}
        self._metrics = {
            "api_calls": 0,
            "cache_hits": 0,
            "disk_hits": 0,
            "failures": 0
        }

    # -----------------------------
    # Adaptive TTL
    # -----------------------------
    def _adaptive_ttl(self, key: str) -> int:
        usage = self._metrics["api_calls"]

        if usage < 50:
            return 600
        elif usage < 200:
            return 900
        else:
            return 1800

    # -----------------------------
    # Disk cache
    # -----------------------------
    def _disk_path(self, key: str):
        return os.path.join(self.data_dir, f"twitch_cache_{key}.json")

    def _load_disk(self, key: str) -> Optional[Any]:
        try:
            with open(self._disk_path(key), "r", encoding="utf-8") as f:
                self._metrics["disk_hits"] += 1
                logger.info(f"Disk cache hit: {key}")
                return json.load(f)
        except Exception:
            return None

    def _save_disk(self, key: str, data: Any):
        os.makedirs(self.data_dir, exist_ok=True)
        with open(self._disk_path(key), "w", encoding="utf-8") as f:
            json.dump(data, f)

    # -----------------------------
    # Core Fetch (wrapper-based)
    # -----------------------------
    async def fetch(
        self,
        key: str,
        url: str,
        headers: Dict[str, str]
    ) -> Optional[Any]:

        now = time.time()

        # 1️⃣ Memory cache
        entry = self._memory.get(key)
        if entry and now < entry["expires"]:
            self._metrics["cache_hits"] += 1
            return entry["data"]

        # 2️⃣ API via global wrapper
        payload = await http_client.request(
            method="GET",
            url=url,
            headers=headers
        )

        if payload:
            self._metrics["api_calls"] += 1
            ttl = self._adaptive_ttl(key)

            self._memory[key] = {
                "data": payload,
                "expires": time.time() + ttl
            }

            self._save_disk(key, payload)
            return payload

        # 3️⃣ Disk fallback
        disk = self._load_disk(key)
        if disk:
            return disk

        self._metrics["failures"] += 1
        logger.warning(f"TwitchDataLayer fetch failed: {key}")
        return None

    # -----------------------------
    # Metrics
    # -----------------------------
    def metrics(self):
        return self._metrics

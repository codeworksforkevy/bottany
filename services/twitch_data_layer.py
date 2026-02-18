import os
import time
import json
import asyncio
from typing import Any, Dict, Optional

import aiohttp

BACKOFF_BASE = 2
MAX_BACKOFF = 60

class TwitchDataLayer:

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self._memory: Dict[str, Dict[str, Any]] = {}
        self._metrics = {
            "api_calls": 0,
            "cache_hits": 0,
            "disk_hits": 0,
            "rate_limits": 0
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

    def _load_disk(self, key: str):
        try:
            with open(self._disk_path(key), "r", encoding="utf-8") as f:
                self._metrics["disk_hits"] += 1
                return json.load(f)
        except:
            return None

    def _save_disk(self, key: str, data: Any):
        os.makedirs(self.data_dir, exist_ok=True)
        with open(self._disk_path(key), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    # -----------------------------
    # Core Fetcher (Rate-limit aware)
    # -----------------------------
    async def fetch(self, key: str, url: str, headers: Dict[str, str]):

        now = time.time()

        # 1️⃣ Memory cache
        entry = self._memory.get(key)
        if entry and now < entry["expires"]:
            self._metrics["cache_hits"] += 1
            return entry["data"]

        # 2️⃣ API call
        backoff = 1

        async with aiohttp.ClientSession() as session:
            while True:
                async with session.get(url, headers=headers) as resp:

                    if resp.status == 429:
                        self._metrics["rate_limits"] += 1
                        await asyncio.sleep(backoff)
                        backoff = min(backoff * BACKOFF_BASE, MAX_BACKOFF)
                        continue

                    if resp.status != 200:
                        break

                    payload = await resp.json()
                    self._metrics["api_calls"] += 1
                    ttl = self._adaptive_ttl(key)

                    self._memory[key] = {
                        "data": payload,
                        "expires": now + ttl
                    }

                    self._save_disk(key, payload)
                    return payload

        # 3️⃣ Disk fallback
        disk = self._load_disk(key)
        if disk:
            return disk

        return None

    # -----------------------------
    # Metrics
    # -----------------------------
    def metrics(self):
        return self._metrics

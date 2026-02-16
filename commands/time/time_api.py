
import aiohttp
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

TIMEZONE_LIST_URL = "https://timeapi.io/api/TimeZone/AvailableTimeZones"
TIMEZONE_TIME_URL = "https://timeapi.io/api/Time/current/zone?timeZone="


class TimeAPI:

    def __init__(self, data_dir):
        self.cache_path = Path(data_dir) / "timezone_cache.json"
        self.timezones = []

    async def fetch_timezones(self):
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(TIMEZONE_LIST_URL) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.timezones = data
                    self._save_cache()
                    return
        raise Exception("Failed to fetch timezone list")

    def _save_cache(self):
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(self.timezones, f)

    def load_cache(self):
        if self.cache_path.exists():
            with open(self.cache_path, "r", encoding="utf-8") as f:
                self.timezones = json.load(f)

    async def get_time(self, timezone: str):
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.get(
                    TIMEZONE_TIME_URL + timezone
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
            except Exception:
                pass

        # Fallback to local zoneinfo
        try:
            tz = ZoneInfo(timezone)
            now = datetime.now(tz)
            return {
                "year": now.year,
                "month": now.month,
                "day": now.day,
                "hour": now.hour,
                "minute": now.minute,
                "seconds": now.second,
                "timeZone": timezone,
                "dayOfWeek": now.strftime("%A"),
                "dstActive": bool(now.dst())
            }
        except Exception:
            return None

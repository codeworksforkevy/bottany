import aiohttp
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

TIMEZONE_LIST_URL = "https://worldtimeapi.org/api/timezone"
TIMEZONE_TIME_URL = "https://worldtimeapi.org/api/timezone/"


class TimeAPI:

    def __init__(self, data_dir):
        self.cache_path = Path(data_dir) / "timezone_cache.json"
        self.timezones = []

    # -------------------------------------------------
    # FETCH TIMEZONE LIST
    # -------------------------------------------------

    async def fetch_timezones(self):

        timeout = aiohttp.ClientTimeout(total=4)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(TIMEZONE_LIST_URL) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.timezones = data
                    self._save_cache()
                    return

        raise RuntimeError("Failed to fetch timezone list")

    def _save_cache(self):
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(self.timezones, f)

    def load_cache(self):
        if self.cache_path.exists():
            with open(self.cache_path, "r", encoding="utf-8") as f:
                self.timezones = json.load(f)

    # -------------------------------------------------
    # GET TIME
    # -------------------------------------------------

    async def get_time(self, timezone: str):

        timeout = aiohttp.ClientTimeout(total=3)

        # 1️⃣ Try API
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(TIMEZONE_TIME_URL + timezone) as resp:
                    if resp.status == 200:
                        data = await resp.json()

                        dt = data.get("datetime")
                        if not dt:
                            raise ValueError("No datetime in API response")

                        parsed = datetime.fromisoformat(dt)

                        return {
                            "hour": parsed.hour,
                            "minute": parsed.minute,
                            "seconds": parsed.second,
                            "timeZone": timezone,
                            "dayOfWeek": parsed.strftime("%A"),
                            "dstActive": False  # API DST not reliable
                        }

        except Exception:
            pass

        # 2️⃣ Local fallback
        try:
            tz = ZoneInfo(timezone)
            now = datetime.now(tz)

            return {
                "hour": now.hour,
                "minute": now.minute,
                "seconds": now.second,
                "timeZone": timezone,
                "dayOfWeek": now.strftime("%A"),
                "dstActive": bool(now.dst())
            }

        except Exception:
            return None

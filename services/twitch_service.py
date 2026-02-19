import os
import time
import logging
from typing import List, Dict, Any

logger = logging.getLogger("bottany.twitch")

HELIX_BADGES = "https://api.twitch.tv/helix/chat/badges/global"

CACHE_TTL = 300

class TwitchService:

    def __init__(self):
        self._badge_cache: List[Dict[str, Any]] = []
        self._badge_expiry = 0

    async def fetch_badges(self, session) -> List[Dict[str, str]]:
        now = time.time()

        if self._badge_cache and now < self._badge_expiry:
            return self._badge_cache

        cid = os.getenv("TWITCH_CLIENT_ID")
        tok = os.getenv("TWITCH_APP_TOKEN")

        if not cid or not tok:
            logger.warning("Twitch credentials missing.")
            return []

        headers = {
            "Client-ID": cid,
            "Authorization": f"Bearer {tok}"
        }

        async with session.get(HELIX_BADGES, headers=headers) as r:

            # --- RATE BUDGET LOGGING ---
            remaining = r.headers.get("Ratelimit-Remaining")
            limit = r.headers.get("Ratelimit-Limit")
            reset = r.headers.get("Ratelimit-Reset")

            logger.info(
                f"Twitch rate budget: remaining={remaining}, limit={limit}, reset={reset}"
            )

            if r.status != 200:
                logger.warning(f"Twitch returned status {r.status}")
                return []

            data = await r.json()

        out = []
        for s in data.get("data", []):
            for v in s.get("versions", []):
                out.append({
                    "title": v.get("title") or s.get("set_id"),
                    "img": v.get("image_url_2x")
                })

        self._badge_cache = out
        self._badge_expiry = now + CACHE_TTL

        return out


twitch_service = TwitchService()

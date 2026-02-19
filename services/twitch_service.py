import os
import time
import logging
from typing import List, Dict, Any

from services.http_client import http_client
from services.twitch_auth import twitch_auth

logger = logging.getLogger("bottany.twitch")

HELIX_BADGES = "https://api.twitch.tv/helix/chat/badges/global"

CACHE_TTL = 300  # 5 minutes


class TwitchService:

    def __init__(self):
        self._badge_cache: List[Dict[str, Any]] = []
        self._badge_expiry: float = 0

    async def fetch_badges(self) -> List[Dict[str, str]]:
        now = time.time()

        # ---- CACHE CHECK ----
        if self._badge_cache and now < self._badge_expiry:
            return self._badge_cache

        # ---- GET VALID TOKEN ----
        token = await twitch_auth.get_token()
        client_id = os.getenv("TWITCH_CLIENT_ID")

        if not token or not client_id:
            logger.warning("Twitch credentials missing.")
            return []

        headers = {
            "Client-ID": client_id,
            "Authorization": f"Bearer {token}"
        }

        # ---- GLOBAL REQUEST WRAPPER ----
        data = await http_client.request(
            method="GET",
            url=HELIX_BADGES,
            headers=headers
        )

        if not data:
            logger.warning("Empty response from Twitch.")
            return []

        out: List[Dict[str, str]] = []

        for s in data.get("data", []):
            for v in s.get("versions", []):
                out.append({
                    "title": v.get("title") or s.get("set_id"),
                    "img": v.get("image_url_2x")
                })

        # ---- CACHE STORE ----
        self._badge_cache = out
        self._badge_expiry = now + CACHE_TTL

        logger.info(f"Cached {len(out)} Twitch badges.")

        return out


twitch_service = TwitchService()

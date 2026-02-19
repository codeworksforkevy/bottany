import os
import time
import logging
from services.http_client import http_client

logger = logging.getLogger("bottany.twitch.auth")

TOKEN_URL = "https://id.twitch.tv/oauth2/token"

class TwitchAuth:

    def __init__(self):
        self._token = None
        self._expires_at = 0

    async def get_token(self) -> str:

        now = time.time()

        if self._token and now < self._expires_at:
            return self._token

        logger.info("Refreshing Twitch App token...")

        cid = os.getenv("TWITCH_CLIENT_ID")
        secret = os.getenv("TWITCH_CLIENT_SECRET")

        params = (
            f"?client_id={cid}"
            f"&client_secret={secret}"
            f"&grant_type=client_credentials"
        )

        data = await http_client.request(
            "POST",
            TOKEN_URL + params
        )

        self._token = data.get("access_token")
        expires_in = data.get("expires_in", 3600)

        self._expires_at = now + expires_in - 60  # 1 min safety

        logger.info("Twitch token refreshed.")

        return self._token


twitch_auth = TwitchAuth()

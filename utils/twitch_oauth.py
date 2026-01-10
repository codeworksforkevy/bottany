from __future__ import annotations
import time
import aiohttp

class TwitchAppTokenCache:
    """Lightweight app-access-token cache (client credentials grant)."""

    def __init__(self) -> None:
        self._token: str | None = None
        self._expires_at: int = 0

    async def get(self, session: aiohttp.ClientSession, client_id: str, client_secret: str) -> str:
        now = int(time.time())
        if self._token and now < (self._expires_at - 60):
            return self._token

        url = "https://id.twitch.tv/oauth2/token"
        params = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
        }

        async with session.post(url, params=params, timeout=20) as resp:
            data = await resp.json()
            if resp.status != 200:
                raise RuntimeError(f"Twitch OAuth token error: {resp.status} {data}")

        token = data.get("access_token")
        expires_in = int(data.get("expires_in", 3600))
        if not token:
            raise RuntimeError(f"Twitch OAuth token missing access_token: {data}")

        self._token = str(token)
        self._expires_at = now + expires_in
        return self._token

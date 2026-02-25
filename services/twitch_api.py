import os
import aiohttp
import asyncio
import time
from typing import Optional, Dict, Any


TOKEN_URL = "https://id.twitch.tv/oauth2/token"
BASE_URL = "https://api.twitch.tv/helix"

DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=15)


class TwitchAPIError(Exception):
    pass


class TwitchRateLimitError(TwitchAPIError):
    pass


class TwitchAPI:

    def __init__(self):
        self.client_id = os.getenv("TWITCH_CLIENT_ID")
        self.client_secret = os.getenv("TWITCH_CLIENT_SECRET")

        if not self.client_id or not self.client_secret:
            raise RuntimeError("TWITCH_CLIENT_ID or TWITCH_CLIENT_SECRET not set.")

        self._token: Optional[str] = None
        self._token_expiry: float = 0

        self._session: Optional[aiohttp.ClientSession] = None
        self._token_lock = asyncio.Lock()

    # -------------------------------------------------
    # SESSION MANAGEMENT
    # -------------------------------------------------

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    # -------------------------------------------------
    # TOKEN MANAGEMENT
    # -------------------------------------------------

    async def _get_token(self) -> str:
        async with self._token_lock:

            # Token still valid
            if self._token and self._token_expiry > time.time():
                return self._token

            session = await self._get_session()

            async with session.post(
                TOKEN_URL,
                params={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "client_credentials",
                },
            ) as resp:

                if resp.status != 200:
                    text = await resp.text()
                    raise TwitchAPIError(f"Token request failed: {resp.status} {text}")

                data = await resp.json()

            self._token = data["access_token"]
            # refresh 60 sec before expiry
            self._token_expiry = time.time() + data["expires_in"] - 60

            return self._token

    async def _headers(self) -> Dict[str, str]:
        token = await self._get_token()
        return {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {token}",
        }

    # -------------------------------------------------
    # CORE REQUEST METHOD
    # -------------------------------------------------

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        retry_on_401: bool = True
    ) -> Dict[str, Any]:

        session = await self._get_session()
        headers = await self._headers()

        url = f"{BASE_URL}/{endpoint}"

        async with session.request(
            method,
            url,
            headers=headers,
            params=params
        ) as resp:

            # Rate limit
            if resp.status == 429:
                retry_after = int(resp.headers.get("Retry-After", "1"))
                await asyncio.sleep(retry_after)
                raise TwitchRateLimitError("Twitch rate limit hit.")

            # Unauthorized → refresh token once
            if resp.status == 401 and retry_on_401:
                self._token = None
                return await self._request(method, endpoint, params, retry_on_401=False)

            if resp.status >= 400:
                text = await resp.text()
                raise TwitchAPIError(
                    f"Request failed [{resp.status}] {endpoint} → {text}"
                )

            return await resp.json()

    # -------------------------------------------------
    # PUBLIC HELIX WRAPPER
    # -------------------------------------------------

    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None):
        return await self._request("GET", endpoint, params)

    # -------------------------------------------------
    # COMMON TWITCH ENDPOINTS
    # -------------------------------------------------

    async def get_global_badges(self):
        return await self.get("chat/badges/global")

    async def get_channel_badges(self, broadcaster_id: str):
        return await self.get(
            "chat/badges",
            params={"broadcaster_id": broadcaster_id}
        )

    async def get_stream_by_login(self, user_login: str):
        return await self.get(
            "streams",
            params={"user_login": user_login}
        )

    async def get_user_by_login(self, user_login: str):
        return await self.get(
            "users",
            params={"login": user_login}
        )

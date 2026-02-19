from __future__ import annotations

import aiohttp
import asyncio
import logging
import random
from typing import Optional, Dict, Any, Union

logger = logging.getLogger("bottany.http")


class HTTPClientManager:
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None

    # -------------------------------------------------
    # LIFECYCLE
    # -------------------------------------------------

    async def start(self):
        if self._session:
            return

        timeout = aiohttp.ClientTimeout(
            total=30,
            connect=10,
            sock_read=20
        )

        self._session = aiohttp.ClientSession(timeout=timeout)
        logger.info("🌐 Global HTTP session started.")

    async def close(self):
        if not self._session:
            return

        await self._session.close()
        self._session = None
        logger.info("🛑 Global HTTP session closed.")

    @property
    def session(self) -> aiohttp.ClientSession:
        if not self._session:
            raise RuntimeError("HTTP session not initialized. Call start() first.")
        return self._session

    # -------------------------------------------------
    # CORE REQUEST
    # -------------------------------------------------

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        retries: int = 4,
        return_raw: bool = False
    ) -> Union[Dict[str, Any], aiohttp.ClientResponse, None]:

        for attempt in range(retries):
            try:
                async with self.session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=json,
                    data=data,
                    params=params
                ) as response:

                    # -------- Twitch Rate Headers --------
                    remaining = response.headers.get("Ratelimit-Remaining")
                    limit = response.headers.get("Ratelimit-Limit")
                    reset = response.headers.get("Ratelimit-Reset")

                    logger.info(
                        f"[HTTP] {method} {url} "
                        f"status={response.status} "
                        f"remaining={remaining} "
                        f"limit={limit} "
                        f"reset={reset}"
                    )

                    # -------- Rate Limit --------
                    if response.status == 429:
                        retry_after = int(response.headers.get("Retry-After", 2))
                        sleep_time = retry_after + random.uniform(0, 0.5)
                        logger.warning(f"429 Rate limit. Sleeping {sleep_time:.2f}s")
                        await asyncio.sleep(sleep_time)
                        continue

                    # -------- 5xx Retry --------
                    if 500 <= response.status < 600:
                        backoff = (2 ** attempt) + random.uniform(0, 1)
                        logger.warning(
                            f"Server error {response.status}. Retry in {backoff:.2f}s"
                        )
                        await asyncio.sleep(backoff)
                        continue

                    # -------- Client Error --------
                    if response.status >= 400:
                        text = await response.text()
                        logger.warning(
                            f"HTTP {response.status} on {url}: {text}"
                        )
                        return None

                    if return_raw:
                        return response

                    try:
                        return await response.json()
                    except Exception:
                        return None

            except aiohttp.ClientError as e:
                backoff = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"HTTP client error: {e}. Retry in {backoff:.2f}s")
                await asyncio.sleep(backoff)

        logger.error(f"❌ Request failed after retries: {url}")
        return None


http_client = HTTPClientManager()

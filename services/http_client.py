import aiohttp
import asyncio
import logging
import random
from typing import Optional, Dict, Any

logger = logging.getLogger("bottany.http")

class HTTPClientManager:
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None

    async def start(self):
        if not self._session:
            timeout = aiohttp.ClientTimeout(total=20)
            self._session = aiohttp.ClientSession(timeout=timeout)
            logger.info("Global HTTP session started.")

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None
            logger.info("Global HTTP session closed.")

    @property
    def session(self) -> aiohttp.ClientSession:
        if not self._session:
            raise RuntimeError("HTTP session not initialized")
        return self._session

    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        retries: int = 3
    ) -> Dict[str, Any]:

        for attempt in range(retries):

            try:
                async with self.session.request(
                    method,
                    url,
                    headers=headers
                ) as r:

                    # ---- RATE LIMIT LOG ----
                    logger.info(
                        f"[{url}] status={r.status} "
                        f"remaining={r.headers.get('Ratelimit-Remaining')}"
                    )

                    if r.status == 429:
                        retry_after = int(r.headers.get("Retry-After", 2))
                        await asyncio.sleep(retry_after)
                        continue

                    if 500 <= r.status < 600:
                        await asyncio.sleep(
                            (2 ** attempt) + random.uniform(0, 1)
                        )
                        continue

                    return await r.json()

            except aiohttp.ClientError as e:
                logger.warning(f"HTTP error: {e}")
                await asyncio.sleep(
                    (2 ** attempt) + random.uniform(0, 1)
                )

        logger.error(f"Request failed after retries: {url}")
        return {}
        

http_client = HTTPClientManager()

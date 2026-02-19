import aiohttp
import logging
from typing import Optional

logger = logging.getLogger("bottany.http")

class HTTPClientManager:
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None

    async def start(self):
        if not self._session:
            timeout = aiohttp.ClientTimeout(total=15)
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


http_client = HTTPClientManager()

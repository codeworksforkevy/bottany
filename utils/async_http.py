
import aiohttp

HEADERS = {
    "User-Agent": "BottanyBot/2.0 (+https://railway.app)"
}

async def fetch_text(url: str, timeout: int = 20):
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(url, timeout=timeout) as resp:
            resp.raise_for_status()
            return await resp.text()

async def url_exists(url: str, timeout: int = 10):
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.head(url, allow_redirects=True, timeout=timeout) as resp:
                return 200 <= resp.status < 400
    except Exception:
        return False

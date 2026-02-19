import logging
from services.http_client import http_client

logger = logging.getLogger("bottany.twitch")

HELIX_BASE = "https://api.twitch.tv/helix"

async def helix_get(auth, path: str):

    token = await auth.get_token()
    headers = {
        "Client-ID": auth.client_id,
        "Authorization": f"Bearer {token}",
    }

    async with http_client.session.get(HELIX_BASE + path, headers=headers) as r:

        remaining = r.headers.get("Ratelimit-Remaining")
        limit = r.headers.get("Ratelimit-Limit")
        reset = r.headers.get("Ratelimit-Reset")

        logger.info(
            "Helix budget: remaining=%s limit=%s reset=%s",
            remaining, limit, reset
        )

        if r.status != 200:
            logger.warning("Helix status %s", r.status)
            return {}

        return await r.json()

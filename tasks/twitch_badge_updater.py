import asyncio
import logging
from services.http_client import http_client
from services.twitch_service import twitch_service

logger = logging.getLogger("bottany.tasks")

async def badge_updater_loop():
    await http_client.start()

    while True:
        try:
            await twitch_service.fetch_badges(http_client.session)
            logger.info("Twitch badges refreshed.")
        except Exception as e:
            logger.error(f"Badge updater error: {e}")

        await asyncio.sleep(300)  # 5 min

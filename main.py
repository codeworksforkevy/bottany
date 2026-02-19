from __future__ import annotations

import os
import asyncio
import logging
import signal
import json
import hmac
import hashlib
import time
from pathlib import Path
from aiohttp import web

import discord
from discord.ext import commands

from services.logging_config import setup_logging
from services.telemetry import capture_exception
from services.http_client import http_client
from services.twitch_live_notifier import notify_live

# =================================================
# ENV
# =================================================

ENV = os.getenv("ENV", "dev").lower()
OWNER_ID = int(os.getenv("BOT_OWNER_ID", "0"))
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
EVENTSUB_SECRET = os.getenv("TWITCH_EVENTSUB_SECRET", "")
CHANNEL_ID = 1446562626695074006

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN not set")

# =================================================
# LOGGING
# =================================================

setup_logging()
logger = logging.getLogger("bottany")

# =================================================
# BOT
# =================================================

intents = discord.Intents.default()
intents.message_content = True

class BottanyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await http_client.start()
        logger.info("HTTP client started.")

    async def on_ready(self):
        logger.info("Bot ready as %s", self.user)

bot = BottanyBot()

# =================================================
# EVENTSUB SECURITY
# =================================================

REPLAY_CACHE = set()
REPLAY_TTL = 600

def verify_signature(msg_id, msg_ts, body, signature):
    if not EVENTSUB_SECRET:
        return False

    expected = hmac.new(
        EVENTSUB_SECRET.encode(),
        (msg_id + msg_ts).encode() + body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(f"sha256={expected}", signature)

def is_fresh_timestamp(msg_ts):
    try:
        ts = int(time.mktime(time.strptime(msg_ts, "%Y-%m-%dT%H:%M:%SZ")))
        return abs(time.time() - ts) < 600
    except Exception:
        return False

# =================================================
# WEBHOOK HANDLER
# =================================================

async def eventsub_handler(request: web.Request):

    body = await request.read()

    msg_id = request.headers.get("Twitch-Eventsub-Message-Id", "")
    msg_ts = request.headers.get("Twitch-Eventsub-Message-Timestamp", "")
    signature = request.headers.get("Twitch-Eventsub-Message-Signature", "")
    msg_type = request.headers.get("Twitch-Eventsub-Message-Type", "")

    if msg_id in REPLAY_CACHE:
        return web.Response(text="duplicate")

    if not verify_signature(msg_id, msg_ts, body, signature):
        return web.Response(status=403)

    if not is_fresh_timestamp(msg_ts):
        return web.Response(status=403)

    REPLAY_CACHE.add(msg_id)

    payload = json.loads(body.decode())

    # Challenge verification
    if msg_type == "webhook_callback_verification":
        return web.Response(text=payload.get("challenge", ""))

    # Live notification
    if msg_type == "notification":
        event = payload.get("event", {})
        login = event.get("broadcaster_user_login")
        title = event.get("title")
        game = event.get("category_name")

        await notify_live(
            bot,
            CHANNEL_ID,
            login,
            title,
            game
        )

    return web.Response(text="ok")

# =================================================
# HEALTH + WEB SERVER
# =================================================

async def health(request):
    return web.json_response({"status": "ok", "env": ENV})

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_post("/twitch/eventsub", eventsub_handler)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", "8080"))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    logger.info("Web server running on port %s", port)

# =================================================
# SHUTDOWN
# =================================================

async def shutdown():
    logger.info("Shutdown initiated")
    await http_client.close()
    await bot.close()

def install_signal_handlers():
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig,
            lambda: asyncio.create_task(shutdown())
        )

# =================================================
# MAIN
# =================================================

async def main():
    install_signal_handlers()
    await start_web_server()
    await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())

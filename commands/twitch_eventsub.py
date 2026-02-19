from __future__ import annotations

import os
import json
import hmac
import hashlib
import logging
import time
from typing import Callable, Optional, List, Dict

from aiohttp import web
import discord

logger = logging.getLogger("bottany.twitch_eventsub")

# --------------------------------------------------------
# CONFIG
# --------------------------------------------------------

SIG_PREFIX = "sha256="
MAX_AGE_SECONDS = 600  # 10 minutes
REPLAY_STORE: Dict[str, float] = {}

# --------------------------------------------------------
# SECURITY HELPERS
# --------------------------------------------------------

def _hmac_sha256(secret: bytes, msg: bytes) -> str:
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()


def _verify_signature(secret: str, msg_id: str, msg_ts: str, body: bytes, sig_header: str) -> bool:
    if not secret or not sig_header or not sig_header.startswith(SIG_PREFIX):
        return False

    expected = _hmac_sha256(
        secret.encode("utf-8"),
        (msg_id + msg_ts).encode("utf-8") + body
    )

    received = sig_header[len(SIG_PREFIX):]
    return hmac.compare_digest(expected, received)


def _validate_timestamp(msg_ts: str) -> bool:
    try:
        # Twitch timestamp format: 2024-01-01T12:34:56.789Z
        ts = time.strptime(msg_ts.split(".")[0], "%Y-%m-%dT%H:%M:%S")
        ts_epoch = time.mktime(ts)
    except Exception:
        return False

    return abs(time.time() - ts_epoch) <= MAX_AGE_SECONDS


def _check_replay(msg_id: str) -> bool:
    now = time.time()

    if msg_id in REPLAY_STORE:
        return False

    REPLAY_STORE[msg_id] = now

    # cleanup old entries
    for k, v in list(REPLAY_STORE.items()):
        if now - v > MAX_AGE_SECONDS:
            REPLAY_STORE.pop(k, None)

    return True


async def _safe_send(channel: discord.abc.Messageable, embed: discord.Embed):
    try:
        await channel.send(embed=embed)
    except Exception as e:
        logger.warning("Failed to send Twitch EventSub message: %s", e)


# --------------------------------------------------------
# MAIN REGISTRATION
# --------------------------------------------------------

async def register_twitch_eventsub(
    bot: discord.Client,
    data_dir: str,
    db_get_channel: Callable[[int, str], Optional[int]],
    db_list_twitch_watch: Callable[[int], List[tuple[str, int]]],
    db_log_clip: Callable[[int, str, str], None],
) -> None:

    secret = (os.getenv("TWITCH_EVENTSUB_SECRET") or "").strip()
    port = int(os.getenv("TWITCH_EVENTSUB_PORT", "8090"))
    path = os.getenv("TWITCH_EVENTSUB_PATH", "/twitch/eventsub")

    if not secret:
        logger.warning("TWITCH_EVENTSUB_SECRET missing.")

    if not path.startswith("/"):
        path = "/" + path

    async def handler(request: web.Request) -> web.Response:

        body = await request.read()

        msg_id = request.headers.get("Twitch-Eventsub-Message-Id", "")
        msg_ts = request.headers.get("Twitch-Eventsub-Message-Timestamp", "")
        sig = request.headers.get("Twitch-Eventsub-Message-Signature", "")
        msg_type = request.headers.get("Twitch-Eventsub-Message-Type", "")

        # Signature
        if not _verify_signature(secret, msg_id, msg_ts, body, sig):
            return web.Response(status=403, text="invalid signature")

        # Timestamp validation
        if not _validate_timestamp(msg_ts):
            return web.Response(status=403, text="timestamp expired")

        # Replay protection
        if not _check_replay(msg_id):
            return web.Response(status=409, text="duplicate message")

        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            return web.Response(status=400, text="invalid json")

        # ----------------------------------------------------
        # Handshake
        # ----------------------------------------------------
        if msg_type == "webhook_callback_verification":
            return web.Response(text=payload.get("challenge", ""))

        if msg_type == "revocation":
            sub = payload.get("subscription", {}) or {}
            logger.warning("EventSub revoked: %s", sub.get("status"))
            return web.Response(text="ok")

        # ----------------------------------------------------
        # Notification
        # ----------------------------------------------------
        if msg_type == "notification":

            sub = payload.get("subscription", {}) or {}
            event = payload.get("event", {}) or {}
            sub_type = sub.get("type", "")

            # Build quick lookup for watched logins per guild
            guild_watch_map: Dict[str, List[tuple[int, int]]] = {}

            for guild in bot.guilds:
                for login, chan_id in db_list_twitch_watch(guild.id):
                    login = (login or "").lower()
                    guild_watch_map.setdefault(login, []).append((guild.id, chan_id))

            # ------------------------------------------------
            # Stream online/offline
            # ------------------------------------------------
            if sub_type in ("stream.online", "stream.offline"):

                login = (event.get("broadcaster_user_login") or "").lower()

                if login not in guild_watch_map:
                    return web.Response(text="ok")

                for guild_id, chan_id in guild_watch_map[login]:
                    ch = bot.get_channel(chan_id)
                    if not ch:
                        continue

                    if sub_type == "stream.online":

                        title = (event.get("title") or "")[:1000]
                        category = (event.get("category_name") or "")[:100]

                        e = discord.Embed(
                            title=f"🔴 {login} is now live!"
                        )

                        if title:
                            e.add_field(name="Title", value=title, inline=False)

                        if category:
                            e.add_field(name="Category", value=category, inline=True)

                        e.add_field(
                            name="Watch",
                            value=f"https://twitch.tv/{login}",
                            inline=False
                        )

                        await _safe_send(ch, e)

                    else:
                        e = discord.Embed(
                            title=f"⚫ Stream ended: {login}"
                        )
                        e.add_field(
                            name="Channel",
                            value=f"https://twitch.tv/{login}",
                            inline=False
                        )
                        await _safe_send(ch, e)

                return web.Response(text="ok")

            # ------------------------------------------------
            # Clip created
            # ------------------------------------------------
            if sub_type == "channel.clip.create":

                login = (event.get("broadcaster_user_login") or "").lower()
                clip_url = event.get("url") or ""
                creator = event.get("creator_user_name") or ""
                title = (event.get("title") or "Clip")[:1000]

                if login not in guild_watch_map:
                    return web.Response(text="ok")

                for guild_id, chan_id in guild_watch_map[login]:
                    db_log_clip(guild_id, login, clip_url)

                    ch = bot.get_channel(chan_id)
                    if not ch:
                        continue

                    e = discord.Embed(
                        title=f"🎬 New clip from {login}",
                        description=f"**{title}**"
                    )

                    if creator:
                        e.add_field(name="Created by", value=creator[:200], inline=True)

                    if clip_url:
                        e.add_field(name="Watch Clip", value=clip_url, inline=False)

                    await _safe_send(ch, e)

                return web.Response(text="ok")

            return web.Response(text="ignored")

        return web.Response(text="ok")

    # --------------------------------------------------------
    # Server
    # --------------------------------------------------------

    app = web.Application()
    app.router.add_post(path, handler)
    app.router.add_get(path, lambda r: web.json_response({"ok": True, "path": path}))

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    logger.info("EventSub webhook running on port %s path %s", port, path)

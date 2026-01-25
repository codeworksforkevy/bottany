from __future__ import annotations
import os, json, hmac, hashlib, logging
from typing import Any, Callable, Awaitable, Dict, List, Optional
import aiohttp
from aiohttp import web
import discord

logger = logging.getLogger("bottany.twitch_eventsub")

# Twitch EventSub headers:
# Twitch-Eventsub-Message-Id, Twitch-Eventsub-Message-Timestamp, Twitch-Eventsub-Message-Signature
# Signature format: "sha256=<hex>"
SIG_PREFIX = "sha256="

def _hmac_sha256(secret: bytes, msg: bytes) -> str:
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()

def _verify_signature(secret: str, msg_id: str, msg_ts: str, body: bytes, sig_header: str) -> bool:
    if not secret or not sig_header:
        return False
    if not sig_header.startswith(SIG_PREFIX):
        return False
    expected = _hmac_sha256(secret.encode("utf-8"), (msg_id + msg_ts).encode("utf-8") + body)
    got = sig_header[len(SIG_PREFIX):]
    return hmac.compare_digest(expected, got)

async def register_twitch_eventsub(
    bot: discord.Client,
    data_dir: str,
    db_get_channel: Callable[[int, str], Optional[int]],
    db_list_twitch_watch: Callable[[int], List[tuple[str,int]]],
    db_log_clip: Callable[[int, str, str], None],
) -> None:
    """
    Starts an aiohttp webhook server (separate from the health server) to receive EventSub.
    Railway: expose a port (TWITCH_EVENTSUB_PORT) and point your EventSub callback to:
      https://<your-app>.up.railway.app/twitch/eventsub
    """

    secret = (os.getenv("TWITCH_EVENTSUB_SECRET","") or "").strip()
    port = int(os.getenv("TWITCH_EVENTSUB_PORT","8090"))
    path = os.getenv("TWITCH_EVENTSUB_PATH", "/twitch/eventsub")

    if not secret:
        logger.warning("TWITCH_EVENTSUB_SECRET missing; EventSub endpoint will reject all requests.")
    if not path.startswith("/"):
        path = "/" + path

    async def handler(request: web.Request) -> web.Response:
        body = await request.read()

        msg_id = request.headers.get("Twitch-Eventsub-Message-Id","")
        msg_ts = request.headers.get("Twitch-Eventsub-Message-Timestamp","")
        sig = request.headers.get("Twitch-Eventsub-Message-Signature","")
        msg_type = request.headers.get("Twitch-Eventsub-Message-Type","")

        if not _verify_signature(secret, msg_id, msg_ts, body, sig):
            return web.Response(status=403, text="invalid signature")

        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            return web.Response(status=400, text="invalid json")

        # verification handshake
        if msg_type == "webhook_callback_verification":
            challenge = payload.get("challenge","")
            return web.Response(status=200, text=str(challenge))

        if msg_type == "revocation":
            # subscription revoked; we log but do not error
            sub = payload.get("subscription",{}) or {}
            reason = sub.get("status","revoked")
            logger.warning("EventSub revoked: %s", reason)
            return web.Response(status=200, text="ok")

        # notifications
        if msg_type == "notification":
            sub = payload.get("subscription",{}) or {}
            ev = payload.get("event",{}) or {}
            sub_type = sub.get("type","")

            # Channel online/offline
            if sub_type in ("stream.online", "stream.offline"):
                login = (ev.get("broadcaster_user_login") or "").lower()
                title = ev.get("title","") if sub_type == "stream.online" else ""
                category = ev.get("category_name","") if sub_type == "stream.online" else ""

                for guild in bot.guilds:
                    watches = dict(db_list_twitch_watch(guild.id))
                    if login not in watches:
                        continue
                    chan_id = watches[login]
                    ch = bot.get_channel(chan_id)
                    if not ch:
                        continue

                    if sub_type == "stream.online":
                        e = discord.Embed(title=f"Going live: {login}")
                        e.add_field(name="Title", value=title or "(no title)", inline=False)
                        if category:
                            e.add_field(name="Category", value=category, inline=True)
                        e.add_field(name="Watch", value=f"https://twitch.tv/{login}", inline=False)
                        # Twitch thumbnails are provided in other endpoints; we keep it link-first to avoid ToS issues
                        await ch.send(embed=e)
                    else:
                        e = discord.Embed(title=f"Stream ended: {login}")
                        e.add_field(name="Channel", value=f"https://twitch.tv/{login}", inline=False)
                        await ch.send(embed=e)

                return web.Response(status=200, text="ok")

            # Clip created
            if sub_type == "channel.clip.create":
                login = (ev.get("broadcaster_user_login") or "").lower()
                clip_url = ev.get("url") or ""
                creator = ev.get("creator_user_name") or ev.get("creator_user_login") or ""
                title = ev.get("title","") or "Clip"
                # log in DB per guild that watches this login
                for guild in bot.guilds:
                    watches = dict(db_list_twitch_watch(guild.id))
                    if login not in watches:
                        continue
                    db_log_clip(guild.id, login, clip_url or "")
                    chan_id = watches[login]
                    ch = bot.get_channel(chan_id)
                    if not ch:
                        continue
                    e = discord.Embed(title=f"New clip: {login}")
                    e.description = f"**{title}**"
                    if creator:
                        e.add_field(name="Created by", value=str(creator), inline=True)
                    if clip_url:
                        e.add_field(name="Clip", value=clip_url, inline=False)
                    await ch.send(embed=e)
                return web.Response(status=200, text="ok")

            return web.Response(status=200, text="ignored")

        return web.Response(status=200, text="ok")

    app = web.Application()
    app.router.add_post(path, handler)
    app.router.add_get(path, lambda r: web.json_response({"ok": True, "path": path}))

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("EventSub webhook server listening on port %s path %s", port, path)

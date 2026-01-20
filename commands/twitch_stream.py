import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

import aiohttp
import discord
from discord import app_commands

# -------------------------
# Files
# -------------------------
TWITCH_CFG_FILE = "twitch_stream_config.json"
TWITCH_SCHEDULE_FILE = "twitch_schedule.json"
TWITCH_MILESTONES_FILE = "twitch_milestones.json"

# -------------------------
# Helpers
# -------------------------
def _load_json(path: str, default: Any) -> Any:
    try:
        if not os.path.exists(path):
            return default
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def _save_json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def _now_utc() -> datetime:
    return datetime.utcnow().replace(microsecond=0)

def _cfg_path(data_dir: str) -> str:
    return os.path.join(data_dir, TWITCH_CFG_FILE)

def _schedule_path(data_dir: str) -> str:
    return os.path.join(data_dir, TWITCH_SCHEDULE_FILE)

def _milestones_path(data_dir: str) -> str:
    return os.path.join(data_dir, TWITCH_MILESTONES_FILE)

async def _get_app_token(session: aiohttp.ClientSession) -> Optional[str]:
    client_id = os.getenv("TWITCH_CLIENT_ID", "").strip()
    client_secret = os.getenv("TWITCH_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        return None
    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    }
    async with session.post(url, params=params, timeout=20) as resp:
        if resp.status != 200:
            return None
        data = await resp.json()
        return data.get("access_token")

async def _twitch_get(session: aiohttp.ClientSession, url: str, token: str, params: Dict[str, str]) -> Optional[Dict[str, Any]]:
    client_id = os.getenv("TWITCH_CLIENT_ID", "").strip()
    if not client_id or not token:
        return None
    headers = {"Client-ID": client_id, "Authorization": f"Bearer {token}"}
    async with session.get(url, headers=headers, params=params, timeout=20) as resp:
        if resp.status != 200:
            return None
        return await resp.json()

async def _get_user_id(session: aiohttp.ClientSession, token: str, login: str) -> Optional[str]:
    data = await _twitch_get(session, "https://api.twitch.tv/helix/users", token, {"login": login})
    if not data:
        return None
    items = data.get("data", [])
    if not items:
        return None
    return str(items[0].get("id"))

async def _get_stream(session: aiohttp.ClientSession, token: str, broadcaster_id: str) -> Optional[Dict[str, Any]]:
    data = await _twitch_get(session, "https://api.twitch.tv/helix/streams", token, {"user_id": broadcaster_id})
    if not data:
        return None
    items = data.get("data", [])
    return items[0] if items else None

async def _get_followers_count(session: aiohttp.ClientSession, token: str, broadcaster_id: str, moderator_id: str) -> Optional[int]:
    # Twitch API requires user access token w/ moderator scope for this endpoint.
    data = await _twitch_get(session, "https://api.twitch.tv/helix/channels/followers", token, {"broadcaster_id": broadcaster_id, "moderator_id": moderator_id})
    if not data:
        return None
    total = data.get("total")
    try:
        return int(total)
    except Exception:
        return None

def _format_delta(td: timedelta) -> str:
    total = int(td.total_seconds())
    if total < 0:
        total = 0
    days, rem = divmod(total, 86400)
    hrs, rem = divmod(rem, 3600)
    mins, _ = divmod(rem, 60)
    if days:
        return f"{days}d {hrs}h {mins}m"
    if hrs:
        return f"{hrs}h {mins}m"
    return f"{mins}m"

def _next_scheduled(sched: Dict[str, Any]) -> Optional[datetime]:
    # schedule format: {"timezone":"Europe/Istanbul", "slots":[{"dow":0-6,"hour":int,"minute":int,"label":""}]}
    tz_name = sched.get("timezone") or "UTC"
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = None

    now = datetime.now(tz) if tz else datetime.utcnow()
    slots = sched.get("slots", []) or []
    if not slots:
        return None

    candidates: List[datetime] = []
    for s in slots:
        try:
            dow = int(s.get("dow"))
            hour = int(s.get("hour"))
            minute = int(s.get("minute"))
        except Exception:
            continue
        # compute next occurrence
        # python weekday: Monday=0..Sunday=6
        days_ahead = (dow - now.weekday()) % 7
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days_ahead)
        if candidate <= now:
            candidate += timedelta(days=7)
        candidates.append(candidate)
    return min(candidates) if candidates else None

class TwitchGroup(app_commands.Group):
    def __init__(self, bot: discord.Client, data_dir: str):
        super().__init__(name="twitch", description="Twitch stream tools (live notifications, schedule, milestones)")
        self._bot = bot
        self._data_dir = data_dir
        self._session: Optional[aiohttp.ClientSession] = None
        self._app_token: Optional[str] = None
        self._app_token_expiry: Optional[datetime] = None
        self._last_live_state: Dict[str, Any] = {"is_live": False, "started_at": "", "title": "", "game": ""}

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _ensure_app_token(self) -> Optional[str]:
        if self._app_token and self._app_token_expiry and _now_utc() < self._app_token_expiry:
            return self._app_token
        session = await self._ensure_session()
        tok = await _get_app_token(session)
        if not tok:
            return None
        # conservative expiry (app tokens typically last ~60 days, but treat as 1 day)
        self._app_token = tok
        self._app_token_expiry = _now_utc() + timedelta(hours=20)
        return tok

    def _cfg(self) -> Dict[str, Any]:
        return _load_json(_cfg_path(self._data_dir), {
            "version": 1,
            "guild_channels": {},
            "streamer_login": os.getenv("TWITCH_STREAMER_LOGIN", "").strip(),
            "live_topic": "twitch_live"
        })

    def _save_cfg(self, obj: Dict[str, Any]) -> None:
        _save_json(_cfg_path(self._data_dir), obj)

    def _schedule(self) -> Dict[str, Any]:
        return _load_json(_schedule_path(self._data_dir), {"version": 1, "timezone": os.getenv("TZ_NAME", "Europe/Istanbul"), "slots": []})

    def _save_schedule(self, obj: Dict[str, Any]) -> None:
        _save_json(_schedule_path(self._data_dir), obj)

    def _milestones(self) -> Dict[str, Any]:
        return _load_json(_milestones_path(self._data_dir), {"version": 1, "follower_thresholds": [100, 250, 500, 1000, 2000, 5000], "last_followers": 0, "last_announced": 0})

    def _save_milestones(self, obj: Dict[str, Any]) -> None:
        _save_json(_milestones_path(self._data_dir), obj)

    @app_commands.command(name="set_channel", description="Admin: set the Discord channel for Twitch live notifications")
    @app_commands.describe(channel="Target channel")
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need Manage Server permission.", ephemeral=True)
            return
        cfg = self._cfg()
        gc = cfg.get("guild_channels", {})
        gc[str(interaction.guild_id)] = int(channel.id)
        cfg["guild_channels"] = gc
        self._save_cfg(cfg)
        await interaction.response.send_message(f"Twitch live notifications will be posted in {channel.mention}.", ephemeral=True)

    @app_commands.command(name="status", description="Show current stream status (best-effort)")
    async def status(self, interaction: discord.Interaction):
        login = (self._cfg().get("streamer_login") or "").strip()
        if not login:
            await interaction.response.send_message("TWITCH_STREAMER_LOGIN is not set and no login configured.", ephemeral=True)
            return
        tok = await self._ensure_app_token()
        if not tok:
            await interaction.response.send_message("Twitch API credentials missing (TWITCH_CLIENT_ID/SECRET).", ephemeral=True)
            return
        session = await self._ensure_session()
        uid = await _get_user_id(session, tok, login)
        if not uid:
            await interaction.response.send_message("Could not resolve streamer user ID.", ephemeral=True)
            return
        stream = await _get_stream(session, tok, uid)
        if not stream:
            await interaction.response.send_message("Offline.")
            return
        title = stream.get("title", "")
        game = stream.get("game_name", "")
        started_at = stream.get("started_at", "")
        url = f"https://twitch.tv/{login}"
        embed = discord.Embed(title="LIVE on Twitch", description=title or "(no title)")
        if game:
            embed.add_field(name="Category", value=game, inline=True)
        if started_at:
            embed.add_field(name="Started", value=started_at, inline=True)
        embed.add_field(name="Watch", value=url, inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="schedule_add", description="Admin: add a weekly schedule slot (0=Mon .. 6=Sun)")
    @app_commands.describe(dow="Day of week (0=Mon .. 6=Sun)", hour="Hour (0-23)", minute="Minute (0-59)", label="Optional label")
    async def schedule_add(self, interaction: discord.Interaction, dow: int, hour: int, minute: int, label: str = ""):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need Manage Server permission.", ephemeral=True)
            return
        if dow < 0 or dow > 6 or hour < 0 or hour > 23 or minute < 0 or minute > 59:
            await interaction.response.send_message("Invalid time. Use dow 0-6, hour 0-23, minute 0-59.", ephemeral=True)
            return
        sched = self._schedule()
        slots = sched.get("slots", [])
        slots.append({"dow": int(dow), "hour": int(hour), "minute": int(minute), "label": (label or "").strip()})
        sched["slots"] = slots
        self._save_schedule(sched)
        await interaction.response.send_message("Added schedule slot.", ephemeral=True)

    @app_commands.command(name="schedule_list", description="List schedule slots")
    async def schedule_list(self, interaction: discord.Interaction):
        sched = self._schedule()
        slots = sched.get("slots", [])
        if not slots:
            await interaction.response.send_message("No schedule slots configured.", ephemeral=True)
            return
        dow_names = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
        lines = []
        for s in slots:
            dow = int(s.get("dow", 0))
            lines.append(f"• {dow_names[dow]} {int(s.get('hour',0)):02d}:{int(s.get('minute',0)):02d} — {s.get('label','').strip() or 'Stream'}")
        embed = discord.Embed(title="Twitch schedule", description="
".join(lines)[:4096])
        embed.add_field(name="Timezone", value=str(sched.get("timezone") or "UTC"), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="next", description="Countdown to the next scheduled stream")
    async def next(self, interaction: discord.Interaction):
        sched = self._schedule()
        nxt = _next_scheduled(sched)
        if not nxt:
            await interaction.response.send_message("No schedule slots configured.")
            return
        now = datetime.now(nxt.tzinfo) if nxt.tzinfo else datetime.utcnow()
        delta = nxt - now
        embed = discord.Embed(title="Next stream", description=f"Starts in **{_format_delta(delta)}**")
        embed.add_field(name="Scheduled time", value=nxt.isoformat(), inline=False)
        embed.add_field(name="Timezone", value=str(sched.get("timezone") or "UTC"), inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="milestones_set", description="Admin: set follower milestone thresholds (comma-separated)")
    @app_commands.describe(thresholds="Example: 100,250,500,1000")
    async def milestones_set(self, interaction: discord.Interaction, thresholds: str):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need Manage Server permission.", ephemeral=True)
            return
        parts = [p.strip() for p in (thresholds or "").split(",") if p.strip()]
        vals = []
        for p in parts:
            try:
                v = int(p)
                if v > 0:
                    vals.append(v)
            except Exception:
                pass
        vals = sorted(set(vals))
        if not vals:
            await interaction.response.send_message("No valid thresholds provided.", ephemeral=True)
            return
        m = self._milestones()
        m["follower_thresholds"] = vals
        self._save_milestones(m)
        await interaction.response.send_message(f"Set follower milestones to: {', '.join(map(str, vals))}", ephemeral=True)

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

async def register_twitch_stream(bot: discord.Client, data_dir: str) -> None:
    group = TwitchGroup(bot, data_dir)
    bot.tree.add_command(group)

    # Background poller: stream online/offline
    if not hasattr(bot, "_twitch_stream_poller"):
        async def _poll_loop():
            await bot.wait_until_ready()
            while not bot.is_closed():
                try:
                    cfg = group._cfg()
                    login = (cfg.get("streamer_login") or "").strip()
                    if login:
                        tok = await group._ensure_app_token()
                        if tok:
                            session = await group._ensure_session()
                            uid = await _get_user_id(session, tok, login)
                            if uid:
                                stream = await _get_stream(session, tok, uid)
                                is_live = bool(stream)
                                prev_live = bool(group._last_live_state.get("is_live"))

                                # Notify transitions
                                if is_live and not prev_live:
                                    title = stream.get("title", "")
                                    game = stream.get("game_name", "")
                                    url = f"https://twitch.tv/{login}"
                                    embed = discord.Embed(title="Stream is LIVE", description=title or "(no title)")
                                    if game:
                                        embed.add_field(name="Category", value=game, inline=True)
                                    embed.add_field(name="Watch", value=url, inline=False)
                                    # Send to all configured guild channels
                                    for g in bot.guilds:
                                        chan_id = cfg.get("guild_channels", {}).get(str(g.id))
                                        if chan_id:
                                            ch = g.get_channel(int(chan_id))
                                            if isinstance(ch, discord.TextChannel):
                                                await ch.send(embed=embed)

                                if (not is_live) and prev_live:
                                    url = f"https://twitch.tv/{login}"
                                    embed = discord.Embed(title="Stream ended", description="The stream is now offline.")
                                    embed.add_field(name="Channel", value=url, inline=False)
                                    for g in bot.guilds:
                                        chan_id = cfg.get("guild_channels", {}).get(str(g.id))
                                        if chan_id:
                                            ch = g.get_channel(int(chan_id))
                                            if isinstance(ch, discord.TextChannel):
                                                await ch.send(embed=embed)

                                group._last_live_state = {
                                    "is_live": is_live,
                                    "started_at": stream.get("started_at", "") if stream else "",
                                    "title": stream.get("title", "") if stream else "",
                                    "game": stream.get("game_name", "") if stream else "",
                                }

                    # Milestone tracker (best-effort)
                    user_token = os.getenv("TWITCH_USER_ACCESS_TOKEN", "").strip()
                    moderator_id = os.getenv("TWITCH_MODERATOR_ID", "").strip()
                    if user_token and moderator_id:
                        cfg = group._cfg()
                        login = (cfg.get("streamer_login") or "").strip()
                        if login:
                            session = await group._ensure_session()
                            uid = await _get_user_id(session, await group._ensure_app_token() or "", login)
                            if uid:
                                followers = await _get_followers_count(session, user_token, uid, moderator_id)
                                if followers is not None:
                                    ms = group._milestones()
                                    last = int(ms.get("last_followers", 0) or 0)
                                    ms["last_followers"] = followers
                                    thresholds = [int(x) for x in (ms.get("follower_thresholds") or []) if int(x) > 0]
                                    thresholds = sorted(set(thresholds))
                                    # announce first threshold crossed above last_announced
                                    last_ann = int(ms.get("last_announced", 0) or 0)
                                    crossed = [t for t in thresholds if last_ann < t <= followers]
                                    if crossed:
                                        t = max(crossed)
                                        ms["last_announced"] = t
                                        _save_json(_milestones_path(group._data_dir), ms)
                                        embed = discord.Embed(title="Follower milestone reached!", description=f"We just hit **{t}** followers on Twitch.")
                                        embed.add_field(name="Channel", value=f"https://twitch.tv/{login}", inline=False)
                                        for g in bot.guilds:
                                            chan_id = cfg.get("guild_channels", {}).get(str(g.id))
                                            if chan_id:
                                                ch = g.get_channel(int(chan_id))
                                                if isinstance(ch, discord.TextChannel):
                                                    await ch.send(embed=embed)
                                    _save_json(_milestones_path(group._data_dir), ms)

                except Exception:
                    # avoid crashing the loop
                    pass
                await asyncio.sleep(int(os.getenv("TWITCH_POLL_SECONDS", "60")))

        bot._twitch_stream_poller = asyncio.create_task(_poll_loop())

    await bot.tree.sync()

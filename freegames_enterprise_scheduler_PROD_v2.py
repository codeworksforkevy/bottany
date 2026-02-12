
# FreeGames Enterprise Scheduler PRO v2
# Upgrades applied:
# - Distributed lock (optional Redis)
# - Offer diff detection (new-only posting)
# - Rate limit guard
# - Metrics tracking
# - Isolation Forest anomaly hook (optional)
# - Closure-safe slash commands

from __future__ import annotations

import os
import json
import hashlib
import datetime as dt
from typing import List

import discord
from discord.ext import tasks
from discord import app_commands

from freegames_logic import gather_offers

# Optional Redis
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except Exception:
    REDIS_AVAILABLE = False

# Optional ML
try:
    from sklearn.ensemble import IsolationForest
    import numpy as np
    ML_AVAILABLE = True
except Exception:
    ML_AVAILABLE = False

STATE_DIR = "data/freegames_state"
CONFIG_FILE = "data/freegames_channels.json"
GLOBAL_STATE_FILE = "data/freegames_global_state.json"
METRICS_FILE = "data/freegames_metrics.json"

REDIS_URL = os.getenv("REDIS_URL")
LOCK_KEY = "freegames_lock"

PLATFORM_COLORS = {
    "epic": 0x2F3136,
    "gog": 0x86328A,
    "humble": 0xCC2929,
    "luna": 0x00A8E1,
}

RATE_GUARD_SECONDS = 30


def _load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)


def _offers_hash(offers):
    raw = "|".join(sorted(f"{o.platform}-{o.title}-{o.url}" for o in offers))
    return hashlib.sha256(raw.encode()).hexdigest()


def _build_embed(offer):
    color = PLATFORM_COLORS.get(offer.platform.lower(), 0xA7D8FF)
    embed = discord.Embed(
        title=offer.title,
        url=offer.url,
        color=color,
        timestamp=dt.datetime.utcnow()
    )

    embed.add_field(name="Status", value="FREE TO KEEP", inline=False)

    if getattr(offer, "thumbnail", None):
        embed.set_thumbnail(url=offer.thumbnail)

    embed.add_field(name="Platform", value=offer.platform.upper(), inline=False)
    embed.set_footer(text="Bottany • Enterprise Production")

    return embed


class FreeGamesEnterprise:

    def __init__(self, bot: discord.Client, registry_path: str):
        self.bot = bot
        self.registry_path = registry_path
        self.redis = redis.from_url(REDIS_URL) if REDIS_AVAILABLE and REDIS_URL else None
        self.last_rate_push = 0
        self.metrics = {"last_run": None, "offers_count": 0, "new_detected": 0}
        self.loop.start()

    async def _acquire_lock(self):
        if not self.redis:
            return True
        return await self.redis.set(LOCK_KEY, "1", ex=60, nx=True)

    async def _release_lock(self):
        if self.redis:
            await self.redis.delete(LOCK_KEY)

    def _detect_anomaly(self, offers_count: int):
        if not ML_AVAILABLE:
            return False
        history = _load_json(GLOBAL_STATE_FILE, {}).get("history_counts", [])
        if len(history) < 5:
            return False
        model = IsolationForest(contamination=0.2)
        X = np.array(history).reshape(-1, 1)
        model.fit(X)
        prediction = model.predict([[offers_count]])
        return prediction[0] == -1

    @tasks.loop(minutes=15)
    async def loop(self):

        if not await self._acquire_lock():
            return

        try:
            offers = await gather_offers(self.registry_path)
            now_ts = dt.datetime.utcnow().timestamp()

            # Rate guard
            if now_ts - self.last_rate_push < RATE_GUARD_SECONDS:
                return

            state = _load_json(GLOBAL_STATE_FILE, {})
            old_titles = set(state.get("titles", []))

            new_offers = [o for o in offers if o.title not in old_titles]

            if not new_offers:
                return

            anomaly = self._detect_anomaly(len(offers))

            configs = _load_json(CONFIG_FILE, {})

            for guild_id, channel_id in configs.items():
                channel = self.bot.get_channel(int(channel_id))
                if not channel:
                    continue

                for offer in new_offers:
                    embed = _build_embed(offer)
                    if anomaly:
                        embed.color = 0xFF0000
                        embed.add_field(name="⚠ Anomaly Detected", value="Unusual offer spike", inline=False)
                    await channel.send(embed=embed)

            self.metrics["last_run"] = dt.datetime.utcnow().isoformat()
            self.metrics["offers_count"] = len(offers)
            self.metrics["new_detected"] = len(new_offers)

            _save_json(METRICS_FILE, self.metrics)
            _save_json(GLOBAL_STATE_FILE, {
                "titles": [o.title for o in offers],
                "history_counts": state.get("history_counts", []) + [len(offers)]
            })

            self.last_rate_push = now_ts

        finally:
            await self._release_lock()


def register_freegames_admin(tree: app_commands.CommandTree, enterprise: FreeGamesEnterprise):

    @tree.command(name="freegames_monitor", description="Production metrics overview.")
    async def monitor(interaction: discord.Interaction):
        metrics = _load_json(METRICS_FILE, {})
        embed = discord.Embed(title="FreeGames Enterprise Metrics", color=0x00FFAA)
        for k, v in metrics.items():
            embed.add_field(name=k, value=str(v), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    def make_platform_command(platform_name: str):
        @tree.command(name=f"freegames_{platform_name}", description=f"Show current {platform_name} offers.")
        async def platform_cmd(interaction: discord.Interaction):
            await interaction.response.defer()
            offers = await gather_offers(enterprise.registry_path)
            offers = [o for o in offers if o.platform.lower() == platform_name]

            if not offers:
                await interaction.followup.send("No active offers found.")
                return

            for offer in offers:
                embed = _build_embed(offer)
                await interaction.followup.send(embed=embed)

        return platform_cmd

    for p in ["epic", "gog", "humble", "luna"]:
        make_platform_command(p)


from __future__ import annotations

import os
import json
import datetime as dt

import discord
from discord.ext import tasks
from discord import app_commands

from freegames_logic import gather_offers

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except Exception:
    REDIS_AVAILABLE = False

try:
    from sklearn.ensemble import IsolationForest
    import numpy as np
    ML_AVAILABLE = True
except Exception:
    ML_AVAILABLE = False


GLOBAL_STATE_FILE = "data/freegames_global_state.json"

REDIS_URL = os.getenv("REDIS_URL")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

LOCK_KEY = "freegames_lock"
RATE_GUARD_SECONDS = 30

PLATFORM_COLORS = {
    "epic": 0x2F3136,
    "gog": 0x86328A,
    "humble": 0xCC2929,
    "luna": 0x00A8E1,
}


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


def _build_embed(offer):
    color = PLATFORM_COLORS.get(offer.platform.lower(), 0xA7D8FF)
    embed = discord.Embed(
        title=offer.title,
        url=offer.url,
        color=color,
        timestamp=dt.datetime.utcnow()
    )
    embed.add_field(name="Status", value="FREE TO KEEP", inline=False)
    embed.add_field(name="Platform", value=offer.platform.upper(), inline=False)

    if getattr(offer, "thumbnail", None):
        embed.set_thumbnail(url=offer.thumbnail)

    return embed


class FreeGamesEnterprise:

    def __init__(self, bot: discord.Client, registry_path: str):
        self.bot = bot
        self.registry_path = registry_path
        self.redis = redis.from_url(REDIS_URL) if REDIS_AVAILABLE and REDIS_URL else None
        self.last_rate_push = 0
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
        state = _load_json(GLOBAL_STATE_FILE, {})
        history = state.get("history_counts", [])
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

            if now_ts - self.last_rate_push < RATE_GUARD_SECONDS:
                return

            state = _load_json(GLOBAL_STATE_FILE, {})
            old_titles = set(state.get("titles", []))

            new_offers = [o for o in offers if o.title not in old_titles]

            if not new_offers:
                return

            anomaly = self._detect_anomaly(len(offers))

            for guild in self.bot.guilds:
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        for offer in new_offers:
                            embed = _build_embed(offer)
                            if anomaly:
                                embed.color = 0xFF0000
                                embed.add_field(name="⚠ Anomaly", value="Unusual offer spike detected.", inline=False)
                            await channel.send(embed=embed)
                        break

            _save_json(GLOBAL_STATE_FILE, {
                "titles": [o.title for o in offers],
                "history_counts": state.get("history_counts", []) + [len(offers)]
            })

            self.last_rate_push = now_ts

        finally:
            await self._release_lock()


def register_commands(tree: app_commands.CommandTree):

    @tree.command(name="freegames_monitor", description="Show freegames metrics.")
    async def monitor(interaction: discord.Interaction):
        state = _load_json(GLOBAL_STATE_FILE, {})
        embed = discord.Embed(title="FreeGames Metrics", color=0x00FFAA)
        embed.add_field(name="Tracked Offers", value=str(len(state.get("titles", []))), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


# =========================
# BOT ENTRY POINT
# =========================

intents = discord.Intents.default()
intents.guilds = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    enterprise = FreeGamesEnterprise(bot, registry_path="data")
    register_commands(tree)
    await tree.sync()


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN not set in environment variables.")
    bot.run(DISCORD_TOKEN)

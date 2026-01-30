# main.py
from __future__ import annotations

import os
import asyncio
import traceback
import discord

# Commands
from commands.academic_trivia import register_academic_trivia
from commands.twitch_badges import register_twitch_badges

# Optional modules (may not exist in older deployments)
try:
    from commands.free_games import register_free_games
except Exception:
    register_free_games = None  # type: ignore

try:
    from commands.gaming_news import register_gaming_news
except Exception:
    register_gaming_news = None  # type: ignore


DATA_DIR = os.getenv("DATA_DIR", "data")
TZ_NAME = os.getenv("TZ_NAME", "UTC")


class BottanyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)

    async def setup_hook(self) -> None:
        await register_all(self)
        await self.tree.sync()


async def _maybe_call(fn, *args, **kwargs):
    """
    Supports sync or async registrar functions.
    """
    if fn is None:
        return
    try:
        res = fn(*args, **kwargs)
        if asyncio.iscoroutine(res):
            await res
    except Exception as e:
        print(f"[register_all] ERROR in {getattr(fn, '__module__', '?')}.{getattr(fn, '__name__', '?')}: {type(e).__name__}: {e}")
        traceback.print_exc()


async def register_all(client: BottanyClient) -> None:
    tree = client.tree

    # Academic trivia expects (client, tree, data_dir)
    await _maybe_call(register_academic_trivia, client, tree, DATA_DIR)
    print("[register_all] Registered academic trivia")

    # Twitch badges
    await _maybe_call(register_twitch_badges, client, tree, DATA_DIR)
    print("[register_all] Registered twitch badges")

    # Free games (optional)
    await _maybe_call(register_free_games, client, tree, DATA_DIR)
    if register_free_games:
        print("[register_all] Registered free games")

    # Gaming news (optional)
    await _maybe_call(register_gaming_news, client, tree, DATA_DIR)
    if register_gaming_news:
        print("[register_all] Registered gaming news")


def main() -> None:
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Missing DISCORD_TOKEN.")
    client = BottanyClient()
    client.run(token)


if __name__ == "__main__":
    main()

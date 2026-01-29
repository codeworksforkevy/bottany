import asyncio
import os
import discord
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN.")

class BottanyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await register_all(self)
        await self.tree.sync()

async def register_all(client):
    # Academic trivia
    from commands.academic_trivia import register_academic_trivia
    await register_academic_trivia(client)

    # Twitch badges (single /twitch group)
    from commands.twitch_badges import register_twitch_badges
    await register_twitch_badges(client)

    # Twitch drops reuses existing group
    try:
        from commands.twitch_badges_and_drops import register_twitch_badges_and_drops
        await register_twitch_badges_and_drops(client)
    except Exception as e:
        print("[register_all] drops skipped:", e)

    # Free games
    from commands.free_games import register_free_games
    await register_free_games(client)

    # Gaming news
    from commands.gaming_news import register_gaming_news
    await register_gaming_news(client)

def main():
    client = BottanyClient()
    client.run(DISCORD_TOKEN)

if __name__ == "__main__":
    main()

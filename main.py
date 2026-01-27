import os
import asyncio
import discord
from dotenv import load_dotenv
from discord import app_commands

from commands.academic_trivia import register_academic_trivia
from src.utils import ensure_dir


def get_env(name: str, default: str = "") -> str:
    val = os.getenv(name)
    return val if val is not None and val != "" else default


async def run() -> None:
    load_dotenv()

    token = get_env("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("Missing DISCORD_TOKEN in environment.")

    data_dir = os.path.abspath(get_env("DATA_DIR", "./data"))
    ensure_dir(data_dir)

    intents = discord.Intents.none()
    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)

    register_academic_trivia(tree, data_dir)

    @client.event
    async def on_ready():
        # Sync global commands
        await tree.sync()
        print(f"Logged in as {client.user} (id={client.user.id})")
        print("Slash commands synced: /academictrivia")

    await client.start(token)


if __name__ == "__main__":
    asyncio.run(run())

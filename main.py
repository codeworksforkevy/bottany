
import os, inspect
from pathlib import Path
import discord
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()
DATA_DIR = Path(__file__).resolve().parent / "data"

def _log(m): print(m, flush=True)

async def _maybe(fn,*a):
    r = fn(*a)
    if inspect.isawaitable(r): return await r
    return r

async def _call(fn, client, tree, data_dir):
    try:
        return await _maybe(fn, client, tree, data_dir)
    except TypeError:
        return await _maybe(fn, client, data_dir)

async def register_all(client, tree):
    mods = [
        ("commands.free_games","register_free_games"),
        ("commands.weekly","register_weekly"),
        ("commands.belgium","register_belgium"),
    ]
    for m,f in mods:
        try:
            mod = __import__(m, fromlist=[f])
            await _call(getattr(mod,f), client, tree, DATA_DIR)
            _log(f"Registered {m}.{f}")
        except Exception as e:
            _log(f"Skip {m}.{f}: {e}")

class BottanyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
    async def setup_hook(self):
        await register_all(self, self.tree)
        await self.tree.sync()

def main():
    client = BottanyClient()
    client.run(os.getenv("DISCORD_TOKEN"))

if __name__=="__main__":
    main()

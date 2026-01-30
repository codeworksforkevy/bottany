import os
import asyncio
import inspect
import discord
from discord import app_commands
from dotenv import load_dotenv

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def _maybe_call(fn, *, client, tree, data_dir):
    """Call a registrar with a flexible signature.

    Supported registrar signatures (sync or async):
      - fn(tree, data_dir)
      - fn(client, tree, data_dir)
      - fn(tree)
      - fn(client)
    """
    sig = inspect.signature(fn)
    params = list(sig.parameters.values())

    mapping = {
        "client": client,
        "bot": client,
        "tree": tree,
        "data_dir": data_dir,
        "DATA_DIR": data_dir,
    }

    # Prefer name-based mapping
    args = []
    used_named = False
    for p in params:
        if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            continue
        if p.name in mapping:
            args.append(mapping[p.name])
            used_named = True

    if not used_named:
        # Fallback by arity
        n = len([p for p in params if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)])
        if n == 3:
            args = [client, tree, data_dir]
        elif n == 2:
            args = [tree, data_dir]
        elif n == 1:
            args = [tree]
        else:
            args = []

    res = fn(*args)
    if inspect.isawaitable(res):
        return res
    return None

async def register_all(client: discord.Client):
    tree = client.tree  # type: ignore[attr-defined]
    data_dir = DATA_DIR

    registrars = [
        ("commands.academic_trivia", "register_academic_trivia"),
        ("commands.free_games", "register_free_games"),
        ("commands.twitch_badges", "register_twitch_badges"),
        ("commands.twitch_badges_and_drops", "register_twitch_badges_and_drops"),
        ("commands.gaming_news", "register_gaming_news"),
    ]

    for mod_name, fn_name in registrars:
        try:
            mod = __import__(mod_name, fromlist=[fn_name])
            fn = getattr(mod, fn_name, None)
            if not fn:
                print(f"[register_all] Skipped {mod_name}: missing {fn_name}")
                continue
            awaitable = _maybe_call(fn, client=client, tree=tree, data_dir=data_dir)
            if awaitable is not None:
                await awaitable
            print(f"[register_all] Registered via {mod_name}.{fn_name}()")
        except Exception as e:
            print(f"[register_all] ERROR in {mod_name}.{fn_name}: {type(e).__name__}: {e}")

    try:
        await tree.sync()
        print("Slash commands synced.")
    except Exception as e:
        print(f"[register_all] tree.sync ERROR: {type(e).__name__}: {e}")

class BottanyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await register_all(self)

def main():
    load_dotenv()
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("Missing DISCORD_TOKEN.")
    client = BottanyClient()
    client.run(token)

if __name__ == "__main__":
    main()

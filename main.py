# main.py
import os
import asyncio
import inspect
from pathlib import Path

import discord
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).resolve().parent / "data"

def _log(msg: str) -> None:
    print(msg, flush=True)

async def _maybe_call(fn, *args, **kwargs):
    """
    Call sync or async registrar; supports varying signatures.
    """
    res = fn(*args, **kwargs)
    if inspect.isawaitable(res):
        return await res
    return res

async def _call_registrar(fn, client: discord.Client, tree: app_commands.CommandTree, data_dir: Path):
    """
    Try common registrar signatures:
      (client, tree, data_dir)
      (client, data_dir)
      (client, tree)
      (client)
    """
    sig = None
    try:
        sig = inspect.signature(fn)
    except Exception:
        sig = None

    # Preferred explicit signature
    if sig is not None:
        nparams = len([p for p in sig.parameters.values()
                       if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)])
        if nparams >= 3:
            return await _maybe_call(fn, client, tree, data_dir)
        if nparams == 2:
            # Ambiguous: try (client, data_dir) then (client, tree)
            try:
                return await _maybe_call(fn, client, data_dir)
            except TypeError:
                return await _maybe_call(fn, client, tree)
        if nparams == 1:
            return await _maybe_call(fn, client)

    # Fallbacks
    for args in [(client, tree, data_dir), (client, data_dir), (client, tree), (client,)]:
        try:
            return await _maybe_call(fn, *args)
        except TypeError:
            continue
    raise TypeError(f"Unsupported registrar signature for {getattr(fn,'__name__','<fn>')}")

async def register_all(client: discord.Client, tree: app_commands.CommandTree) -> None:
    """
    Import + register all slash commands. Each module exposes a registrar.
    """
    # NOTE: keep these imports inside to avoid failing the whole bot at import time
    modules = [
        ("commands.academic_trivia", "register_academic_trivia"),
        ("commands.twitch_badges", "register_twitch_badges"),
        ("commands.twitch_badges_and_drops", "register_twitch_badges_and_drops"),
        ("commands.free_games", "register_free_games"),
        ("commands.gaming_news", "register_gaming_news"),
    ]

    for mod_name, fn_name in modules:
        try:
            mod = __import__(mod_name, fromlist=[fn_name])
            fn = getattr(mod, fn_name)
        except Exception as e:
            _log(f"[register_all] Skipped {mod_name}.{fn_name}: {type(e).__name__}: {e}")
            continue

        try:
            await _call_registrar(fn, client, tree, DATA_DIR)
            _log(f"[register_all] Registered via {mod_name}.{fn_name}()")
        except Exception as e:
            _log(f"[register_all] ERROR in {mod_name}.{fn_name}: {type(e).__name__}: {e}")

class BottanyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        # You can enable more intents if you later need message content / guild members, etc.
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self) -> None:
        await register_all(self, self.tree)

        # Sync globally (can take time to propagate), but ensures Railway has the commands registered.
        try:
            await self.tree.sync()
            _log("Slash commands synced.")
        except Exception as e:
            _log(f"[setup_hook] tree.sync failed: {type(e).__name__}: {e}")

def main() -> None:
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("Missing DISCORD_TOKEN.")
    client = BottanyClient()
    client.run(token)

if __name__ == "__main__":
    main()

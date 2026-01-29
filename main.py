\
import os
import asyncio
import inspect
import importlib
from typing import Any, Dict, Optional

import discord
from discord import app_commands
from dotenv import load_dotenv


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(key)
    return v if v not in (None, "") else default


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _call_with_accepted_kwargs(fn, kwargs: Dict[str, Any]):
    """
    Call a function with only the kwargs it actually accepts.
    Supports both sync and async register_* functions.
    """
    try:
        sig = inspect.signature(fn)
        accepted = {k: v for k, v in kwargs.items() if k in sig.parameters}
        res = fn(**accepted)
    except TypeError:
        # Fallback: if signature inspection fails (builtins, C-ext), try a best-effort call.
        res = fn(**kwargs)
    return res


async def register_all(client: discord.Client, tree: app_commands.CommandTree, data_dir: str) -> None:
    """
    Dynamically load/register command modules if present.

    This prevents "silent" missing commands on Railway (module not imported => command not registered),
    and also fixes RuntimeWarning: coroutine 'register_*' was never awaited by awaiting if needed.
    """
    # Common kwargs patterns across your modules
    kwargs: Dict[str, Any] = {
        "bot": client,
        "client": client,
        "tree": tree,
        "DATA_DIR": data_dir,
        "data_dir": data_dir,
    }

    registrars = [
        # Academic trivia
        ("commands.academic_trivia", ["register_academic_trivia", "register_academictrivia", "register_academic_trivia_command"]),
        # Twitch badges (+ pager)
        ("commands.twitch_badges", ["register_badges", "register_twitch_badges"]),
        ("commands.twitch_badges_and_drops", ["register_twitch_badges_and_drops", "register_badges_and_drops"]),
        # Free games
        ("commands.free_games", ["register_free_games", "register_freegames", "register_free_games_command"]),
        # Gaming news
        ("commands.gaming_news", ["register_gaming_news"]),
    ]

    loaded_any = False

    for mod_name, fn_names in registrars:
        try:
            mod = importlib.import_module(mod_name)
        except Exception as e:
            print(f"[register_all] Skipped {mod_name}: {type(e).__name__}: {e}")
            continue

        fn = None
        for cand in fn_names:
            if hasattr(mod, cand):
                fn = getattr(mod, cand)
                break

        if not callable(fn):
            print(f"[register_all] Module {mod_name} loaded but no registrar found (looked for {fn_names}).")
            continue

        try:
            res = _call_with_accepted_kwargs(fn, kwargs)
            if inspect.isawaitable(res):
                await res
            loaded_any = True
            print(f"[register_all] Registered via {mod_name}.{fn.__name__}()")
        except Exception as e:
            print(f"[register_all] ERROR in {mod_name}.{getattr(fn,'__name__','<unknown>')}: {type(e).__name__}: {e}")

    if not loaded_any:
        print("[register_all] WARNING: No command modules were registered. Check imports/paths.")


class BottanyClient(discord.Client):
    def __init__(self, data_dir: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_dir = data_dir
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self) -> None:
        # 1) Register all commands (imports matter!)
        await register_all(self, self.tree, self.data_dir)

        # 2) Sync command tree once during startup (Railway-safe)
        await self.tree.sync()
        print("Slash commands synced.")


async def run() -> None:
    load_dotenv()

    token = get_env("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("Missing DISCORD_TOKEN.")

    # DATA_DIR default: ./data relative to main.py location (more robust than CWD)
    here = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.abspath(get_env("DATA_DIR", os.path.join(here, "data")))
    ensure_dir(data_dir)

    intents = discord.Intents.none()
    client = BottanyClient(data_dir=data_dir, intents=intents)

    @client.event
    async def on_ready():
        # setup_hook already synced; this is just a reliable banner for logs.
        print(f"Logged in as {client.user} (id={client.user.id})")

    await client.start(token)


if __name__ == "__main__":
    asyncio.run(run())

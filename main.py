import os
import asyncio
import inspect
from typing import Any, Callable, Optional

import discord
from discord import app_commands
from dotenv import load_dotenv


def _env(name: str, default: str = "") -> str:
    v = os.getenv(name)
    return v if v not in (None, "") else default


async def _maybe_await(x: Any) -> Any:
    # Handles: coroutine object OR async function return.
    if inspect.isawaitable(x):
        return await x
    return x


async def call_registrar(
    fn: Callable[..., Any],
    *,
    client: discord.Client,
    tree: app_commands.CommandTree,
    data_dir: str,
) -> None:
    """Call a register_* function with best-effort argument matching.

    Different modules in this repo use slightly different signatures:
    - register_x(client)
    - register_x(client, tree)
    - register_x(client, tree, data_dir)
    - register_x(tree, data_dir)
    - register_x(bot, DATA_DIR)
    etc.

    We inspect the function signature and pass what it can accept.
    """
    sig = inspect.signature(fn)
    params = list(sig.parameters.values())

    kwargs: dict[str, Any] = {}
    for p in params:
        name = p.name.lower()

        if name in ("client", "bot"):
            kwargs[p.name] = client
        elif name in ("tree", "command_tree", "cmd_tree"):
            kwargs[p.name] = tree
        elif name in ("data_dir", "datadir", "data_path", "data_root"):
            kwargs[p.name] = data_dir
        # Some modules take a config dict; we won't guess it here.

    # If it's purely positional with no helpful names, fall back by arity.
    if not kwargs and all(p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD) for p in params):
        arity = len(params)
        if arity == 1:
            return await _maybe_await(fn(client))
        if arity == 2:
            # prefer (client, data_dir) if param name hints that, else (client, tree)
            if params[1].name.lower() in ("data_dir", "datadir", "data_path", "data_root"):
                return await _maybe_await(fn(client, data_dir))
            return await _maybe_await(fn(client, tree))
        if arity >= 3:
            return await _maybe_await(fn(client, tree, data_dir))

    return await _maybe_await(fn(**kwargs))


def _has_root_command(tree: app_commands.CommandTree, name: str) -> bool:
    name = name.lower()
    for c in tree.get_commands():
        if getattr(c, "name", "").lower() == name:
            return True
    return False


async def register_all(client: discord.Client, tree: app_commands.CommandTree, data_dir: str) -> None:
    """Import and register all slash command modules."""
    # Order matters when there are overlapping groups.
    modules: list[tuple[str, str]] = [
        ("commands.academic_trivia", "register_academic_trivia"),
        # Twitch: prefer combined module if it exists, otherwise basic badges.
        ("commands.twitch_badges_and_drops", "register_twitch_badges_and_drops"),
        ("commands.twitch_badges", "register_twitch_badges"),
        ("commands.free_games", "register_free_games"),
        ("commands.gaming_news", "register_gaming_news"),
    ]

    for mod_name, fn_name in modules:
        try:
            mod = __import__(mod_name, fromlist=[fn_name])
            fn = getattr(mod, fn_name)

            # Avoid "CommandAlreadyRegistered: twitch"
            if mod_name.endswith("twitch_badges") and _has_root_command(tree, "twitch"):
                print(f"[register_all] Skipped {mod_name}.{fn_name} (twitch group already registered)")
                continue

            await call_registrar(fn, client=client, tree=tree, data_dir=data_dir)
            print(f"[register_all] Registered via {mod_name}.{fn_name}()")
        except ModuleNotFoundError as e:
            print(f"[register_all] Skipped {mod_name}: {e.__class__.__name__}: {e}")
        except Exception as e:
            print(f"[register_all] ERROR in {mod_name}.{fn_name}: {e.__class__.__name__}: {e}")


class BottanyClient(discord.Client):
    def __init__(self, *, data_dir: str):
        intents = discord.Intents.none()
        super().__init__(intents=intents)
        self.data_dir = data_dir
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self) -> None:
        # Register commands BEFORE syncing
        await register_all(self, self.tree, self.data_dir)
        try:
            await self.tree.sync()
            print("Slash commands synced.")
        except Exception as e:
            print(f"[sync] ERROR: {e.__class__.__name__}: {e}")

    async def on_ready(self) -> None:
        if self.user:
            print(f"Logged in as {self.user} (id={self.user.id})")


def main() -> None:
    load_dotenv()
    token = _env("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("Missing DISCORD_TOKEN.")

    here = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.abspath(_env("DATA_DIR", os.path.join(here, "data")))
    os.makedirs(data_dir, exist_ok=True)

    client = BottanyClient(data_dir=data_dir)
    client.run(token)


if __name__ == "__main__":
    main()

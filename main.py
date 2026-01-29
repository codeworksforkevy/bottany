import os
import sys
import json
import asyncio
import hashlib
import secrets
import importlib
import inspect
from datetime import datetime, timezone

import discord
from discord import app_commands
from dotenv import load_dotenv


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def load_json(path: str, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_join(base_dir: str, *parts: str) -> str:
    joined = os.path.abspath(os.path.join(base_dir, *parts))
    base_abs = os.path.abspath(base_dir)
    if not joined.startswith(base_abs + os.sep) and joined != base_abs:
        raise ValueError("Unsafe path traversal detected.")
    return joined


def daily_index(n: int, day_str: str) -> int:
    h = hashlib.sha256(day_str.encode("utf-8")).hexdigest()
    return int(h, 16) % n


def get_env(name: str, default: str = "") -> str:
    val = os.getenv(name)
    return val if val else default


def make_academictrivia_command(tree: app_commands.CommandTree, data_dir: str) -> None:
    pool_path = safe_join(data_dir, "academic_trivia_pool.json")

    @app_commands.command(
        name="academictrivia",
        description="Open-licensed academic trivia: daily (deterministic) or random."
    )
    @app_commands.describe(mode="Choose 'daily' (same each day) or 'random'")
    async def academictrivia(interaction: discord.Interaction, mode: str = "daily"):
        pool = load_json(pool_path, {"version": "1.0.0", "items": []})
        items = pool.get("items", [])
        if not isinstance(items, list) or len(items) == 0:
            await interaction.response.send_message(
                "Trivia pool is empty. Fill data/academic_trivia_pool.json first.",
                ephemeral=True
            )
            return

        mode = (mode or "daily").strip().lower()
        if mode not in ("daily", "random"):
            await interaction.response.send_message("Invalid mode. Use daily or random.", ephemeral=True)
            return

        if mode == "daily":
            day_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            idx = daily_index(len(items), day_str)
            picked = items[idx]
            title = "Academic Daily Trivia"
            footer = f"UTC day: {day_str} • Pool size: {len(items)}"
        else:
            picked = items[secrets.randbelow(len(items))]
            title = "Academic Trivia (Random)"
            footer = f"Pool size: {len(items)}"

        text = (picked.get("text") or "").strip()
        if not text:
            await interaction.response.send_message("Selected item is empty. Rebuild your pool.", ephemeral=True)
            return

        emb = discord.Embed(title=title, description=text)
        emb.add_field(
            name="Source",
            value=f'{picked.get("source_org","Unknown")} — {picked.get("source_title","")}'.strip(" —"),
            inline=False
        )
        emb.add_field(name="License", value=picked.get("license","(unknown)"), inline=True)
        if picked.get("source_url"):
            emb.add_field(name="Open", value=picked["source_url"], inline=False)
        emb.set_footer(text=footer)

        await interaction.response.send_message(embed=emb)

    tree.add_command(academictrivia)


def _try_register_callable(fn, client: discord.Client, tree: app_commands.CommandTree, data_dir: str) -> bool:
    """Call a register_* function with best-effort argument matching."""
    try:
        sig = inspect.signature(fn)
        kwargs = {}
        for name, p in sig.parameters.items():
            lname = name.lower()
            if lname in ("bot", "client"):
                kwargs[name] = client
            elif lname in ("tree", "command_tree", "cmd_tree"):
                kwargs[name] = tree
            elif lname in ("data_dir", "datadir", "data_path", "data_root"):
                kwargs[name] = data_dir
            else:
                # Don't guess extra params; let it fail loudly in that module.
                pass
        # If it needs positional-only or required params we didn't satisfy, skip.
        for name, p in sig.parameters.items():
            if p.default is inspect._empty and name not in kwargs and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                return False
        fn(**kwargs)
        return True
    except Exception as e:
        print(f"[WARN] register call failed: {getattr(fn,'__name__',fn)} -> {e}")
        return False


def register_optional_command_modules(
    client: discord.Client,
    tree: app_commands.CommandTree,
    data_dir: str,
    modules: list[str],
) -> None:
    """Import commands.<module> and run register_* hooks if present."""
    loaded = []
    for modname in modules:
        try:
            m = importlib.import_module(modname)
        except Exception as e:
            print(f"[INFO] Optional module not loaded: {modname} ({e})")
            continue

        did_any = False
        for attr in dir(m):
            if not attr.startswith("register_"):
                continue
            fn = getattr(m, attr)
            if callable(fn) and _try_register_callable(fn, client, tree, data_dir):
                did_any = True

        if did_any:
            loaded.append(modname)

    if loaded:
        print("[INFO] Registered optional modules:", ", ".join(loaded))


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
    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)

    # Core command(s)
    make_academictrivia_command(tree, data_dir)

    # Optional command modules (keeps main.py small; avoids silent non-registration on Railway)
    register_optional_command_modules(
        client,
        tree,
        data_dir,
        modules=[
            "commands.twitch_badges",
            "commands.twitch_badges_and_drops",
            "commands.twitch_drops",
            "commands.twitch_badges_watch",
            "commands.twitch_stream",
            "commands.twitch_eventsub",
            "commands.free_games",
            "commands.gaming_news",
        ],
    )

    @client.event
    async def on_ready():
        synced = await tree.sync()
        names = [f"/{c.name}" for c in synced]
        print(f"Logged in as {client.user} (id={client.user.id})")
        print("Slash commands synced:", ", ".join(names) if names else "(none)")

    await client.start(token)


if __name__ == "__main__":
    asyncio.run(run())

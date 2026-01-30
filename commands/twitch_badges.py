import os
import json
import discord
from discord import app_commands

# This patch focuses on: correct registrar signature + /badges alias.
# Keep/merge your existing badge pager logic; swap _show_badges with your real implementation.

BADGES_CACHE = "twitch_badges_cache.json"  # stored in data/
DEFAULT_GROUP_NAME = "twitch"

def _cache_path(data_dir: str) -> str:
    # data_dir may already be .../data
    if os.path.basename(data_dir) == "data":
        return os.path.join(data_dir, BADGES_CACHE)
    return os.path.join(data_dir, "data", BADGES_CACHE)

def _load_cache(data_dir: str) -> dict:
    path = _cache_path(data_dir)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def register_twitch_badges(tree: app_commands.CommandTree, data_dir: str):
    """Registrar signature: (tree, data_dir)."""

    async def _show_badges(interaction: discord.Interaction):
        cache = _load_cache(data_dir)
        n_sets = len(cache.get("badge_sets", {})) if isinstance(cache, dict) else 0
        await interaction.response.send_message(
            f"Twitch badges module is loaded. Cached sets: {n_sets}.",
            ephemeral=False
        )

    # Ensure /twitch group exists
    twitch_group = None
    for c in tree.get_commands():
        if isinstance(c, app_commands.Group) and c.name == DEFAULT_GROUP_NAME:
            twitch_group = c
            break
    if twitch_group is None:
        try:
            twitch_group = app_commands.Group(name=DEFAULT_GROUP_NAME, description="Twitch utilities")
            tree.add_command(twitch_group)
        except Exception:
            twitch_group = None

    # /twitch badges
    if twitch_group is not None:
        @twitch_group.command(name="badges", description="Browse Twitch chat badges")
        async def twitch_badges_cmd(interaction: discord.Interaction):
            await _show_badges(interaction)

    # /badges alias (prevents 404 + matches your logs)
    @app_commands.command(name="badges", description="Browse Twitch chat badges (alias of /twitch badges)")
    async def badges_alias(interaction: discord.Interaction):
        await _show_badges(interaction)

    existing = [c.name for c in tree.get_commands()]
    if "badges" not in existing:
        tree.add_command(badges_alias)

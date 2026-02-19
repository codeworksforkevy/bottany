from __future__ import annotations

import os
import json
import datetime
import discord
from discord.ext import tasks
from discord import app_commands

# -------------------------------------------------
# SAFE IMPORTS (freegames logic)
# -------------------------------------------------

try:
    from freegames_logic import (
        fetch_epic_free_games,
        fetch_gog_deals,
        fetch_amazon_luna,
        fetch_humble_bundle,
    )
except Exception:
    def fetch_epic_free_games(): return []
    def fetch_gog_deals(): return []
    def fetch_amazon_luna(): return []
    def fetch_humble_bundle(): return []


# -------------------------------------------------
# CONFIG
# -------------------------------------------------

STATE_FILE = "weekly_digest_state.json"
POST_HOUR_UTC = 18  # Friday 18:00 UTC


# -------------------------------------------------
# JSON UTIL
# -------------------------------------------------

def _load(path: str, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default or {"last_post_iso": ""}


def _save(path: str, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)


# -------------------------------------------------
# HELPERS
# -------------------------------------------------

def _fmt(items, limit=10):
    lines = [f"• {i}" for i in items[:limit]]
    return "\n".join(lines)[:1024]


def _has_any(*groups):
    return any(bool(g) for g in groups)


# -------------------------------------------------
# EMBED BUILDER
# -------------------------------------------------

def build_weekly_embed(epic, gog, luna, humble):

    embed = discord.Embed(
        title="🎮 Weekly Gaming Digest",
        description="Free games & discounts – weekly roundup",
        timestamp=datetime.datetime.utcnow(),
        color=0x2F3136,
    )

    if epic:
        embed.add_field(
            name="Epic Games (Free)",
            value=_fmt(epic),
            inline=False
        )

    if gog:
        embed.add_field(
            name="GOG (Deals)",
            value=_fmt(gog),
            inline=False
        )

    if luna:
        embed.add_field(
            name="Amazon Luna",
            value=_fmt(luna),
            inline=False
        )

    if humble:
        embed.add_field(
            name="Humble Bundle",
            value=_fmt(humble),
            inline=False
        )

    embed.set_footer(text="Auto-generated weekly digest")

    return embed


# -------------------------------------------------
# REGISTER
# -------------------------------------------------

def register_weekly(client: discord.Client, tree, data_dir):

    state_path = os.path.join(data_dir, STATE_FILE)
    state = _load(state_path, {"last_post_iso": ""})

    channel_id = int(os.getenv("WEEKLY_DIGEST_CHANNEL_ID", "0"))

    # -------------------------------------------------
    # GROUP (duplicate-safe)
    # -------------------------------------------------

    existing = tree.get_command("weekly")

    if isinstance(existing, app_commands.Group):
        weekly_group = existing
    else:
        weekly_group = app_commands.Group(
            name="weekly",
            description="Weekly gaming digest tools"
        )
        tree.add_command(weekly_group)

    # -------------------------------------------------
    # COMMAND: preview
    # -------------------------------------------------

    @weekly_group.command(name="preview", description="Admin-only weekly preview")
    async def weekly_preview(interaction: discord.Interaction):

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Admins only.", ephemeral=True)
            return

        epic = fetch_epic_free_games()
        gog = fetch_gog_deals()
        luna = fetch_amazon_luna()
        humble = fetch_humble_bundle()

        if not _has_any(epic, gog, luna, humble):
            await interaction.response.send_message(
                "No weekly content available.",
                ephemeral=True
            )
            return

        embed = build_weekly_embed(epic, gog, luna, humble)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # -------------------------------------------------
    # COMMAND: post (manual force)
    # -------------------------------------------------

    @weekly_group.command(name="post", description="Force post weekly digest (Admin only)")
    async def weekly_post(interaction: discord.Interaction):

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Admins only.", ephemeral=True)
            return

        if not channel_id:
            await interaction.response.send_message(
                "WEEKLY_DIGEST_CHANNEL_ID not configured.",
                ephemeral=True
            )
            return

        epic = fetch_epic_free_games()
        gog = fetch_gog_deals()
        luna = fetch_amazon_luna()
        humble = fetch_humble_bundle()

        if not _has_any(epic, gog, luna, humble):
            await interaction.response.send_message(
                "No weekly content available.",
                ephemeral=True
            )
            return

        channel = client.get_channel(channel_id)
        if not channel:
            await interaction.response.send_message(
                "Configured channel not found.",
                ephemeral=True
            )
            return

        embed = build_weekly_embed(epic, gog, luna, humble)
        await channel.send(embed=embed)

        now = datetime.datetime.utcnow()
        state["last_post_iso"] = now.isoformat()
        _save(state_path, state)

        await interaction.response.send_message(
            "Weekly digest posted successfully.",
            ephemeral=True
        )

    # -------------------------------------------------
    # BACKGROUND AUTO POST
    # -------------------------------------------------

    @tasks.loop(minutes=30)
    async def friday_poster():

        now = datetime.datetime.utcnow()

        if now.weekday() != 4:
            return

        if now.hour < POST_HOUR_UTC:
            return

        last_iso = state.get("last_post_iso")

        if last_iso:
            last_dt = datetime.datetime.fromisoformat(last_iso)
            if (now - last_dt).days < 7:
                return

        epic = fetch_epic_free_games()
        gog = fetch_gog_deals()
        luna = fetch_amazon_luna()
        humble = fetch_humble_bundle()

        if not _has_any(epic, gog, luna, humble):
            return

        if not channel_id:
            return

        channel = client.get_channel(channel_id)
        if not channel:
            return

        embed = build_weekly_embed(epic, gog, luna, humble)
        await channel.send(embed=embed)

        state["last_post_iso"] = now.isoformat()
        _save(state_path, state)

    @friday_poster.before_loop
    async def before():
        await client.wait_until_ready()

    if not getattr(client, "_weekly_started", False):
        client._weekly_started = True
        friday_poster.start()

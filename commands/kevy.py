from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict

import discord
from discord import app_commands

# ── Config ────────────────────────────────────────────────────────────────────

_COLOR  = 0x89CFF0   # baby blue
_HEART  = "💙"

# Random love messages for /kevy love — keeps it fresh each use
_LOVE_MESSAGES = [
    "We love you, Kevy",
]

# Leaderboard position labels
_MEDALS = {1: "01 —", 2: "02 —", 3: "03 —"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _data_path(data_dir: str) -> str:
    return os.path.join(data_dir, "kevy_stats.json")


def _today_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_stats(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {"total": 0, "today": {}, "leaderboard": {}, "last_date": _today_key()}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"total": 0, "today": {}, "leaderboard": {}, "last_date": _today_key()}


def _save_stats(path: str, stats: Dict[str, Any]) -> None:
    dir_ = os.path.dirname(path)
    if dir_:
        os.makedirs(dir_, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


def _rollover_if_needed(stats: Dict[str, Any]) -> None:
    today = _today_key()
    if stats.get("last_date") != today:
        stats["today"] = {}
        stats["last_date"] = today


def _top_today(today: Dict[str, int]) -> tuple[str, int] | None:
    """Return (user_id, count) of today's top sender, or None."""
    if not today:
        return None
    uid, count = max(today.items(), key=lambda x: x[1])
    return uid, count


# ── Registration ──────────────────────────────────────────────────────────────

async def register(bot: discord.Client, data_dir: str) -> None:
    """Register /kevy commands. Called by main.py loader."""

    existing = bot.tree.get_command("kevy")
    if isinstance(existing, app_commands.Group):
        return
    if existing:
        raise RuntimeError("Command name collision: 'kevy' already exists.")

    stats_path = _data_path(data_dir)

    kevy_group = app_commands.Group(
        name="kevy",
        description="Spread love to Kevy",
    )

    # ── /kevy love ────────────────────────────────────────────────────────────

    @kevy_group.command(name="love", description="Send love to Kevy")
    @app_commands.describe(
        user="Tag someone to send love on their behalf (optional)",
        ephemeral="Only you see the message (default: visible to all)",
    )
    async def kevy_love(
        interaction: discord.Interaction,
        user: discord.User | None = None,
        ephemeral: bool = False,
    ) -> None:
        stats = _load_stats(stats_path)
        _rollover_if_needed(stats)

        uid = str(interaction.user.id)
        stats["total"]                    += 1
        stats["today"][uid]                = stats["today"].get(uid, 0) + 1
        stats["leaderboard"][uid]          = stats["leaderboard"].get(uid, 0) + 1
        _save_stats(stats_path, stats)

        user_today = stats["today"][uid]
        total      = stats["total"]
        message    = _LOVE_MESSAGES[0]

        embed = discord.Embed(color=_COLOR)

        if user:
            embed.description = (
                f"{interaction.user.mention} → {user.mention}\n"
                f"**{message}** {_HEART}"
            )
        else:
            embed.description = f"**{message}** {_HEART}"

        embed.set_footer(
            text=f"Your love count today: {user_today}  ·  Total: {total}"
        )

        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    # ── /kevy count ───────────────────────────────────────────────────────────

    @kevy_group.command(name="count", description="Show total Kevy love count")
    async def kevy_count(interaction: discord.Interaction) -> None:
        stats = _load_stats(stats_path)
        _rollover_if_needed(stats)

        total      = stats.get("total", 0)
        today_sum  = sum(stats.get("today", {}).values())

        embed = discord.Embed(
            title=f"Kevy Love Counter  {_HEART}",
            color=_COLOR,
        )
        embed.add_field(name="Today",    value=str(today_sum), inline=True)
        embed.add_field(name="All Time", value=str(total),     inline=True)

        # Show today's top sender if there is one
        top = _top_today(stats.get("today", {}))
        if top:
            uid, count = top
            embed.add_field(
                name="Today's Top Sender",
                value=f"<@{uid}> — {count}",
                inline=False,
            )

        # Public — everyone can see the love
        await interaction.response.send_message(embed=embed)

    # ── /kevy stats ───────────────────────────────────────────────────────────

    @kevy_group.command(name="stats", description="Your personal Kevy love stats")
    async def kevy_stats(interaction: discord.Interaction) -> None:
        stats = _load_stats(stats_path)
        _rollover_if_needed(stats)

        uid        = str(interaction.user.id)
        today      = stats.get("today", {}).get(uid, 0)
        all_time   = stats.get("leaderboard", {}).get(uid, 0)
        total_all  = stats.get("total", 0)

        # Rank on leaderboard
        board = sorted(
            stats.get("leaderboard", {}).items(),
            key=lambda x: x[1],
            reverse=True,
        )
        rank = next((i + 1 for i, (u, _) in enumerate(board) if u == uid), None)
        rank_str = f"#{rank}" if rank else "—"

        embed = discord.Embed(
            title=f"Your Kevy Stats  {_HEART}",
            color=_COLOR,
        )
        embed.add_field(name="Today",         value=str(today),     inline=True)
        embed.add_field(name="All Time",       value=str(all_time),  inline=True)
        embed.add_field(name="Your Rank",      value=rank_str,       inline=True)
        embed.add_field(name="Community Total",value=str(total_all), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /kevy leaderboard ─────────────────────────────────────────────────────

    @kevy_group.command(name="leaderboard", description="Top Kevy lovers of all time")
    async def kevy_leaderboard(interaction: discord.Interaction) -> None:
        stats = _load_stats(stats_path)
        board = stats.get("leaderboard", {})

        if not board:
            await interaction.response.send_message(
                "No Kevy love has been sent yet.", ephemeral=True
            )
            return

        top10 = sorted(board.items(), key=lambda x: x[1], reverse=True)[:10]

        lines = []
        for i, (uid, count) in enumerate(top10, start=1):
            prefix = _MEDALS.get(i, f"{i:02} —")
            lines.append(f"`{prefix}` <@{uid}> — **{count}**")

        embed = discord.Embed(
            title=f"Kevy Leaderboard  {_HEART}",
            description="\n".join(lines),
            color=_COLOR,
        )
        embed.set_footer(text=f"Total love sent: {stats.get('total', 0)}")

        await interaction.response.send_message(embed=embed)

    bot.tree.add_command(kevy_group)

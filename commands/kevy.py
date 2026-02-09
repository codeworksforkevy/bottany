import discord
from discord import app_commands
import json
import os
from datetime import datetime, timezone

# -------------------------
# Persistence (JSON)
# -------------------------

DATA_PATH = "data/kevy_stats.json"


def _load_stats():
    if not os.path.exists(DATA_PATH):
        return {
            "total": 0,
            "today": {},
            "leaderboard": {},
            "last_date": _today_key(),
        }
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_stats(stats):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


def _today_key():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _rollover_if_needed(stats):
    today = _today_key()
    if stats.get("last_date") != today:
        stats["today"] = {}
        stats["last_date"] = today


# -------------------------
# Registration
# -------------------------

def register_kevy(bot):
    """
    /kevy command group
    - love
    - count
    - stats (today / total)
    - leaderboard
    Persistent, reconnect-safe.
    """

    if getattr(bot, "_kevy_registered", False):
        return

    kevy_group = app_commands.Group(
        name="kevy",
        description="Spread love to Kevy 🎉"
    )

    # -------------------------
    # /kevy love
    # -------------------------
    @kevy_group.command(name="love", description="Send love to Kevy 💙")
    @app_commands.describe(
        user="Mention someone (optional)",
        ephemeral="Only you can see the message"
    )
    async def kevy_love(
        interaction: discord.Interaction,
        user: discord.User | None = None,
        ephemeral: bool = False,
    ):
        stats = _load_stats()
        _rollover_if_needed(stats)

        uid = str(interaction.user.id)

        stats["total"] += 1
        stats["today"][uid] = stats["today"].get(uid, 0) + 1
        stats["leaderboard"][uid] = stats["leaderboard"].get(uid, 0) + 1

        _save_stats(stats)

        heart = "💙"
        text = "We love you Kevy"

        if user:
            text = f"{user.mention} — {text}"

        embed = discord.Embed(
            description=f"**{text}** {heart}",
            color=0x5865F2
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=ephemeral
        )

    # -------------------------
    # /kevy count
    # -------------------------
    @kevy_group.command(name="count", description="Show total /kevy usage.")
    async def kevy_count(interaction: discord.Interaction):
        stats = _load_stats()
        embed = discord.Embed(
            title="Kevy Counter 🎉",
            description=f"**Total uses:** {stats.get('total', 0)} 💙",
            color=0x57F287
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # -------------------------
    # /kevy stats
    # -------------------------
    @kevy_group.command(name="stats", description="Show today's and total Kevy stats.")
    async def kevy_stats(interaction: discord.Interaction):
        stats = _load_stats()
        _rollover_if_needed(stats)

        today_total = sum(stats.get("today", {}).values())
        total = stats.get("total", 0)

        embed = discord.Embed(
            title="Kevy Stats 🎉",
            color=0xFEE75C
        )
        embed.add_field(name="Today", value=str(today_total), inline=True)
        embed.add_field(name="Total", value=str(total), inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # -------------------------
    # /kevy leaderboard
    # -------------------------
    @kevy_group.command(name="leaderboard", description="Top Kevy lovers 💙")
    async def kevy_leaderboard(interaction: discord.Interaction):
        stats = _load_stats()
        board = stats.get("leaderboard", {})

        if not board:
            await interaction.response.send_message(
                "No Kevy activity yet 🎉",
                ephemeral=True
            )
            return

        sorted_users = sorted(
            board.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        lines = []
        for i, (uid, count) in enumerate(sorted_users, start=1):
            lines.append(f"**{i}.** <@{uid}> — {count}")

        embed = discord.Embed(
            title="Kevy Leaderboard 🎉",
            description="\n".join(lines),
            color=0xEB459E
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    bot.tree.add_command(kevy_group)
    bot._kevy_registered = True

from __future__ import annotations

import os
import json
import asyncio
import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo
from collections import deque

import discord
from discord import app_commands

logger = logging.getLogger("bottany.utility")

UTILITY_FILE = "utility_data.json"

_lock = asyncio.Lock()
_message_queue = deque()


# =========================================================
# JSON
# =========================================================

def _path(data_dir: str) -> str:
    return os.path.join(data_dir, UTILITY_FILE)


def _default_data():
    return {
        "version": 4,
        "reminders": [],
        "guild_timezones": {},
        "user_timezones": {}
    }


def _load_json(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return _default_data()
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return _default_data()


def _save_json(path: str, obj: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# =========================================================
# RATE SAFE MESSAGE WORKER
# =========================================================

async def _message_worker(bot: discord.Client):

    await bot.wait_until_ready()

    while not bot.is_closed():

        if _message_queue:
            channel_id, content = _message_queue.popleft()
            ch = bot.get_channel(channel_id)

            if isinstance(ch, discord.TextChannel):
                try:
                    await ch.send(content)
                except Exception as e:
                    logger.warning(f"Send failed: {e}")

            await asyncio.sleep(1.2)
        else:
            await asyncio.sleep(0.5)


# =========================================================
# TIME HELPERS
# =========================================================

TIME_PATTERN = re.compile(r"\b(\d{1,2}):(\d{2})\b")


def _validate_timezone(tz_name: str) -> bool:
    try:
        ZoneInfo(tz_name)
        return True
    except Exception:
        return False


def _get_effective_timezone(data: Dict[str, Any], guild_id: int, user_id: int) -> str:
    return (
        data["user_timezones"].get(str(user_id))
        or data["guild_timezones"].get(str(guild_id))
        or "UTC"
    )


def _convert_times(text: str, tz_name: str) -> str:
    tz = ZoneInfo(tz_name)

    def repl(match):
        hour = int(match.group(1))
        minute = int(match.group(2))

        now_local = datetime.now(tz)
        dt_local = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)

        if dt_local < now_local:
            dt_local += timedelta(days=1)

        dt_utc = dt_local.astimezone(timezone.utc)
        return f"<t:{int(dt_utc.timestamp())}:F>"

    return TIME_PATTERN.sub(repl, text)


# =========================================================
# UTILITY GROUP
# =========================================================

class UtilityGroup(app_commands.Group):

    def __init__(self, bot: discord.Client, data_dir: str):
        super().__init__(name="utility", description="Utility commands")
        self.bot = bot
        self.data_dir = data_dir

    # -----------------------------------------------------
    # TIMEZONE (SERVER)
    # -----------------------------------------------------

    @app_commands.command(name="timezone", description="Set server timezone (IANA)")
    async def timezone(self, interaction: discord.Interaction, tz: str):

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "Admin permission required.",
                ephemeral=True
            )
            return

        if not _validate_timezone(tz):
            await interaction.response.send_message(
                "Invalid IANA timezone. Example: Europe/Brussels",
                ephemeral=True
            )
            return

        async with _lock:
            path = _path(self.data_dir)
            data = _load_json(path)
            data["guild_timezones"][str(interaction.guild_id)] = tz
            _save_json(path, data)

        await interaction.response.send_message(
            f"Server timezone set to `{tz}`."
        )

    # -----------------------------------------------------
    # MY TIMEZONE
    # -----------------------------------------------------

    @app_commands.command(name="mytimezone", description="Set your personal timezone")
    async def mytimezone(self, interaction: discord.Interaction, tz: str):

        if not _validate_timezone(tz):
            await interaction.response.send_message(
                "Invalid IANA timezone.",
                ephemeral=True
            )
            return

        async with _lock:
            path = _path(self.data_dir)
            data = _load_json(path)
            data["user_timezones"][str(interaction.user.id)] = tz
            _save_json(path, data)

        await interaction.response.send_message(
            f"Your timezone set to `{tz}`.",
            ephemeral=True
        )

    # -----------------------------------------------------
    # SCHEDULE (HH:MM → DISCORD TIMESTAMP)
    # -----------------------------------------------------

    @app_commands.command(name="schedule", description="Convert HH:MM to Discord timestamps")
    async def schedule(self, interaction: discord.Interaction, text: str):

        path = _path(self.data_dir)
        data = _load_json(path)

        tz_name = _get_effective_timezone(
            data,
            interaction.guild_id or 0,
            interaction.user.id
        )

        converted = _convert_times(text, tz_name)

        await interaction.response.send_message(converted)

    # -----------------------------------------------------
    # REMIND
    # -----------------------------------------------------

    @app_commands.command(name="remind", description="Set reminder in minutes")
    async def remind(
        self,
        interaction: discord.Interaction,
        minutes: int,
        text: str,
        repeat: Optional[str] = None
    ):

        if minutes < 1 or minutes > 10080:
            await interaction.response.send_message(
                "Minutes must be 1–10080.",
                ephemeral=True
            )
            return

        due = _utc_now() + timedelta(minutes=minutes)

        async with _lock:
            path = _path(self.data_dir)
            data = _load_json(path)

            reminder_id = len(data["reminders"]) + 1

            data["reminders"].append({
                "id": reminder_id,
                "guild_id": interaction.guild_id,
                "channel_id": interaction.channel_id,
                "user_id": interaction.user.id,
                "due": due.isoformat(),
                "text": text[:500],
                "repeat": repeat if repeat in ("daily", "weekly") else None
            })

            _save_json(path, data)

        await interaction.response.send_message(
            f"Reminder #{reminder_id} set.",
            ephemeral=True
        )

    # -----------------------------------------------------
    # LIST REMINDERS
    # -----------------------------------------------------

    @app_commands.command(name="reminders", description="List your reminders")
    async def reminders(self, interaction: discord.Interaction):

        path = _path(self.data_dir)
        data = _load_json(path)

        user_id = interaction.user.id
        items = [r for r in data["reminders"] if r["user_id"] == user_id]

        if not items:
            await interaction.response.send_message(
                "No active reminders.",
                ephemeral=True
            )
            return

        lines = []
        for r in items:
            ts = int(datetime.fromisoformat(r["due"]).timestamp())
            lines.append(f"#{r['id']} — <t:{ts}:F> — {r['text']}")

        await interaction.response.send_message(
            "\n".join(lines[:20]),
            ephemeral=True
        )

    # -----------------------------------------------------
    # CANCEL
    # -----------------------------------------------------

    @app_commands.command(name="cancel", description="Cancel reminder by number")
    async def cancel(self, interaction: discord.Interaction, number: int):

        async with _lock:
            path = _path(self.data_dir)
            data = _load_json(path)

            before = len(data["reminders"])
            data["reminders"] = [
                r for r in data["reminders"]
                if not (r["id"] == number and r["user_id"] == interaction.user.id)
            ]
            after = len(data["reminders"])

            _save_json(path, data)

        if before == after:
            await interaction.response.send_message(
                "Reminder not found.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"Reminder #{number} cancelled.",
                ephemeral=True
            )


# =========================================================
# REGISTER
# =========================================================

async def register(bot: discord.Client, data_dir: str):

    group = bot.tree.get_command("utility")

    if not isinstance(group, app_commands.Group):
        group = UtilityGroup(bot, data_dir)
        bot.tree.add_command(group)

    if getattr(bot, "_utility_started", False):
        return

    bot._utility_started = True

    bot._utility_worker = asyncio.create_task(_message_worker(bot))

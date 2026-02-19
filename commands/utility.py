from __future__ import annotations

import os
import json
import asyncio
import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo, available_timezones
from collections import deque

import discord
from discord import app_commands

logger = logging.getLogger("bottany.utility")

UTILITY_FILE = "utility_data.json"

_lock = asyncio.Lock()
_message_queue = deque()

MAX_REMINDERS_PER_USER = 20

TIME_PATTERN = re.compile(r"\b(\d{1,2}):(\d{2})\b")
IN_PATTERN = re.compile(r"in\s+(\d+)\s+(minutes?|hours?)", re.I)
TOMORROW_PATTERN = re.compile(r"tomorrow\s+(\d{1,2}):(\d{2})", re.I)
NEXT_WEEKDAY_PATTERN = re.compile(r"next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+(\d{1,2}):(\d{2})", re.I)

WEEKDAY_MAP = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


# =========================================================
# JSON
# =========================================================

def _path(data_dir: str) -> str:
    return os.path.join(data_dir, UTILITY_FILE)


def _default_data():
    return {
        "version": 5,
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
# RATE SAFE WORKER
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

def _validate_timezone(tz_name: str) -> bool:
    try:
        ZoneInfo(tz_name)
        return True
    except Exception:
        return False


def _get_effective_timezone(data, guild_id, user_id):
    return (
        data["user_timezones"].get(str(user_id))
        or data["guild_timezones"].get(str(guild_id))
        or "UTC"
    )


def _parse_natural_time(text: str, tz_name: str) -> Optional[datetime]:
    tz = ZoneInfo(tz_name)
    now_local = datetime.now(tz)

    m = IN_PATTERN.search(text)
    if m:
        val = int(m.group(1))
        unit = m.group(2).lower()
        if "hour" in unit:
            return _utc_now() + timedelta(hours=val)
        return _utc_now() + timedelta(minutes=val)

    m = TOMORROW_PATTERN.search(text)
    if m:
        h, mnt = int(m.group(1)), int(m.group(2))
        dt = now_local + timedelta(days=1)
        dt = dt.replace(hour=h, minute=mnt, second=0, microsecond=0)
        return dt.astimezone(timezone.utc)

    m = NEXT_WEEKDAY_PATTERN.search(text)
    if m:
        wd = WEEKDAY_MAP[m.group(1).lower()]
        h, mnt = int(m.group(2)), int(m.group(3))
        days_ahead = (wd - now_local.weekday() + 7) % 7
        if days_ahead == 0:
            days_ahead = 7
        dt = now_local + timedelta(days=days_ahead)
        dt = dt.replace(hour=h, minute=mnt, second=0, microsecond=0)
        return dt.astimezone(timezone.utc)

    return None


# =========================================================
# AUTOCOMPLETE
# =========================================================

async def timezone_autocomplete(interaction, current):
    matches = [
        tz for tz in available_timezones()
        if current.lower() in tz.lower()
    ]
    return [
        app_commands.Choice(name=tz, value=tz)
        for tz in matches[:25]
    ]


async def reminder_id_autocomplete(interaction, current):
    bot = interaction.client
    group: UtilityGroup = bot.tree.get_command("utility")
    path = _path(group.data_dir)
    data = _load_json(path)
    user_id = interaction.user.id

    matches = [
        str(r["id"])
        for r in data["reminders"]
        if r["user_id"] == user_id
        and current in str(r["id"])
    ]

    return [
        app_commands.Choice(name=m, value=int(m))
        for m in matches[:25]
    ]


# =========================================================
# UTILITY GROUP
# =========================================================

class UtilityGroup(app_commands.Group):

    def __init__(self, bot: discord.Client, data_dir: str):
        super().__init__(name="utility", description="Utility commands")
        self.bot = bot
        self.data_dir = data_dir

    # ---------------- TIMEZONE ----------------

    @app_commands.command(name="timezone")
    @app_commands.autocomplete(tz=timezone_autocomplete)
    async def timezone(self, interaction: discord.Interaction, tz: str):

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Admin only.", ephemeral=True)
            return

        if not _validate_timezone(tz):
            await interaction.response.send_message("Invalid timezone.", ephemeral=True)
            return

        async with _lock:
            path = _path(self.data_dir)
            data = _load_json(path)
            data["guild_timezones"][str(interaction.guild_id)] = tz
            _save_json(path, data)

        await interaction.response.send_message(f"Server timezone set to `{tz}`.")

    # ---------------- MY TIMEZONE ----------------

    @app_commands.command(name="mytimezone")
    @app_commands.autocomplete(tz=timezone_autocomplete)
    async def mytimezone(self, interaction: discord.Interaction, tz: str):

        if not _validate_timezone(tz):
            await interaction.response.send_message("Invalid timezone.", ephemeral=True)
            return

        async with _lock:
            path = _path(self.data_dir)
            data = _load_json(path)
            data["user_timezones"][str(interaction.user.id)] = tz
            _save_json(path, data)

        await interaction.response.send_message(f"Your timezone set to `{tz}`.", ephemeral=True)

    # ---------------- REMIND ----------------

    @app_commands.command(name="remind")
    async def remind(self, interaction: discord.Interaction, text: str):

        path = _path(self.data_dir)
        async with _lock:
            data = _load_json(path)

            user_reminders = [r for r in data["reminders"] if r["user_id"] == interaction.user.id]

            if len(user_reminders) >= MAX_REMINDERS_PER_USER:
                await interaction.response.send_message("Reminder limit reached.", ephemeral=True)
                return

            tz_name = _get_effective_timezone(data, interaction.guild_id, interaction.user.id)

            due = _parse_natural_time(text, tz_name)
            if not due:
                await interaction.response.send_message(
                    "Could not parse time. Example: `in 30 minutes`, `tomorrow 18:00`",
                    ephemeral=True
                )
                return

            for r in user_reminders:
                existing_due = datetime.fromisoformat(r["due"])
                if abs((existing_due - due).total_seconds()) < 60:
                    await interaction.response.send_message(
                        "Conflict: another reminder exists near this time.",
                        ephemeral=True
                    )
                    return

            reminder_id = max([r["id"] for r in data["reminders"]] or [0]) + 1

            data["reminders"].append({
                "id": reminder_id,
                "guild_id": interaction.guild_id,
                "channel_id": interaction.channel_id,
                "user_id": interaction.user.id,
                "due": due.isoformat(),
                "text": text[:500]
            })

            _save_json(path, data)

        await interaction.response.send_message(f"Reminder #{reminder_id} set.", ephemeral=True)

    # ---------------- EDIT ----------------

    @app_commands.command(name="edit")
    @app_commands.autocomplete(number=reminder_id_autocomplete)
    async def edit(self, interaction: discord.Interaction, number: int, text: str):

        async with _lock:
            path = _path(self.data_dir)
            data = _load_json(path)

            for r in data["reminders"]:
                if r["id"] == number and r["user_id"] == interaction.user.id:
                    tz_name = _get_effective_timezone(data, interaction.guild_id, interaction.user.id)
                    new_due = _parse_natural_time(text, tz_name)
                    if not new_due:
                        await interaction.response.send_message("Invalid time format.", ephemeral=True)
                        return
                    r["due"] = new_due.isoformat()
                    r["text"] = text[:500]
                    _save_json(path, data)
                    await interaction.response.send_message(f"Reminder #{number} updated.", ephemeral=True)
                    return

        await interaction.response.send_message("Reminder not found.", ephemeral=True)


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

import os
import json
import asyncio
import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from zoneinfo import ZoneInfo
from collections import deque

import discord
from discord import app_commands

logger = logging.getLogger("bottany.utility")

UTILITY_FILE = "utility_data.json"

_lock = asyncio.Lock()
_message_queue = deque()


# =========================================================
# JSON HELPERS
# =========================================================

def _path(data_dir: str) -> str:
    return os.path.join(data_dir, UTILITY_FILE)


def _load_json(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {
            "version": 3,
            "reminders": [],
            "guild_timezones": {},
            "user_timezones": {}
        }
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "version": 3,
            "reminders": [],
            "guild_timezones": {},
            "user_timezones": {}
        }


def _save_json(path: str, obj: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# =========================================================
# MESSAGE WORKER (RATE SAFE)
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

            await asyncio.sleep(1.2)  # rate-limit safe
        else:
            await asyncio.sleep(0.5)


# =========================================================
# UTILITY GROUP
# =========================================================

class UtilityGroup(app_commands.Group):

    def __init__(self, bot: discord.Client, data_dir: str):
        super().__init__(name="utility", description="Utility commands")
        self.bot = bot
        self.data_dir = data_dir

    # -----------------------------------------------------
    # PING
    # -----------------------------------------------------
    @app_commands.command(name="ping", description="Check bot latency")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"Pong. Latency: {int(self.bot.latency * 1000)}ms"
        )

    # -----------------------------------------------------
    # SERVER INFO
    # -----------------------------------------------------
    @app_commands.command(name="serverinfo", description="Show server info")
    async def serverinfo(self, interaction: discord.Interaction):

        g = interaction.guild
        if not g:
            await interaction.response.send_message(
                "This command must be used in a server.",
                ephemeral=True
            )
            return

        embed = discord.Embed(title="Server Info")
        embed.add_field(name="Name", value=g.name)
        embed.add_field(name="Members", value=str(g.member_count or 0))
        embed.add_field(
            name="Created",
            value=f"<t:{int(g.created_at.timestamp())}:F>"
        )

        await interaction.response.send_message(embed=embed)

    # -----------------------------------------------------
    # POLL
    # -----------------------------------------------------
    @app_commands.command(name="poll", description="Create poll (2-5 options)")
    async def poll(
        self,
        interaction: discord.Interaction,
        question: str,
        option1: str,
        option2: str,
        option3: str = "",
        option4: str = "",
        option5: str = ""
    ):

        opts = [o for o in [option1, option2, option3, option4, option5] if o.strip()]
        if len(opts) < 2:
            await interaction.response.send_message(
                "Provide at least 2 options.",
                ephemeral=True
            )
            return

        emoji = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
        desc = "\n".join(f"{emoji[i]} {opts[i]}" for i in range(len(opts)))

        embed = discord.Embed(
            title=question[:256],
            description=desc[:4096]
        )

        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()

        for i in range(len(opts)):
            await msg.add_reaction(emoji[i])

    # -----------------------------------------------------
    # REMIND (Recurring supported)
    # -----------------------------------------------------
    @app_commands.command(name="remind", description="Set reminder (minutes)")
    async def remind(
        self,
        interaction: discord.Interaction,
        minutes: int,
        text: str,
        repeat: str = "none"
    ):

        if minutes < 1 or minutes > 10080:
            await interaction.response.send_message(
                "Minutes must be between 1 and 10080.",
                ephemeral=True
            )
            return

        if repeat not in ("none", "daily", "weekly"):
            await interaction.response.send_message(
                "Repeat must be: none, daily, weekly.",
                ephemeral=True
            )
            return

        due = _utc_now() + timedelta(minutes=minutes)

        async with _lock:
            data = _load_json(_path(self.data_dir))
            reminders = data["reminders"]
            new_id = max([r["id"] for r in reminders], default=0) + 1

            reminders.append({
                "id": new_id,
                "guild_id": int(interaction.guild_id or 0),
                "channel_id": int(interaction.channel_id),
                "user_id": int(interaction.user.id),
                "due": due.isoformat(),
                "text": text[:500],
                "repeat": None if repeat == "none" else repeat
            })

            _save_json(_path(self.data_dir), data)

        await interaction.response.send_message(
            f"Reminder #{new_id} set.",
            ephemeral=True
        )

    # -----------------------------------------------------
    # REMINDERS LIST
    # -----------------------------------------------------
    @app_commands.command(name="reminders", description="List active reminders")
    async def reminders(self, interaction: discord.Interaction):

        async with _lock:
            data = _load_json(_path(self.data_dir))
            items = [
                r for r in data["reminders"]
                if r["user_id"] == interaction.user.id
            ]

        if not items:
            await interaction.response.send_message(
                "No active reminders.",
                ephemeral=True
            )
            return

        lines = []
        for r in items:
            due = datetime.fromisoformat(r["due"])
            unix = int(due.timestamp())
            rep = f" ({r['repeat']})" if r.get("repeat") else ""
            lines.append(f"#{r['id']} — <t:{unix}:F>{rep}")

        await interaction.response.send_message(
            "\n".join(lines),
            ephemeral=True
        )

    # -----------------------------------------------------
    # CANCEL
    # -----------------------------------------------------
    @app_commands.command(name="cancel", description="Cancel reminder by ID")
    async def cancel(self, interaction: discord.Interaction, reminder_id: int):

        async with _lock:
            data = _load_json(_path(self.data_dir))
            before = len(data["reminders"])
            data["reminders"] = [
                r for r in data["reminders"]
                if r["id"] != reminder_id
            ]
            _save_json(_path(self.data_dir), data)

        if before == len(data["reminders"]):
            await interaction.response.send_message(
                "Reminder not found.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"Reminder #{reminder_id} cancelled.",
                ephemeral=True
            )

    # -----------------------------------------------------
    # GUILD TIMEZONE
    # -----------------------------------------------------
    @app_commands.command(name="timezone", description="Set server timezone")
    async def timezone_cmd(self, interaction: discord.Interaction, timezone_name: str):

        try:
            ZoneInfo(timezone_name)
        except Exception:
            await interaction.response.send_message(
                "Invalid timezone. Example: Europe/Brussels",
                ephemeral=True
            )
            return

        async with _lock:
            data = _load_json(_path(self.data_dir))
            data["guild_timezones"][str(interaction.guild_id)] = timezone_name
            _save_json(_path(self.data_dir), data)

        await interaction.response.send_message(
            f"Server timezone set to {timezone_name}"
        )

    # -----------------------------------------------------
    # USER TIMEZONE
    # -----------------------------------------------------
    @app_commands.command(name="mytimezone", description="Set your timezone")
    async def mytimezone(self, interaction: discord.Interaction, timezone_name: str):

        try:
            ZoneInfo(timezone_name)
        except Exception:
            await interaction.response.send_message(
                "Invalid timezone.",
                ephemeral=True
            )
            return

        async with _lock:
            data = _load_json(_path(self.data_dir))
            data["user_timezones"][str(interaction.user.id)] = timezone_name
            _save_json(_path(self.data_dir), data)

        await interaction.response.send_message(
            f"Your timezone set to {timezone_name}",
            ephemeral=True
        )

    # -----------------------------------------------------
    # SCHEDULE (Multi-time)
    # -----------------------------------------------------
    @app_commands.command(name="schedule", description="Convert HH:MM to timestamps")
    async def schedule(self, interaction: discord.Interaction, text: str):

        pattern = r"\b([01]?\d|2[0-3]):([0-5]\d)\b"
        matches = list(re.finditer(pattern, text))

        if not matches:
            await interaction.response.send_message(
                "No HH:MM time found.",
                ephemeral=True
            )
            return

        async with _lock:
            data = _load_json(_path(self.data_dir))
            tz_name = (
                data["user_timezones"].get(str(interaction.user.id))
                or data["guild_timezones"].get(str(interaction.guild_id))
                or "UTC"
            )

        tz = ZoneInfo(tz_name)
        now = datetime.now(tz)

        new_text = text
        timestamps = []

        for m in matches:
            hour = int(m.group(1))
            minute = int(m.group(2))

            dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if dt < now:
                dt += timedelta(days=1)

            unix = int(dt.timestamp())
            timestamps.append(unix)

            new_text = new_text.replace(
                m.group(0),
                f"<t:{unix}:F>"
            )

        relative = "\n".join(f"<t:{u}:R>" for u in timestamps)

        await interaction.response.send_message(
            f"{new_text}\n\n{relative}"
        )


# =========================================================
# BACKGROUND REMINDER LOOP
# =========================================================

async def register_utility(bot: discord.Client, data_dir: str):

    group = UtilityGroup(bot, data_dir)
    bot.tree.add_command(group)

    if hasattr(bot, "_utility_task"):
        return

    async def reminder_loop():

        await bot.wait_until_ready()
        path = _path(data_dir)

        while not bot.is_closed():

            async with _lock:
                data = _load_json(path)
                reminders: List[Dict] = data["reminders"]

                if not reminders:
                    await asyncio.sleep(30)
                    continue

                reminders.sort(key=lambda r: r["due"])
                next_due = datetime.fromisoformat(reminders[0]["due"])
                now = _utc_now()

                if next_due > now:
                    await asyncio.sleep(
                        min((next_due - now).total_seconds(), 60)
                    )
                    continue

                keep = []

                for r in reminders:
                    due = datetime.fromisoformat(r["due"])

                    if due <= now:
                        _message_queue.append(
                            (
                                r["channel_id"],
                                f"<@{r['user_id']}> ⏰ Reminder: {r['text']}"
                            )
                        )

                        if r.get("repeat") == "daily":
                            r["due"] = (due + timedelta(days=1)).isoformat()
                            keep.append(r)
                        elif r.get("repeat") == "weekly":
                            r["due"] = (due + timedelta(weeks=1)).isoformat()
                            keep.append(r)

                    else:
                        keep.append(r)

                data["reminders"] = keep
                _save_json(path, data)

            await asyncio.sleep(5)

    bot._utility_task = asyncio.create_task(reminder_loop())
    bot._utility_worker = asyncio.create_task(_message_worker(bot))

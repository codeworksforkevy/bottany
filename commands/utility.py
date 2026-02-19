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

            await asyncio.sleep(1.2)
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
    # HELP (NOW PUBLIC)
    # -----------------------------------------------------
    @app_commands.command(
        name="help",
        description="Show help for utility commands"
    )
    async def help(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title="📦 Utility Commands",
            description=(
                "### 🕒 Time Conversion\n"
                "**/utility schedule <text>**\n"
                "Convert HH:MM times to Discord timestamps.\n\n"

                "### 🧑‍💻 Timezone\n"
                "**/utility timezone <IANA>** — Set server timezone\n"
                "**/utility mytimezone <IANA>** — Set personal timezone\n\n"

                "### 📝 Reminders\n"
                "**/utility remind <minutes> <text> [repeat]**\n"
                "**/utility reminders** — List reminders\n"
                "**/utility cancel <id>** — Cancel reminder\n\n"

                "### 📊 Server Tools\n"
                "**/utility poll** — Create poll\n"
                "**/utility serverinfo** — Show server info\n"
                "**/utility ping** — Bot latency"
            ),
            color=0x5865F2
        )

        embed.set_footer(
            text="Times automatically adjust to each user's local timezone."
        )

        # 🔥 PUBLIC (ephemeral kaldırıldı)
        await interaction.response.send_message(embed=embed)

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


# =========================================================
# REGISTER
# =========================================================

async def register(bot: discord.Client, data_dir: str):

    existing = bot.tree.get_command("utility")

    if isinstance(existing, app_commands.Group):
        group = existing
    elif existing:
        raise RuntimeError(
            "Command name collision: 'utility' already exists and is not a Group."
        )
    else:
        group = UtilityGroup(bot, data_dir)
        bot.tree.add_command(group)

    if getattr(bot, "_utility_registered", False):
        return

    bot._utility_registered = True

    # Background worker
    if not hasattr(bot, "_utility_worker"):
        bot._utility_worker = asyncio.create_task(_message_worker(bot))

    # Reminder loop
    if not hasattr(bot, "_utility_task"):

        async def reminder_loop():

            await bot.wait_until_ready()
            path = _path(data_dir)

            while not bot.is_closed():

                async with _lock:
                    data = _load_json(path)
                    reminders: List[Dict] = data["reminders"]

                    now = _utc_now()
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

                await asyncio.sleep(10)

        bot._utility_task = asyncio.create_task(reminder_loop())

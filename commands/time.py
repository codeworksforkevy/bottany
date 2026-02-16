from datetime import datetime
from zoneinfo import ZoneInfo
import json
from pathlib import Path
import discord
from discord import app_commands


async def register(bot, data_dir):

    tz_path = Path(data_dir) / "city_timezones.json"

    if tz_path.exists():
        with open(tz_path, "r", encoding="utf-8") as f:
            CITY_TZ = json.load(f)
    else:
        CITY_TZ = {
            "utc": "UTC",
            "ankara": "Europe/Istanbul",
            "istanbul": "Europe/Istanbul",
            "rome": "Europe/Rome",
            "italy": "Europe/Rome",
            "brussels": "Europe/Brussels",
            "belgium": "Europe/Brussels",
        }

    @bot.tree.command(
        name="time",
        description="Show local time, UTC and offset for a city or country"
    )
    @app_commands.describe(city="City or country name")
    async def time_command(interaction: discord.Interaction, city: str):

        key = city.strip().lower()

        if key not in CITY_TZ:
            await interaction.response.send_message(
                f"Unknown location: {city}",
                ephemeral=False
            )
            return

        tz = ZoneInfo(CITY_TZ[key])
        now = datetime.now(tz)
        offset = now.utcoffset()
        hours = int(offset.total_seconds() // 3600) if offset else 0
        sign = "+" if hours >= 0 else "-"

        msg = (
            f"🕒 **{city.title()}**\n"
            f"Local time: **{now.strftime('%H:%M')}**\n"
            f"UTC offset: **UTC{sign}{abs(hours)}**"
        )

        await interaction.response.send_message(msg, ephemeral=False)

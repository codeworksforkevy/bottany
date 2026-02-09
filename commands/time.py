from datetime import datetime
from zoneinfo import ZoneInfo
import json
from pathlib import Path
import discord
from discord import app_commands

DATA_DIR = Path("data")
CITY_TZ_FILE = DATA_DIR / "city_timezones.json"

with open(CITY_TZ_FILE, "r", encoding="utf-8") as f:
    CITY_TIMEZONES = json.load(f)

def register_time_command(bot: discord.Client):
    @bot.tree.command(
        name="time",
        description="Show the current local time in a given city or country"
    )
    @app_commands.describe(city="City or country name (e.g. Tokyo, Belgium, Milano)")
    async def time(interaction: discord.Interaction, city: str):
        key = city.strip().lower()

        if key not in CITY_TIMEZONES:
            await interaction.response.send_message(
                f"❌ I don't have timezone data for **{city}** yet.",
                ephemeral=True
            )
            return

        tz = CITY_TIMEZONES[key]
        now = datetime.now(ZoneInfo(tz))

        formatted = now.strftime("%H:%M (%d %B %Y)")
        await interaction.response.send_message(
            f"🕒 **{city.title()}** local time: **{formatted}**",
            ephemeral=True
        )
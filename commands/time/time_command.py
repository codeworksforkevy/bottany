import os
import discord
from discord import app_commands
import logging
import re
from difflib import get_close_matches
from datetime import datetime
from zoneinfo import ZoneInfo
import aiohttp

logger = logging.getLogger("bottany.time")

CORE_CITIES = {
"stockholm": "Europe/Stockholm",
"gothenburg": "Europe/Stockholm",
"oslo": "Europe/Oslo",
"bergen": "Europe/Oslo",
"copenhagen": "Europe/Copenhagen",
"helsinki": "Europe/Helsinki",
"berlin": "Europe/Berlin",
"paris": "Europe/Paris",
"london": "Europe/London",
"rome": "Europe/Rome",
"madrid": "Europe/Madrid",
"amsterdam": "Europe/Amsterdam",
"brussels": "Europe/Brussels",
"vienna": "Europe/Vienna",
"warsaw": "Europe/Warsaw",
"athens": "Europe/Athens",
"ankara": "Europe/Istanbul",
"istanbul": "Europe/Istanbul",
"new york": "America/New_York",
"los angeles": "America/Los_Angeles",
"chicago": "America/Chicago",
"houston": "America/Chicago",
"miami": "America/New_York",
"seattle": "America/Los_Angeles",
"toronto": "America/Toronto",
"vancouver": "America/Vancouver",
"mexico city": "America/Mexico_City",
"bogota": "America/Bogota",
"sao paulo": "America/Sao_Paulo",
"tokyo": "Asia/Tokyo",
"osaka": "Asia/Tokyo",
"seoul": "Asia/Seoul",
"beijing": "Asia/Shanghai",
"shanghai": "Asia/Shanghai",
"singapore": "Asia/Singapore",
"kuala lumpur": "Asia/Kuala_Lumpur",
"new delhi": "Asia/Kolkata",
"mumbai": "Asia/Kolkata",
"sydney": "Australia/Sydney",
"melbourne": "Australia/Sydney",
"cairo": "Africa/Cairo",
"nairobi": "Africa/Nairobi",
"lagos": "Africa/Lagos",
"dubai": "Asia/Dubai",
"riyadh": "Asia/Riyadh",
"tel aviv": "Asia/Jerusalem",
}

def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def get_day_icon(hour: int) -> str:
    if 6 <= hour < 17:
        return "☀️"
    elif 17 <= hour < 20:
        return "🌇"
    elif 20 <= hour < 23:
        return "🌆"
    else:
        return "🌌"

def get_flag_from_timezone(tz: str) -> str:
    region = tz.split("/")[0]
    region_flag = {
        "Europe": "🇪🇺",
        "Asia": "🌏",
        "America": "🌎",
        "Australia": "🇦🇺",
        "Africa": "🌍",
    }
    return region_flag.get(region, "")

async def fetch_time_from_api(timezone: str):
    try:
        timeout = aiohttp.ClientTimeout(total=2.5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"http://worldtimeapi.org/api/timezone/{timezone}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return datetime.fromisoformat(data["datetime"])
    except Exception:
        pass
    return None

def fallback_zoneinfo(timezone: str):
    try:
        return datetime.now(ZoneInfo(timezone))
    except Exception:
        return None

async def register(bot, data_dir):

    guild = discord.Object(id=1446560723122520207)

    @bot.tree.command(
        name="time",
        description="World clock (multi-city)",
        guild=guild
    )
    @app_commands.describe(
        locations="Example: Stockholm, Tokyo, New York"
    )
    async def time_command(interaction: discord.Interaction, locations: str):

        await interaction.response.defer()

        inputs = [i.strip() for i in locations.split(",") if i.strip()]

        if len(inputs) > 5:
            await interaction.followup.send("Maximum 5 locations allowed.")
            return

        lines = []
        corrections = []

        for raw in inputs:

            normalized = normalize(raw)
            timezone = CORE_CITIES.get(normalized)

            if not timezone:
                matches = get_close_matches(normalized, CORE_CITIES.keys(), n=1, cutoff=0.7)
                if matches:
                    timezone = CORE_CITIES[matches[0]]
                    corrections.append(f"{raw} → {matches[0].title()}")

            if not timezone:
                lines.append(f"❌  {raw}")
                continue

            dt = await fetch_time_from_api(timezone)
            if not dt:
                dt = fallback_zoneinfo(timezone)

            if not dt:
                lines.append(f"❌  {raw}")
                continue

            hour = dt.hour
            minute = dt.minute

            city_display = timezone.split("/")[-1].replace("_", " ")
            icon = get_day_icon(hour)
            flag = get_flag_from_timezone(timezone)

            lines.append(f"{flag}  {icon}  {city_display:<12}  {hour:02}:{minute:02}")

        if not lines:
            await interaction.followup.send("No valid locations.")
            return

        embed = discord.Embed(
            title="Time Dashboard",
            description="────────────────────────\n\n" + "\n".join(lines),
            color=0x1e1f22
        )

        if corrections:
            embed.description += "\n\nauto-corrected: " + ", ".join(corrections)

        await interaction.followup.send(embed=embed)

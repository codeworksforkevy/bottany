import discord
from discord import app_commands
import asyncio
import logging
import re
from difflib import get_close_matches
from datetime import datetime
from zoneinfo import ZoneInfo
import aiohttp

logger = logging.getLogger("bottany.time")

# =====================================================
# 🌍 CORE GLOBAL CITIES (115+)
# =====================================================

CORE_CITIES = {
# EUROPE
"stockholm": "Europe/Stockholm",
"gothenburg": "Europe/Stockholm",
"oslo": "Europe/Oslo",
"bergen": "Europe/Oslo",
"copenhagen": "Europe/Copenhagen",
"aarhus": "Europe/Copenhagen",
"helsinki": "Europe/Helsinki",
"tallinn": "Europe/Tallinn",
"riga": "Europe/Riga",
"vilnius": "Europe/Vilnius",
"warsaw": "Europe/Warsaw",
"krakow": "Europe/Warsaw",
"berlin": "Europe/Berlin",
"munich": "Europe/Berlin",
"frankfurt": "Europe/Berlin",
"hamburg": "Europe/Berlin",
"amsterdam": "Europe/Amsterdam",
"rotterdam": "Europe/Amsterdam",
"brussels": "Europe/Brussels",
"paris": "Europe/Paris",
"lyon": "Europe/Paris",
"marseille": "Europe/Paris",
"madrid": "Europe/Madrid",
"barcelona": "Europe/Madrid",
"lisbon": "Europe/Lisbon",
"rome": "Europe/Rome",
"milan": "Europe/Rome",
"naples": "Europe/Rome",
"vienna": "Europe/Vienna",
"prague": "Europe/Prague",
"budapest": "Europe/Budapest",
"athens": "Europe/Athens",
"bucharest": "Europe/Bucharest",
"sofia": "Europe/Sofia",
"zagreb": "Europe/Zagreb",
"ljubljana": "Europe/Ljubljana",
"bratislava": "Europe/Bratislava",
"luxembourg": "Europe/Luxembourg",
"dublin": "Europe/Dublin",
"london": "Europe/London",
"manchester": "Europe/London",
"zurich": "Europe/Zurich",
"geneva": "Europe/Zurich",
"reykjavik": "Atlantic/Reykjavik",
"ankara": "Europe/Istanbul",
"istanbul": "Europe/Istanbul",

# USA
"washington": "America/New_York",
"new york": "America/New_York",
"los angeles": "America/Los_Angeles",
"san francisco": "America/Los_Angeles",
"san diego": "America/Los_Angeles",
"chicago": "America/Chicago",
"houston": "America/Chicago",
"dallas": "America/Chicago",
"miami": "America/New_York",
"boston": "America/New_York",
"seattle": "America/Los_Angeles",
"atlanta": "America/New_York",
"denver": "America/Denver",
"phoenix": "America/Phoenix",
"las vegas": "America/Los_Angeles",

# CANADA
"ottawa": "America/Toronto",
"toronto": "America/Toronto",
"montreal": "America/Toronto",
"vancouver": "America/Vancouver",
"calgary": "America/Edmonton",

# LATAM
"mexico city": "America/Mexico_City",
"bogota": "America/Bogota",
"lima": "America/Lima",
"santiago": "America/Santiago",
"buenos aires": "America/Argentina/Buenos_Aires",
"sao paulo": "America/Sao_Paulo",
"rio de janeiro": "America/Sao_Paulo",
"brasilia": "America/Sao_Paulo",

# ASIA
"tokyo": "Asia/Tokyo",
"osaka": "Asia/Tokyo",
"seoul": "Asia/Seoul",
"busan": "Asia/Seoul",
"beijing": "Asia/Shanghai",
"shanghai": "Asia/Shanghai",
"shenzhen": "Asia/Shanghai",
"hong kong": "Asia/Hong_Kong",
"taipei": "Asia/Taipei",

# INDIA
"new delhi": "Asia/Kolkata",
"mumbai": "Asia/Kolkata",
"bangalore": "Asia/Kolkata",
"hyderabad": "Asia/Kolkata",
"chennai": "Asia/Kolkata",
"kolkata": "Asia/Kolkata",

# SOUTHEAST ASIA
"kuala lumpur": "Asia/Kuala_Lumpur",
"penang": "Asia/Kuala_Lumpur",
"bangkok": "Asia/Bangkok",
"singapore": "Asia/Singapore",
"jakarta": "Asia/Jakarta",
"manila": "Asia/Manila",
"ho chi minh": "Asia/Ho_Chi_Minh",

# OCEANIA
"sydney": "Australia/Sydney",
"melbourne": "Australia/Sydney",
"brisbane": "Australia/Brisbane",
"perth": "Australia/Perth",
"auckland": "Pacific/Auckland",
"wellington": "Pacific/Auckland",

# AFRICA
"cairo": "Africa/Cairo",
"nairobi": "Africa/Nairobi",
"lagos": "Africa/Lagos",
"johannesburg": "Africa/Johannesburg",
"cape town": "Africa/Johannesburg",
"addis ababa": "Africa/Addis_Ababa",
"casablanca": "Africa/Casablanca",
"rabat": "Africa/Casablanca",

# MIDDLE EAST
"dubai": "Asia/Dubai",
"abu dhabi": "Asia/Dubai",
"riyadh": "Asia/Riyadh",
"doha": "Asia/Qatar",
"tehran": "Asia/Tehran",
"tel aviv": "Asia/Jerusalem",
"jerusalem": "Asia/Jerusalem",
}

# =====================================================
# 🔧 HELPERS
# =====================================================

def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = text.replace("_", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text

def get_flag_from_timezone(tz: str) -> str:
    country_map = {
        "Europe/Stockholm": "SE",
        "Europe/Oslo": "NO",
        "Europe/Copenhagen": "DK",
        "Europe/Helsinki": "FI",
        "Europe/Berlin": "DE",
        "Europe/Paris": "FR",
        "Europe/London": "GB",
        "Europe/Rome": "IT",
        "Europe/Madrid": "ES",
        "Europe/Amsterdam": "NL",
        "Europe/Brussels": "BE",
        "Europe/Zurich": "CH",
        "Europe/Warsaw": "PL",
        "Europe/Athens": "GR",
        "Europe/Istanbul": "TR",
        "Asia/Tokyo": "JP",
        "Asia/Seoul": "KR",
        "Asia/Shanghai": "CN",
        "Asia/Kolkata": "IN",
        "Asia/Kuala_Lumpur": "MY",
        "Asia/Singapore": "SG",
        "Asia/Dubai": "AE",
        "America/New_York": "US",
        "America/Los_Angeles": "US",
        "America/Chicago": "US",
        "America/Denver": "US",
        "America/Toronto": "CA",
        "America/Sao_Paulo": "BR",
        "Australia/Sydney": "AU",
    }
    code = country_map.get(tz)
    if not code:
        return ""
    return chr(127397 + ord(code[0])) + chr(127397 + ord(code[1]))

def get_day_icon(hour: int) -> str:
    if 6 <= hour < 17:
        return "☀️"
    elif 17 <= hour < 20:
        return "🌇"
    elif 20 <= hour < 23:
        return "🌆"
    else:
        return "🌌"

async def fetch_time_from_api(timezone: str):
    try:
        timeout = aiohttp.ClientTimeout(total=2.5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"http://worldtimeapi.org/api/timezone/{timezone}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    dt = datetime.fromisoformat(data["datetime"])
                    return dt
    except Exception:
        pass
    return None

def fallback_zoneinfo(timezone: str):
    try:
        return datetime.now(ZoneInfo(timezone))
    except Exception:
        return None

# =====================================================
# 🌍 COMMAND
# =====================================================

async def register(bot, data_dir):

    @bot.tree.command(
        name="time",
        description="World clock (multi-city)"
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

        for raw_input in inputs:

            normalized = normalize(raw_input)

            timezone = CORE_CITIES.get(normalized)

            # Fuzzy
            if not timezone:
                matches = get_close_matches(normalized, CORE_CITIES.keys(), n=1, cutoff=0.7)
                if matches:
                    timezone = CORE_CITIES[matches[0]]
                    corrections.append(f"{raw_input} → {matches[0].title()}")

            if not timezone:
                lines.append(f"❌  {raw_input}")
                continue

            dt = await fetch_time_from_api(timezone)
            if not dt:
                dt = fallback_zoneinfo(timezone)

            if not dt:
                lines.append(f"❌  {raw_input}")
                continue

            hour = dt.hour
            minute = dt.minute

            city_display = timezone.split("/")[-1].replace("_", " ")
            icon = get_day_icon(hour)
            flag = get_flag_from_timezone(timezone)

            lines.append(
                f"{flag}  {icon}  {city_display:<12}  {hour:02}:{minute:02}"
            )

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

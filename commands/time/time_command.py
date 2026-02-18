from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo
from difflib import get_close_matches
from typing import Dict, Tuple

import discord
from discord import app_commands


# =====================================================
# 🌍 CITY DATABASE
# Format:
# "city name": ("Timezone/String", "CountryCode")
# =====================================================

CORE_CITIES: Dict[str, Tuple[str, str]] = {

    # EUROPE
    "stockholm": ("Europe/Stockholm", "SE"),
    "gothenburg": ("Europe/Stockholm", "SE"),
    "oslo": ("Europe/Oslo", "NO"),
    "copenhagen": ("Europe/Copenhagen", "DK"),
    "helsinki": ("Europe/Helsinki", "FI"),
    "berlin": ("Europe/Berlin", "DE"),
    "paris": ("Europe/Paris", "FR"),
    "rome": ("Europe/Rome", "IT"),
    "madrid": ("Europe/Madrid", "ES"),
    "amsterdam": ("Europe/Amsterdam", "NL"),
    "brussels": ("Europe/Brussels", "BE"),
    "zurich": ("Europe/Zurich", "CH"),
    "warsaw": ("Europe/Warsaw", "PL"),
    "athens": ("Europe/Athens", "GR"),
    "london": ("Europe/London", "GB"),
    "dublin": ("Europe/Dublin", "IE"),
    "istanbul": ("Europe/Istanbul", "TR"),
    "ankara": ("Europe/Istanbul", "TR"),

    # USA
    "new york": ("America/New_York", "US"),
    "washington": ("America/New_York", "US"),
    "los angeles": ("America/Los_Angeles", "US"),
    "san francisco": ("America/Los_Angeles", "US"),
    "chicago": ("America/Chicago", "US"),
    "houston": ("America/Chicago", "US"),
    "denver": ("America/Denver", "US"),
    "phoenix": ("America/Phoenix", "US"),
    "seattle": ("America/Los_Angeles", "US"),
    "miami": ("America/New_York", "US"),

    # CANADA
    "toronto": ("America/Toronto", "CA"),
    "vancouver": ("America/Vancouver", "CA"),

    # LATAM
    "mexico city": ("America/Mexico_City", "MX"),
    "buenos aires": ("America/Argentina/Buenos_Aires", "AR"),
    "sao paulo": ("America/Sao_Paulo", "BR"),

    # ASIA
    "tokyo": ("Asia/Tokyo", "JP"),
    "osaka": ("Asia/Tokyo", "JP"),
    "seoul": ("Asia/Seoul", "KR"),
    "beijing": ("Asia/Shanghai", "CN"),
    "shanghai": ("Asia/Shanghai", "CN"),
    "singapore": ("Asia/Singapore", "SG"),
    "bangkok": ("Asia/Bangkok", "TH"),
    "kuala lumpur": ("Asia/Kuala_Lumpur", "MY"),
    "dubai": ("Asia/Dubai", "AE"),
    "riyadh": ("Asia/Riyadh", "SA"),

    # OCEANIA
    "sydney": ("Australia/Sydney", "AU"),
    "melbourne": ("Australia/Sydney", "AU"),
    "brisbane": ("Australia/Brisbane", "AU"),
    "perth": ("Australia/Perth", "AU"),
    "auckland": ("Pacific/Auckland", "NZ"),

    # AFRICA
    "cairo": ("Africa/Cairo", "EG"),
    "nairobi": ("Africa/Nairobi", "KE"),
    "lagos": ("Africa/Lagos", "NG"),
    "johannesburg": ("Africa/Johannesburg", "ZA"),
}


# =====================================================
# 🔧 HELPERS
# =====================================================

def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def country_code_to_flag(code: str) -> str:
    return "".join(chr(127397 + ord(c)) for c in code.upper())


def day_icon(hour: int) -> str:
    if 6 <= hour < 17:
        return "☀️"
    elif 17 <= hour < 20:
        return "🌇"
    elif 20 <= hour < 23:
        return "🌆"
    return "🌌"


# =====================================================
# 🕒 COMMAND REGISTRATION
# =====================================================

def register(bot, data_dir: str):

    @bot.tree.command(
        name="time",
        description="World clock dashboard (multi-city)"
    )
    @app_commands.describe(
        locations="Example: Stockholm, Tokyo, New York"
    )
    async def time_command(interaction: discord.Interaction, locations: str):

        await interaction.response.defer()

        inputs = [x.strip() for x in locations.split(",") if x.strip()]
        if not inputs:
            await interaction.followup.send("Provide at least one city.")
            return

        if len(inputs) > 6:
            await interaction.followup.send("Maximum 6 cities allowed.")
            return

        rows = []
        corrections = []

        for raw in inputs:
            key = normalize(raw)
            entry = CORE_CITIES.get(key)

            if not entry:
                matches = get_close_matches(key, CORE_CITIES.keys(), n=1, cutoff=0.7)
                if matches:
                    entry = CORE_CITIES[matches[0]]
                    corrections.append(f"{raw} → {matches[0].title()}")

            if not entry:
                rows.append(f"❌  {raw}")
                continue

            tz, cc = entry

            try:
                now = datetime.now(ZoneInfo(tz))
            except Exception:
                rows.append(f"❌  {raw}")
                continue

            flag = country_code_to_flag(cc)
            icon = day_icon(now.hour)
            city_display = tz.split("/")[-1].replace("_", " ")
            offset = now.strftime("%z")
            offset_fmt = f"UTC{int(offset[:3]):+}"

            rows.append(
                f"{flag} {icon}  {city_display:<15}  {now.strftime('%H:%M')}  ({offset_fmt})"
            )

        if not rows:
            await interaction.followup.send("No valid locations.")
            return

        embed = discord.Embed(
            title="🌍 Time Dashboard",
            description="```" + "\n".join(rows) + "```",
            color=0x2F3136
        )

        if corrections:
            embed.add_field(
                name="Auto-corrected",
                value=", ".join(corrections),
                inline=False
            )

        await interaction.followup.send(embed=embed)


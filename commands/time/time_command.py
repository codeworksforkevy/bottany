from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo
from difflib import get_close_matches
from typing import Dict, Tuple

import discord
from discord import app_commands


# =====================================================
# 🌍 CORE CITY DATABASE
# =====================================================

CORE_CITIES: Dict[str, Tuple[str, str]] = {
    "stockholm": ("Europe/Stockholm", "SE"),
    "gothenburg": ("Europe/Stockholm", "SE"),
    "oslo": ("Europe/Oslo", "NO"),
    "copenhagen": ("Europe/Copenhagen", "DK"),
    "helsinki": ("Europe/Helsinki", "FI"),
    "warsaw": ("Europe/Warsaw", "PL"),
    "berlin": ("Europe/Berlin", "DE"),
    "amsterdam": ("Europe/Amsterdam", "NL"),
    "brussels": ("Europe/Brussels", "BE"),
    "paris": ("Europe/Paris", "FR"),
    "madrid": ("Europe/Madrid", "ES"),
    "rome": ("Europe/Rome", "IT"),
    "vienna": ("Europe/Vienna", "AT"),
    "athens": ("Europe/Athens", "GR"),
    "dublin": ("Europe/Dublin", "IE"),
    "london": ("Europe/London", "GB"),
    "zurich": ("Europe/Zurich", "CH"),
    "reykjavik": ("Atlantic/Reykjavik", "IS"),
    "ankara": ("Europe/Istanbul", "TR"),
    "istanbul": ("Europe/Istanbul", "TR"),

    "new york": ("America/New_York", "US"),
    "los angeles": ("America/Los_Angeles", "US"),
    "chicago": ("America/Chicago", "US"),
    "miami": ("America/New_York", "US"),
    "seattle": ("America/Los_Angeles", "US"),
    "denver": ("America/Denver", "US"),
    "phoenix": ("America/Phoenix", "US"),

    "toronto": ("America/Toronto", "CA"),
    "vancouver": ("America/Vancouver", "CA"),

    "mexico city": ("America/Mexico_City", "MX"),
    "bogota": ("America/Bogota", "CO"),
    "lima": ("America/Lima", "PE"),
    "buenos aires": ("America/Argentina/Buenos_Aires", "AR"),
    "sao paulo": ("America/Sao_Paulo", "BR"),

    "tokyo": ("Asia/Tokyo", "JP"),
    "osaka": ("Asia/Tokyo", "JP"),
    "seoul": ("Asia/Seoul", "KR"),
    "beijing": ("Asia/Shanghai", "CN"),
    "shanghai": ("Asia/Shanghai", "CN"),
    "singapore": ("Asia/Singapore", "SG"),
    "dubai": ("Asia/Dubai", "AE"),

    "sydney": ("Australia/Sydney", "AU"),
    "melbourne": ("Australia/Sydney", "AU"),

    "cairo": ("Africa/Cairo", "EG"),
    "nairobi": ("Africa/Nairobi", "KE"),

    "new delhi": ("Asia/Kolkata", "IN"),
    "kuala lumpur": ("Asia/Kuala_Lumpur", "MY"),
}


# =====================================================
# HELPERS
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
# REGISTER (HYBRID LOADER SAFE)
# =====================================================

def register(bot, data_dir: str):

    existing = bot.tree.get_command("time")

    if existing:
        # Eğer zaten varsa tekrar ekleme
        return

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
                matches = get_close_matches(
                    key,
                    CORE_CITIES.keys(),
                    n=1,
                    cutoff=0.7
                )
                if matches:
                    entry = CORE_CITIES[matches[0]]
                    corrections.append(
                        f"{raw} → {matches[0].title()}"
                    )

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

            rows.append(
                f"{flag} {icon}  {city_display:<18}  {now.strftime('%H:%M')}"
            )

        embed = discord.Embed(
            title="Time Dashboard",
            description="```" + "\n".join(rows)[:3900] + "```",
            color=0x2B2D31
        )

        if corrections:
            embed.add_field(
                name="Auto-corrected",
                value=", ".join(corrections)[:1024],
                inline=False
            )

        await interaction.followup.send(embed=embed)

    command = app_commands.Command(
        name="time",
        description="Premium world clock dashboard",
        callback=time_command
    )

    bot.tree.add_command(command)

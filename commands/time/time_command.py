
from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo
from difflib import get_close_matches
from typing import Dict, Tuple

import discord
from discord import app_commands


CORE_CITIES: Dict[str, Tuple[str, str]] = {

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

    "new york": ("America/New_York", "US"),
    "los angeles": ("America/Los_Angeles", "US"),
    "chicago": ("America/Chicago", "US"),
    "denver": ("America/Denver", "US"),
    "phoenix": ("America/Phoenix", "US"),
    "miami": ("America/New_York", "US"),

    "tokyo": ("Asia/Tokyo", "JP"),
    "seoul": ("Asia/Seoul", "KR"),
    "beijing": ("Asia/Shanghai", "CN"),
    "singapore": ("Asia/Singapore", "SG"),

    "sydney": ("Australia/Sydney", "AU"),
    "auckland": ("Pacific/Auckland", "NZ"),
}


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
    return "🌙"


def register(bot, data_dir: str):

    @bot.tree.command(
        name="time",
        description="Premium world clock dashboard"
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

        embed = discord.Embed(
            title="Time Dashboard",
            color=0x1E1E2E
        )

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
                embed.add_field(
                    name=f"❌ {raw}",
                    value="Not found",
                    inline=True
                )
                continue

            tz, cc = entry

            try:
                now = datetime.now(ZoneInfo(tz))
            except Exception:
                embed.add_field(
                    name=f"❌ {raw}",
                    value="Timezone error",
                    inline=True
                )
                continue

            flag = country_code_to_flag(cc)
            icon = day_icon(now.hour)
            city_display = tz.split("/")[-1].replace("_", " ")

            embed.add_field(
                name=f"{flag} {city_display}",
                value=f"{icon}   **{now.strftime('%H:%M')}**",
                inline=True
            )

        if corrections:
            embed.add_field(
                name="Auto-corrected",
                value=", ".join(corrections),
                inline=False
            )

        embed.set_footer(text="Live world clock • Bottany")

        await interaction.followup.send(embed=embed)

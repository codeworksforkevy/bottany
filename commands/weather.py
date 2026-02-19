from __future__ import annotations
import os
import json
import asyncio
import time
from typing import Optional, Dict, Any, List, Tuple

import discord
from discord import app_commands

from providers.open_meteo import geocode_city, fetch_forecast
from providers.bbc_rss import fetch_bbc_rss_by_location_id

# =========================================================
# SIMPLE CACHE (5 min)
# =========================================================

_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
CACHE_TTL = 300  # 5 minutes


def _get_cache(key: str):
    entry = _CACHE.get(key)
    if not entry:
        return None
    expires, data = entry
    if time.time() > expires:
        _CACHE.pop(key, None)
        return None
    return data


def _set_cache(key: str, data: Dict[str, Any]):
    _CACHE[key] = (time.time() + CACHE_TTL, data)


# =========================================================
# HELPERS
# =========================================================

def _load_json(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _place_label(g) -> str:
    parts = [g.name]
    if g.admin1:
        parts.append(g.admin1)
    if g.country:
        parts.append(g.country)
    return ", ".join([p for p in parts if p])


def _fmt(x, unit=""):
    if x is None:
        return "—"
    try:
        return f"{float(x):.1f}{unit}"
    except Exception:
        return "—"


# =========================================================
# WEATHER CODE MAP
# =========================================================

WEATHER_CODE_MAP: Dict[int, Tuple[str, str]] = {
    0: ("Clear", "☀️"),
    1: ("Mainly clear", "🌤️"),
    2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Fog", "🌫️"),
    51: ("Drizzle", "🌦️"),
    61: ("Rain", "🌧️"),
    71: ("Snow", "❄️"),
    95: ("Thunderstorm", "⛈️"),
}


# =========================================================
# EMBED BUILDER (LIGHT VERSION)
# =========================================================

def build_weather_embed(
    *,
    place_label: str,
    forecast: Dict[str, Any],
    bbc_items: Optional[List[Dict[str, str]]] = None,
    source_footer: str = "Open-Meteo"
) -> discord.Embed:

    current = forecast.get("current") or {}
    daily = forecast.get("daily") or {}

    wcode = current.get("weather_code")
    try:
        wcode = int(wcode)
    except Exception:
        wcode = None

    label, emoji = WEATHER_CODE_MAP.get(wcode, ("Conditions", "🛰️"))

    title = f"{emoji} {place_label}"
    desc = f"**{label}**"

    # Simple severe flag
    wind = float(current.get("wind_speed_10m") or 0)
    precip = float(current.get("precipitation") or 0)

    if wcode in (95,) or wind >= 60 or precip >= 15:
        desc = f"🚨 Severe conditions\n{desc}"

    embed = discord.Embed(title=title, description=desc, color=0x1D4ED8)

    embed.add_field(
        name="Temperature",
        value=f"🌡 {_fmt(current.get('temperature_2m'), '°C')}\n"
              f"Feels: {_fmt(current.get('apparent_temperature'), '°C')}",
        inline=True
    )

    embed.add_field(
        name="Wind",
        value=f"💨 {_fmt(wind, ' km/h')}",
        inline=True
    )

    embed.add_field(
        name="Precipitation",
        value=f"🌧 {_fmt(precip, ' mm')}",
        inline=True
    )

    # 3-day outlook
    dates = daily.get("time") or []
    tmin = daily.get("temperature_2m_min") or []
    tmax = daily.get("temperature_2m_max") or []

    lines = []
    for i in range(min(3, len(dates))):
        lines.append(
            f"• {dates[i]} — {_fmt(tmin[i], '°C')} / {_fmt(tmax[i], '°C')}"
        )

    if lines:
        embed.add_field(name="3-Day Outlook", value="\n".join(lines), inline=False)

    # BBC enrichment (UK only)
    if bbc_items:
        bbc_lines = []
        for it in bbc_items[:2]:
            if it.get("title"):
                bbc_lines.append(f"• {it['title']}")
        if bbc_lines:
            embed.add_field(
                name="BBC Summary (UK)",
                value="\n".join(bbc_lines),
                inline=False
            )

    updated = current.get("time")
    footer = f"Source: {source_footer}"
    if updated:
        footer += f" · Updated {updated}"
    embed.set_footer(text=footer)

    return embed


# =========================================================
# VIEW (DETAILS + PROPER REFRESH)
# =========================================================

class WeatherView(discord.ui.View):

    def __init__(self, *, forecast, place_label, refresh_cb=None, timeout=120):
        super().__init__(timeout=timeout)
        self._forecast = forecast
        self._place_label = place_label
        self._refresh_cb = refresh_cb

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.secondary)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not self._refresh_cb:
            await interaction.response.send_message(
                "Refresh unavailable.",
                ephemeral=True
            )
            return

        try:
            self._forecast = await self._refresh_cb()

            new_embed = build_weather_embed(
                place_label=self._place_label,
                forecast=self._forecast
            )

            await interaction.response.edit_message(embed=new_embed, view=self)

        except Exception:
            await interaction.response.send_message(
                "Could not refresh right now.",
                ephemeral=True
            )


# =========================================================
# COMMAND
# =========================================================

def register_weather(bot, data_dir: str) -> None:

    bbc_map_path = os.path.join(data_dir, "bbc_location_registry.json")
    BBC_MAP = _load_json(bbc_map_path).get("city_to_location_id", {})
    BBC_MAP = {k.lower(): v for k, v in BBC_MAP.items()}

    @bot.tree.command(
        name="weather",
        description="Weather forecast by city."
    )
    async def weather_cmd(interaction: discord.Interaction, city: str):

        city_clean = (city or "").strip()
        if not city_clean:
            await interaction.response.send_message(
                "Example: `/weather London`",
                ephemeral=True
            )
            return

        geo = await asyncio.to_thread(geocode_city, city_clean)
        if not geo:
            await interaction.response.send_message(
                f"City not found: '{city_clean}'.",
                ephemeral=True
            )
            return

        cache_key = f"{geo.latitude}:{geo.longitude}"
        fc = _get_cache(cache_key)

        if not fc:
            try:
                fc = await asyncio.to_thread(
                    fetch_forecast,
                    geo.latitude,
                    geo.longitude,
                    timezone=geo.timezone or "auto",
                    days=3
                )
                if fc:
                    _set_cache(cache_key, fc)
            except Exception:
                fc = None

        # BBC enrichment (UK only)
        loc_id = BBC_MAP.get(city_clean.lower())
        bbc = await asyncio.to_thread(fetch_bbc_rss_by_location_id, loc_id) if loc_id else None

        if not fc:
            await interaction.response.send_message(
                "Weather service temporarily unavailable.",
                ephemeral=True
            )
            return

        place = _place_label(geo)

        embed = build_weather_embed(
            place_label=place,
            forecast=fc,
            bbc_items=(bbc.get("items") if bbc else None),
            source_footer=("Open-Meteo + BBC RSS" if bbc else "Open-Meteo")
        )

        async def refresh_cb():
            new_fc = await asyncio.to_thread(
                fetch_forecast,
                geo.latitude,
                geo.longitude,
                timezone=geo.timezone or "auto",
                days=3
            )
            if new_fc:
                _set_cache(cache_key, new_fc)
            return new_fc

        view = WeatherView(
            forecast=fc,
            place_label=place,
            refresh_cb=refresh_cb
        )

        await interaction.response.send_message(embed=embed, view=view)

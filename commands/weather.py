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
# CACHE (5 min)
# =========================================================

_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
CACHE_TTL = 300


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
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


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
# WEATHER MAP
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
# AIR QUALITY FETCH (Open-Meteo)
# =========================================================

import urllib.request
import urllib.parse


def fetch_air_quality(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    try:
        params = urllib.parse.urlencode({
            "latitude": lat,
            "longitude": lon,
            "current": "european_aqi,pm2_5,pm10"
        })

        url = f"https://air-quality-api.open-meteo.com/v1/air-quality?{params}"

        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        return data.get("current")
    except Exception:
        return None


def _aqi_label(aqi: Optional[float]) -> str:
    if aqi is None:
        return "—"

    try:
        aqi = float(aqi)
    except Exception:
        return "—"

    if aqi <= 20:
        return "🟢 Good"
    elif aqi <= 40:
        return "🟡 Fair"
    elif aqi <= 60:
        return "🟠 Moderate"
    elif aqi <= 80:
        return "🔴 Poor"
    else:
        return "🟣 Very Poor"


# =========================================================
# EMBED BUILDER (Premium + AQ)
# =========================================================

def build_weather_embed(
    *,
    place_label: str,
    forecast: Dict[str, Any],
    air_quality: Optional[Dict[str, Any]] = None,
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

    wind = float(current.get("wind_speed_10m") or 0)
    precip = float(current.get("precipitation") or 0)

    severe = (wcode in (95,) or wind >= 60 or precip >= 15)

    # COLOR LOGIC
    if severe:
        color = 0x7F1D1D
    elif bbc_items:
        color = 0x0A1F44
    else:
        color = 0x1D4ED8

    if bbc_items:
        title = f"🇬🇧 {emoji} {place_label}"
    else:
        title = f"{emoji} {place_label}"

    desc = f"**{label}**"
    if severe:
        desc = f"🚨 Severe conditions\n{desc}"

    embed = discord.Embed(
        title=title[:256],
        description=desc[:4096],
        color=color
    )

    # Temperature
    embed.add_field(
        name="Temperature",
        value=(
            f"🌡 {_fmt(current.get('temperature_2m'), '°C')}\n"
            f"Feels: {_fmt(current.get('apparent_temperature'), '°C')}"
        )[:1024],
        inline=True
    )

    embed.add_field(
        name="Wind",
        value=f"💨 {_fmt(wind, ' km/h')}"[:1024],
        inline=True
    )

    embed.add_field(
        name="Precipitation",
        value=f"🌧 {_fmt(precip, ' mm')}"[:1024],
        inline=True
    )

    # Air Quality
    if air_quality:
        aqi = air_quality.get("european_aqi")
        pm25 = air_quality.get("pm2_5")
        pm10 = air_quality.get("pm10")

        embed.add_field(
            name="Air Quality",
            value=(
                f"AQI: {_aqi_label(aqi)}\n"
                f"PM2.5: {_fmt(pm25, ' µg/m³')}\n"
                f"PM10: {_fmt(pm10, ' µg/m³')}"
            )[:1024],
            inline=False
        )

    # Outlook
    dates = daily.get("time") or []
    tmin = daily.get("temperature_2m_min") or []
    tmax = daily.get("temperature_2m_max") or []

    lines = []
    for i in range(min(3, len(dates))):
        lines.append(
            f"• {dates[i]} — {_fmt(tmin[i], '°C')} / {_fmt(tmax[i], '°C')}"
        )

    if lines:
        embed.add_field(
            name="3-Day Outlook",
            value="\n".join(lines)[:1024],
            inline=False
        )

    # BBC Premium
    if bbc_items:

        embed.add_field(
            name="\u200B",
            value="──────────────",
            inline=False
        )

        bbc_lines = []
        for it in bbc_items[:2]:
            t = (it.get("title") or "").strip()
            if t:
                bbc_lines.append(f"• {t[:200]}")

        if bbc_lines:
            embed.add_field(
                name="🇬🇧 BBC Weather Insight (UK)",
                value=("_Editorial summary_\n" + "\n".join(bbc_lines))[:1024],
                inline=False
            )

    updated = current.get("time")
    footer = f"Source: {source_footer}"
    if updated:
        footer += f" · Updated {updated}"

    embed.set_footer(text=footer[:2048])

    return embed


# =========================================================
# VIEW
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
            await interaction.response.send_message("Refresh unavailable.", ephemeral=True)
            return

        try:
            self._forecast = await self._refresh_cb()

            await interaction.response.edit_message(
                embed=self._forecast["embed"],
                view=self
            )

        except Exception:
            await interaction.response.send_message("Could not refresh.", ephemeral=True)


# =========================================================
# COMMAND
# =========================================================

def register_weather(bot, data_dir: str) -> None:

    bbc_map_path = os.path.join(data_dir, "bbc_location_registry.json")
    BBC_MAP = _load_json(bbc_map_path).get("city_to_location_id", {})
    BBC_MAP = {k.lower(): v for k, v in BBC_MAP.items()}

    @bot.tree.command(name="weather", description="Weather forecast by city.")
    async def weather_cmd(interaction: discord.Interaction, city: str):

        city_clean = (city or "").strip()

        geo = await asyncio.to_thread(geocode_city, city_clean)
        if not geo:
            await interaction.response.send_message("City not found.", ephemeral=True)
            return

        cache_key = f"{geo.latitude}:{geo.longitude}"

        data = _get_cache(cache_key)

        if not data:
            fc = await asyncio.to_thread(
                fetch_forecast,
                geo.latitude,
                geo.longitude,
                timezone=geo.timezone or "auto",
                days=3
            )

            aq = await asyncio.to_thread(fetch_air_quality, geo.latitude, geo.longitude)

            data = {"forecast": fc, "air_quality": aq}
            _set_cache(cache_key, data)

        fc = data["forecast"]
        aq = data["air_quality"]

        # BBC matching tolerant
        city_key = city_clean.lower().split(",")[0].strip()
        loc_id = None
        for k, v in BBC_MAP.items():
            if k in city_key:
                loc_id = v
                break

        bbc = await asyncio.to_thread(fetch_bbc_rss_by_location_id, loc_id) if loc_id else None

        place = _place_label(geo)

        embed = build_weather_embed(
            place_label=place,
            forecast=fc,
            air_quality=aq,
            bbc_items=(bbc.get("items") if bbc else None),
            source_footer=("Open-Meteo + BBC RSS" if bbc else "Open-Meteo")
        )

        view = WeatherView(forecast=data, place_label=place)

        await interaction.response.send_message(embed=embed, view=view)

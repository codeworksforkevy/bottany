from __future__ import annotations
import os, json, asyncio
from typing import Optional, Dict, Any, List, Tuple
import discord
from discord import app_commands

from providers.open_meteo import geocode_city, fetch_forecast
from providers.bbc_rss import fetch_bbc_rss_by_location_id

# ---------------------------
# Registry helpers
# ---------------------------

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

def _deg_to_compass(deg: Optional[float]) -> str:
    if deg is None:
        return "—"
    dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
    ix = int((float(deg) / 22.5) + 0.5) % 16
    return dirs[ix]

def _fmt_num(x: Optional[float], unit: str = "", dp: int = 0) -> str:
    if x is None:
        return "—"
    try:
        v = float(x)
    except Exception:
        return "—"
    return f"{v:.{dp}f}{unit}" if dp else f"{v:.0f}{unit}"

def _mini_bar(value: float, *, max_value: float, length: int = 10, solid: str = "█", empty: str = "░") -> str:
    if max_value <= 0:
        return empty * length
    ratio = max(0.0, min(1.0, float(value) / float(max_value)))
    fill = int(round(ratio * length))
    return solid * fill + empty * (length - fill)

# ---------------------------
# Weather code mapping (Open-Meteo/WMO)
# ---------------------------

WEATHER_CODE_MAP: Dict[int, Tuple[str, str]] = {
    0: ("Clear", "☀️"),
    1: ("Mainly clear", "🌤️"),
    2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Fog", "🌫️"),
    48: ("Depositing rime fog", "🌫️"),
    51: ("Light drizzle", "🌦️"),
    53: ("Moderate drizzle", "🌦️"),
    55: ("Dense drizzle", "🌧️"),
    56: ("Light freezing drizzle", "🌧️"),
    57: ("Dense freezing drizzle", "🌧️"),
    61: ("Slight rain", "🌧️"),
    63: ("Moderate rain", "🌧️"),
    65: ("Heavy rain", "⛈️"),
    66: ("Light freezing rain", "🌧️"),
    67: ("Heavy freezing rain", "⛈️"),
    71: ("Slight snow fall", "🌨️"),
    73: ("Moderate snow fall", "🌨️"),
    75: ("Heavy snow fall", "❄️"),
    77: ("Snow grains", "🌨️"),
    80: ("Slight rain showers", "🌦️"),
    81: ("Moderate rain showers", "🌧️"),
    82: ("Violent rain showers", "⛈️"),
    85: ("Slight snow showers", "🌨️"),
    86: ("Heavy snow showers", "❄️"),
    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm with slight hail", "⛈️"),
    99: ("Thunderstorm with heavy hail", "⛈️"),
}

def _pick_accent_color(wcode: Optional[int], precip: float, wind: float, uv: float, vis_km: float) -> int:
    # restrained but semantic palette for a "card system" aesthetic
    if (wcode in (95, 96, 99)) or precip >= 10:
        return 0x172554  # deep storm navy
    if wcode in (71, 73, 75, 77, 85, 86):
        return 0xB8D8F0  # icy
    if wcode in (45, 48) or vis_km <= 2:
        return 0x374151  # fog slate
    if uv >= 7:
        return 0xB45309  # strong UV amber-brown
    if precip >= 1:
        return 0x1D4ED8  # rain blue
    if wind >= 45:
        return 0x334155  # windy slate
    return 0xD4A017      # clear warm

def _advisory_ribbon(current: Dict[str, Any]) -> Optional[str]:
    t = current.get("temperature_2m")
    feels = current.get("apparent_temperature")
    precip = float(current.get("precipitation") or 0.0)
    wind = float(current.get("wind_speed_10m") or 0.0)
    uv = float(current.get("uv_index") or 0.0)
    vis_m = current.get("visibility")
    pressure = current.get("pressure_msl")

    advisories: List[str] = []

    if wind >= 60:
        advisories.append("⚠️ Severe wind")
    elif wind >= 45:
        advisories.append("⚠️ Strong wind")

    if precip >= 10:
        advisories.append("⛈️ Heavy precipitation")
    elif precip >= 3:
        advisories.append("🌧️ Wet conditions")

    if uv >= 8:
        advisories.append("☀️ High UV")
    elif uv >= 6:
        advisories.append("☀️ Moderate UV")

    if vis_m is not None:
        try:
            vis_km = float(vis_m) / 1000.0
            if vis_km <= 1:
                advisories.append("🌫️ Very low visibility")
            elif vis_km <= 3:
                advisories.append("🌫️ Low visibility")
        except Exception:
            pass

    if pressure is not None:
        try:
            p = float(pressure)
            if p <= 990:
                advisories.append("📉 Low pressure")
            elif p >= 1030:
                advisories.append("📈 High pressure")
        except Exception:
            pass

    if t is not None and feels is not None:
        try:
            delta = float(t) - float(feels)
            if delta >= 4:
                advisories.append("🥶 Feels colder")
            elif delta <= -3:
                advisories.append("🥵 Feels warmer")
        except Exception:
            pass

    if not advisories:
        return None
    return " · ".join(advisories[:2])

def build_weather_embed_card_system_v2(
    *,
    place_label: str,
    forecast: Dict[str, Any],
    bbc_items: Optional[List[Dict[str, str]]] = None,
    source_footer: str = "Open-Meteo (UKMO/UKV where available)",
) -> discord.Embed:
    current: Dict[str, Any] = forecast.get("current") or {}
    daily: Dict[str, Any] = forecast.get("daily") or {}

    # Weather code -> label + icon
    wcode_raw = current.get("weather_code")
    try:
        wcode = int(wcode_raw) if wcode_raw is not None else None
    except Exception:
        wcode = None
    cond_label, cond_emoji = WEATHER_CODE_MAP.get(wcode, ("Conditions", "🛰️"))

    # Metrics
    precip_now = float(current.get("precipitation") or 0.0)
    wind = float(current.get("wind_speed_10m") or 0.0)
    uv = float(current.get("uv_index") or 0.0)
    visibility_m = current.get("visibility")

    vis_km = 999.0
    if visibility_m is not None:
        try:
            vis_km = float(visibility_m) / 1000.0
        except Exception:
            vis_km = 999.0

    color = _pick_accent_color(wcode, precip_now, wind, uv, vis_km)
    ribbon = _advisory_ribbon(current)

    title = f"{cond_emoji} {place_label} — Atmospheric Snapshot"
    desc = f"_{cond_label}._"
    if ribbon:
        desc = f"**{ribbon}**\n{desc}"

    embed = discord.Embed(title=title, description=desc, color=color)

    # Micro-gauges
    precip_g = _mini_bar(precip_now, max_value=12.0, length=10)
    wind_g = _mini_bar(wind, max_value=70.0, length=10)
    uv_g = _mini_bar(uv, max_value=11.0, length=10)

    # THERMAL
    t = current.get("temperature_2m")
    feels = current.get("apparent_temperature")
    tmin0 = (daily.get("temperature_2m_min") or [None])[0]
    tmax0 = (daily.get("temperature_2m_max") or [None])[0]
    thermal = [
        f"🌡️ Air: **{_fmt_num(t, '°C', dp=1)}**",
        f"🧍 Feels: **{_fmt_num(feels, '°C', dp=1)}**",
    ]
    if tmin0 is not None and tmax0 is not None:
        thermal.append(f"📈 Today: **{_fmt_num(tmin0,'°C')}–{_fmt_num(tmax0,'°C')}**")
    embed.add_field(name="THERMAL", value="\n".join(thermal), inline=True)

    # HYDRO
    pprob0 = (daily.get("precipitation_probability_max") or [None])[0]
    psum0 = (daily.get("precipitation_sum") or [None])[0]
    hydro = [
        f"🌧️ Now: **{_fmt_num(precip_now, ' mm', dp=1)}**  `{precip_g}`",
    ]
    if pprob0 is not None:
        hydro.append(f"☂️ Prob (max): **{_fmt_num(pprob0, '%')}**")
    if psum0 is not None:
        hydro.append(f"📦 Day sum: **{_fmt_num(psum0, ' mm', dp=1)}**")
    embed.add_field(name="HYDRO", value="\n".join(hydro), inline=True)

    # AERO
    wdir = _deg_to_compass(current.get("wind_direction_10m"))
    wmax0 = (daily.get("wind_speed_10m_max") or [None])[0]
    aero = [
        f"💨 Wind: **{_fmt_num(wind, ' km/h')}** ({wdir})  `{wind_g}`",
    ]
    if wmax0 is not None:
        aero.append(f"🌬️ Day max: **{_fmt_num(wmax0, ' km/h')}**")
    embed.add_field(name="AERO", value="\n".join(aero), inline=True)

    # ATMOS
    rh = current.get("relative_humidity_2m")
    pressure = current.get("pressure_msl")
    cloud = current.get("cloud_cover")
    atmos: List[str] = []
    if rh is not None:
        atmos.append(f"💧 Humidity: **{_fmt_num(rh, '%')}**")
    if pressure is not None:
        atmos.append(f"🧭 Pressure: **{_fmt_num(pressure, ' hPa')}**")
    if cloud is not None:
        atmos.append(f"☁️ Cloud: **{_fmt_num(cloud, '%')}**")
    if visibility_m is not None:
        atmos.append(f"👁️ Visibility: **{_fmt_num(vis_km, ' km', dp=1)}**")
    if current.get("uv_index") is not None:
        atmos.append(f"🔆 UV: **{_fmt_num(uv, '', dp=1)}**  `{uv_g}`")
    embed.add_field(name="ATMOS", value="\n".join(atmos) if atmos else "—", inline=False)

    # OUTLOOK (72h)
    dates = daily.get("time") or []
    d_wcode = daily.get("weather_code") or []
    d_uvmax = daily.get("uv_index_max") or []
    d_tmin = daily.get("temperature_2m_min") or []
    d_tmax = daily.get("temperature_2m_max") or []
    d_psum = daily.get("precipitation_sum") or []
    d_pprob = daily.get("precipitation_probability_max") or []

    lines: List[str] = []
    for i in range(min(3, len(dates))):
        code = None
        if i < len(d_wcode):
            try:
                code = int(d_wcode[i]) if d_wcode[i] is not None else None
            except Exception:
                code = None
        lab, em = WEATHER_CODE_MAP.get(code, ("", "•"))
        mn = d_tmin[i] if i < len(d_tmin) else None
        mx = d_tmax[i] if i < len(d_tmax) else None
        ps = d_psum[i] if i < len(d_psum) else None
        pr = d_pprob[i] if i < len(d_pprob) else None
        uvm = d_uvmax[i] if i < len(d_uvmax) else None

        parts: List[str] = []
        if mn is not None and mx is not None:
            parts.append(f"🌡️ {float(mn):.0f}–{float(mx):.0f}°C")
        if ps is not None:
            parts.append(f"🌧️ {float(ps):.1f} mm")
        if pr is not None:
            parts.append(f"☂️ {float(pr):.0f}%")
        if uvm is not None:
            parts.append(f"🔆 {float(uvm):.0f}")

        lines.append(f"▸ **{dates[i]}** {em} — " + " | ".join(parts))
    embed.add_field(name="OUTLOOK (72h)", value="\n".join(lines) if lines else "—", inline=False)

    # BBC summary (optional UK enrichment)
    if bbc_items:
        bbc_lines: List[str] = []
        for it in bbc_items[:3]:
            tline = (it.get("title") or "").strip()
            if tline:
                bbc_lines.append(f"• {tline}")
        if bbc_lines:
            embed.add_field(name="BBC SUMMARY (UK)", value="\n".join(bbc_lines), inline=False)

    updated = (current.get("time") or "").strip()
    footer = f"Source: {source_footer}"
    if updated:
        footer += f" · Updated {updated}"
    embed.set_footer(text=footer)
    return embed

def build_hourly_details_text(forecast: Dict[str, Any], *, hours: int = 12) -> str:
    hourly = forecast.get("hourly") or {}
    times = hourly.get("time") or []
    temp = hourly.get("temperature_2m") or []
    app = hourly.get("apparent_temperature") or []
    pprob = hourly.get("precipitation_probability") or []
    precip = hourly.get("precipitation") or []
    wcode = hourly.get("weather_code") or []
    wind = hourly.get("wind_speed_10m") or []
    wdir = hourly.get("wind_direction_10m") or []
    cloud = hourly.get("cloud_cover") or []
    rh = hourly.get("relative_humidity_2m") or []
    pres = hourly.get("pressure_msl") or []
    vis = hourly.get("visibility") or []
    uv = hourly.get("uv_index") or []

    n = min(int(hours), len(times))
    if n <= 0:
        return "No hourly data available."

    lines: List[str] = ["**Hourly details (next hours)**"]
    for i in range(n):
        code = None
        if i < len(wcode):
            try:
                code = int(wcode[i]) if wcode[i] is not None else None
            except Exception:
                code = None
        lab, em = WEATHER_CODE_MAP.get(code, ("", "•"))
        wd = _deg_to_compass(wdir[i] if i < len(wdir) else None)

        vis_km = None
        if i < len(vis) and vis[i] is not None:
            try:
                vis_km = float(vis[i]) / 1000.0
            except Exception:
                vis_km = None

        # Guard indices
        def g(arr, default=None):
            return arr[i] if i < len(arr) else default

        try:
            line = (
                f"• `{times[i]}` {em} "
                f"{float(g(temp, 0.0)):.0f}°C (feels {float(g(app, 0.0)):.0f}°C) | "
                f"☂️ {float(g(pprob, 0.0)):.0f}% | 🌧️ {float(g(precip, 0.0)):.1f}mm | "
                f"💨 {float(g(wind, 0.0)):.0f}km/h {wd} | "
                f"☁️ {float(g(cloud, 0.0)):.0f}% | 💧 {float(g(rh, 0.0)):.0f}% | "
                f"🧭 {float(g(pres, 0.0)):.0f}hPa | "
                f"👁️ {(f'{vis_km:.1f}km' if vis_km is not None else '—')} | "
                f"🔆 {float(g(uv, 0.0)):.0f}"
            )
        except Exception:
            line = f"• `{times[i]}` —"
        lines.append(line)

    text = "\n".join(lines)
    if len(text) > 1800:
        text = text[:1750] + "\n…(truncated)"
    return text

class WeatherDetailsView(discord.ui.View):
    def __init__(self, *, forecast: Dict[str, Any], refresh_cb=None, timeout: int = 120):
        super().__init__(timeout=timeout)
        self._forecast = forecast
        self._refresh_cb = refresh_cb

    @discord.ui.button(label="View Details", style=discord.ButtonStyle.primary)
    async def view_details(self, interaction: discord.Interaction, button: discord.ui.Button):
        text = build_hourly_details_text(self._forecast, hours=12)
        await interaction.response.send_message(text, ephemeral=True)

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.secondary)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._refresh_cb:
            await interaction.response.send_message("Refresh is not configured for this message.", ephemeral=True)
            return
        try:
            self._forecast = await self._refresh_cb()
            await interaction.response.send_message("Updated.", ephemeral=True)
        except Exception:
            await interaction.response.send_message("Could not refresh right now.", ephemeral=True)

# ---------------------------
# Command registration
# ---------------------------

def register_weather(bot, data_dir: str) -> None:
    # Optional: allow a small BBC mapping registry for UK cities (city -> location_id).
    bbc_map_path = os.path.join(data_dir, "bbc_location_registry.json")
    BBC_MAP = _load_json(bbc_map_path).get("city_to_location_id", {}) if os.path.exists(bbc_map_path) else {}

    @bot.tree.command(
        name="weather",
        description="Weather forecast by city (Open‑Meteo primary; optional BBC UK summary)."
    )
    @app_commands.describe(city="City name (e.g., London, Istanbul, Luxembourg)")
    async def weather_cmd(interaction: discord.Interaction, city: str):
        city_clean = (city or "").strip()
        if not city_clean:
            await interaction.response.send_message(
                "Please provide a city name. Example: `/weather London`",
                ephemeral=True
            )
            return

        # Use threads for blocking urllib calls (keeps the bot responsive).
        geo = await asyncio.to_thread(geocode_city, city_clean)
        if not geo:
            await interaction.response.send_message(
                f"City not found: '{city_clean}'. Try a more specific name (e.g., include region/country).",
                ephemeral=True
            )
            return

        # Primary: Open‑Meteo
        fc = None
        try:
            fc = await asyncio.to_thread(fetch_forecast, geo.latitude, geo.longitude, timezone=geo.timezone or "auto", days=3)
        except Exception:
            fc = None

        # Optional: BBC enrichment (only if mapped)
        loc_id = BBC_MAP.get(city_clean.lower())
        bbc = await asyncio.to_thread(fetch_bbc_rss_by_location_id, loc_id) if loc_id else None

        if not fc:
            # Hard fallback: BBC only if mapped
            if bbc:
                embed = discord.Embed(title=bbc.get("title") or f"BBC Weather — {city_clean}")
                embed.description = bbc.get("description") or ""
                for it in (bbc.get("items") or [])[:3]:
                    if it.get("title"):
                        embed.add_field(name=it["title"], value=it.get("description") or "—", inline=False)
                embed.set_footer(text="Source: BBC Weather RSS (fallback)")
                await interaction.response.send_message(embed=embed)
                return

            await interaction.response.send_message("Weather providers are temporarily unavailable.", ephemeral=True)
            return

        place = _place_label(geo)
        embed = build_weather_embed_card_system_v2(
            place_label=place,
            forecast=fc,
            bbc_items=(bbc.get("items") if bbc else None),
            source_footer=("Open‑Meteo (UKMO/UKV where available)" if not bbc else "Open‑Meteo + BBC RSS"),
        )

        async def refresh_cb():
            return await asyncio.to_thread(fetch_forecast, geo.latitude, geo.longitude, timezone=geo.timezone or "auto", days=3)

        view = WeatherDetailsView(forecast=fc, refresh_cb=refresh_cb)
        await interaction.response.send_message(embed=embed, view=view)

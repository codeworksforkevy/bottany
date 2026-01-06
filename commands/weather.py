# commands/weather.py
from __future__ import annotations

import os
from typing import Optional, Dict, Any

import aiohttp
import discord
from discord import app_commands


def _get_api_key() -> Optional[str]:
    # Set this on Railway as an environment variable:
    # OPENWEATHER_API_KEY = "..."
    return os.getenv("OPENWEATHER_API_KEY")


def _safe_city(city: str) -> str:
    return (city or "").strip()


def _mk_embed(city_label: str, data: Dict[str, Any]) -> discord.Embed:
    name = data.get("name") or city_label
    weather_list = data.get("weather") or []
    main = data.get("main") or {}
    wind = data.get("wind") or {}

    desc = ""
    if isinstance(weather_list, list) and weather_list:
        desc = str(weather_list[0].get("description") or "").title()

    e = discord.Embed(title=f"Weather — {name}", description=desc or "—")

    # Temperatures
    temp = main.get("temp")
    feels = main.get("feels_like")
    if temp is not None:
        e.add_field(name="Temperature", value=f"{temp} °C", inline=True)
    if feels is not None:
        e.add_field(name="Feels like", value=f"{feels} °C", inline=True)

    # Humidity / pressure
    humidity = main.get("humidity")
    pressure = main.get("pressure")
    if humidity is not None:
        e.add_field(name="Humidity", value=f"{humidity}%", inline=True)
    if pressure is not None:
        e.add_field(name="Pressure", value=f"{pressure} hPa", inline=True)

    # Wind
    wind_speed = wind.get("speed")
    if wind_speed is not None:
        e.add_field(name="Wind", value=f"{wind_speed} m/s", inline=True)

    # Optional: show provider note
    e.set_footer(text="Source: OpenWeather (current conditions)")
    return e


async def _fetch_openweather_current(city: str, api_key: str) -> Dict[str, Any]:
    # Current weather endpoint (simple and reliable)
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": api_key,
        "units": "metric",
    }

    timeout = aiohttp.ClientTimeout(total=12)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, params=params) as resp:
            # Return structured error data for better messages
            if resp.status != 200:
                try:
                    payload = await resp.json()
                except Exception:
                    payload = {"message": await resp.text()}
                return {"_error": True, "status": resp.status, "payload": payload}
            return await resp.json()


def register_weather(bot: discord.Client, DATA_DIR: str) -> None:
    """
    Registers:
      /weather today <city>

    Notes:
    - Requires OPENWEATHER_API_KEY environment variable.
    - Uses defer + followup to avoid interaction timeouts.
    """

    weather_group = app_commands.Group(
        name="weather",
        description="Weather information",
    )

    @weather_group.command(name="today", description="Show today's weather for a city.")
    @app_commands.describe(city="City name (e.g., Berlin, Ankara)")
    async def today(interaction: discord.Interaction, city: str):
        city_clean = _safe_city(city)
        if not city_clean:
            await interaction.response.send_message("Please provide a city name.", ephemeral=True)
            return

        # Always defer to avoid the 3s interaction window
        await interaction.response.defer()

        api_key = _get_api_key()
        if not api_key:
            await interaction.followup.send(
                "Weather is not configured: missing `OPENWEATHER_API_KEY` environment variable.",
                ephemeral=True,
            )
            return

        try:
            data = await _fetch_openweather_current(city_clean, api_key)

            if data.get("_error"):
                status = data.get("status")
                payload = data.get("payload") or {}
                msg = payload.get("message") or "Unknown error"

                # Common user-facing cases
                if status == 404:
                    await interaction.followup.send(
                        f"I couldn't find **{city_clean}**. Try a different spelling (or include country like `Berlin,DE`).",
                        ephemeral=True,
                    )
                    return

                await interaction.followup.send(
                    f"Weather API error (HTTP {status}): {msg}",
                    ephemeral=True,
                )
                return

            embed = _mk_embed(city_clean, data)
            await interaction.followup.send(embed=embed)

        except asyncio.TimeoutError:  # type: ignore[name-defined]
            await interaction.followup.send(
                "Weather request timed out. Please try again.",
                ephemeral=True,
            )
        except Exception as e:
            await interaction.followup.send(
                f"Weather error: `{type(e).__name__}: {e}`",
                ephemeral=True,
            )

    bot.tree.add_command(weather_group)

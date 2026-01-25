from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any
import urllib.parse
import urllib.request
import json

@dataclass
class GeoResult:
    name: str
    country: Optional[str]
    admin1: Optional[str]
    latitude: float
    longitude: float
    timezone: Optional[str]

def _http_get_json(url: str, timeout: int = 12) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "BottanyWeather/2.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def geocode_city(city: str, *, count: int = 1) -> Optional[GeoResult]:
    q = urllib.parse.quote((city or "").strip())
    if not q:
        return None
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={q}&count={count}&language=en&format=json"
    data = _http_get_json(url)
    results = data.get("results") or []
    if not results:
        return None
    top = results[0]
    return GeoResult(
        name=top.get("name") or city,
        country=top.get("country"),
        admin1=top.get("admin1"),
        latitude=float(top["latitude"]),
        longitude=float(top["longitude"]),
        timezone=top.get("timezone"),
    )

def fetch_forecast(lat: float, lon: float, *, timezone: str = "auto", days: int = 3) -> Dict[str, Any]:
    """
    Open-Meteo forecast with richer metrics for an advanced Discord embed UI.
    - current: weather_code, humidity, pressure, cloud cover, visibility, uv
    - hourly: next-hours detail panel
    - daily: 72h outlook card with codes, precip prob max, uv max
    """
    days = max(1, min(int(days), 7))
    tz = urllib.parse.quote(timezone or "auto")
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current="
        "temperature_2m,apparent_temperature,weather_code,precipitation,wind_speed_10m,wind_direction_10m,"
        "relative_humidity_2m,pressure_msl,cloud_cover,visibility,uv_index"
        "&hourly="
        "temperature_2m,apparent_temperature,precipitation_probability,precipitation,weather_code,"
        "wind_speed_10m,wind_direction_10m,cloud_cover,relative_humidity_2m,pressure_msl,visibility,uv_index"
        "&daily="
        "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,"
        "wind_speed_10m_max,weather_code,uv_index_max"
        f"&forecast_days={days}"
        f"&timezone={tz}"
    )
    return _http_get_json(url)

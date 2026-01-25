from __future__ import annotations
import os, json, logging
from typing import Any, Optional, List
import aiohttp
import discord
from discord import app_commands

logger = logging.getLogger("bottany.weather_metoffice")

DATAPOINT_BASE = "http://datapoint.metoffice.gov.uk/public/data"

def _load(path: str, default: Optional[dict]=None) -> dict:
    if not os.path.exists(path):
        return default or {}
    with open(path,"r",encoding="utf-8") as f:
        return json.load(f)

async def _get_json(url: str, timeout: int = 20) -> dict:
    async with aiohttp.ClientSession() as s:
        async with s.get(url, timeout=timeout) as r:
            if r.status != 200:
                txt = await r.text()
                raise RuntimeError(f"Met Office DataPoint error {r.status}: {txt[:200]}")
            return await r.json()

def _safe_int(x, default=0):
    try:
        return int(x)
    except Exception:
        return default

def _parse_daily(data: dict) -> list[dict]:
    """
    Parse DataPoint daily site forecast response into list:
    {date, day: {Wx, F, S, ...}, night: {...}}
    """
    out = []
    loc = (((data.get("SiteRep") or {}).get("DV") or {}).get("Location") or {})
    periods = loc.get("Period") or []
    if isinstance(periods, dict):
        periods = [periods]
    for p in periods:
        d = (p.get("value","") or "").replace("Z","")
        reps = p.get("Rep") or []
        if isinstance(reps, dict):
            reps = [reps]
        day = None
        night = None
        for r in reps:
            # In daily feed, Rep has "D" field for day/night, but can vary; we infer using '$' time offset: 0=day, 720=night
            t = _safe_int(r.get("$",0),0)
            if t == 0:
                day = r
            elif t >= 720:
                night = r
        out.append({"date": d, "day": day or {}, "night": night or {}})
    return out

def register_weather_metoffice(bot, data_dir: str) -> None:
    api_key = (os.getenv("METOFFICE_API_KEY","") or "").strip()
    sites_cache_path = os.path.join(data_dir, "metoffice_sites_cache.json")
    sites_cache = _load(sites_cache_path, default={"sites": [], "updated_utc": ""})
    sites = sites_cache.get("sites", []) or []

    weather_group = app_commands.Group(name="weather", description="Weather (Met Office DataPoint; official).")

    @weather_group.command(name="metoffice_site", description="Met Office daily forecast by site ID (UK DataPoint).")
    @app_commands.describe(site_id="Met Office site ID (from DataPoint sitelist)", days="How many days (1-5)")
    async def metoffice_site(interaction: discord.Interaction, site_id: str, days: int = 3):
        if not api_key:
            await interaction.response.send_message("Missing METOFFICE_API_KEY. Add it as an environment variable.", ephemeral=True)
            return
        sid = (site_id or "").strip()
        if not sid.isdigit():
            await interaction.response.send_message("site_id must be numeric (DataPoint site ID).", ephemeral=True)
            return
        n = max(1, min(5, int(days or 3)))
        url = f"{DATAPOINT_BASE}/val/wxfcs/all/json/{sid}?res=daily&key={api_key}"
        try:
            data = await _get_json(url)
            days_list = _parse_daily(data)[:n]
            loc = (((data.get("SiteRep") or {}).get("DV") or {}).get("Location") or {})
            name = loc.get("name") or loc.get("i") or f"Site {sid}"
            lat = loc.get("lat")
            lon = loc.get("lon")
            e = discord.Embed(title=f"Met Office forecast — {name}")
            if lat and lon:
                e.description = f"Site {sid} • {lat}, {lon}"
            for d in days_list:
                date_str = d.get("date","")
                day = d.get("day",{}) or {}
                night = d.get("night",{}) or {}
                # DataPoint uses codes; we show key ones
                line = []
                if day.get("Dm") or day.get("Nm"):
                    line.append(f"Temp: {day.get('Dm','?')}°C (day) / {night.get('Nm','?')}°C (night)")
                if day.get("PPd") or night.get("PPn"):
                    line.append(f"Precip prob: {day.get('PPd','?')}% (day) / {night.get('PPn','?')}% (night)")
                if day.get("S"):
                    line.append(f"Wind: {day.get('S')} mph dir {day.get('D','?')}")
                e.add_field(name=date_str or "Day", value="\n".join(line)[:1024] if line else "(no data)", inline=False)
            e.set_footer(text="Source: Met Office DataPoint (UK site-specific daily forecast)")
            await interaction.response.send_message(embed=e)
        except Exception as ex:
            await interaction.response.send_message(f"Met Office request failed: {ex}", ephemeral=True)

    @weather_group.command(name="metoffice_find", description="Find a Met Office DataPoint site in the local cache.")
    @app_commands.describe(query="City/town substring (requires metoffice_sites_cache.json)")
    async def metoffice_find(interaction: discord.Interaction, query: str):
        q = (query or "").strip().lower()
        if not q:
            await interaction.response.send_message("Provide a query.", ephemeral=True)
            return
        if not sites:
            await interaction.response.send_message(
                "No local cache yet. Run scripts/update_metoffice_sites_cache.py to generate metoffice_sites_cache.json.",
                ephemeral=True
            )
            return
        hits = [s for s in sites if q in (s.get("name","").lower())]
        if not hits:
            await interaction.response.send_message("No matches in the cache.", ephemeral=True)
            return
        e = discord.Embed(title="Met Office sites (cache)")
        for s in hits[:10]:
            e.add_field(name=s.get("name","Site"), value=f"ID: `{s.get('id')}` • {s.get('country','UK')}", inline=False)
        if len(hits) > 10:
            e.set_footer(text=f"+ {len(hits)-10} more")
        await interaction.response.send_message(embed=e, ephemeral=True)

    bot.tree.add_command(weather_group)

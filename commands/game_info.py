import os
import json
from typing import Optional, Dict, Any

import aiohttp
import discord
from discord import app_commands

async def _steam_appdetails(session: aiohttp.ClientSession, appid: int) -> Optional[Dict[str, Any]]:
    url = "https://store.steampowered.com/api/appdetails"
    params = {"appids": str(appid), "l": "en"}
    async with session.get(url, params=params, timeout=20) as resp:
        if resp.status != 200:
            return None
        data = await resp.json()
        x = data.get(str(appid))
        if not x or not x.get("success"):
            return None
        return x.get("data")

class GameInfoGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="game", description="Game info cards (Steam + official search links)")

    @app_commands.command(name="info", description="Game info card: Steam (appid) + official search links")
    @app_commands.describe(query="Steam appid (number) or game name")
    async def info(self, interaction: discord.Interaction, query: str):
        q = (query or "").strip()
        if not q:
            await interaction.response.send_message("Provide a Steam appid (number) or a game name.", ephemeral=True)
            return

        # Determine if appid
        appid = None
        if q.isdigit():
            try:
                appid = int(q)
            except Exception:
                appid = None

        steam_url = None
        title = q
        desc = ""
        fields = []

        if appid:
            steam_url = f"https://store.steampowered.com/app/{appid}/"
            async with aiohttp.ClientSession() as session:
                data = await _steam_appdetails(session, appid)
            if data:
                title = data.get("name") or title
                short = data.get("short_description") or ""
                if short:
                    desc = short
                genres = ", ".join([g.get("description") for g in (data.get("genres") or []) if g.get("description")][:4])
                if genres:
                    fields.append(("Genres", genres, True))
                developers = ", ".join((data.get("developers") or [])[:3])
                if developers:
                    fields.append(("Developers", developers, True))
                publishers = ", ".join((data.get("publishers") or [])[:3])
                if publishers:
                    fields.append(("Publishers", publishers, True))
                price = data.get("price_overview", {})
                if price and price.get("final_formatted"):
                    fields.append(("Price", price.get("final_formatted"), True))

        # Official entry points (no scraping)
        # Metacritic and HowLongToBeat have no official APIs we can rely on.
        name_for_search = title
        import urllib.parse
        enc = urllib.parse.quote(name_for_search)
        steam_search = f"https://store.steampowered.com/search/?term={enc}"
        metacritic_search = f"https://www.metacritic.com/search/all/{enc}/results"
        hltb_search = f"https://howlongtobeat.com/?q={enc}"

        embed = discord.Embed(title=title[:256], description=(desc or "").strip()[:4096])
        if steam_url:
            embed.add_field(name="Steam", value=steam_url, inline=False)
        else:
            embed.add_field(name="Steam search", value=steam_search, inline=False)

        embed.add_field(name="Metacritic search", value=metacritic_search, inline=False)
        embed.add_field(name="HowLongToBeat search", value=hltb_search, inline=False)

        for n,v,i in fields:
            embed.add_field(name=n, value=v, inline=i)

        embed.set_footer(text="Steam details via Steam store API when appid is provided. Other links are official search entry points.")
        await interaction.response.send_message(embed=embed)

async def register_game_info(bot: discord.Client, data_dir: str) -> None:
    bot.tree.add_command(GameInfoGroup())
    await bot.tree.sync()

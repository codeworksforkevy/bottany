import os
import re
import requests
import discord
from discord import app_commands

# Gaming-only query + post-filter to prevent sports bleed-through.
GAMING_QUERY = (
    '(video game OR videogame OR gaming OR "PC game" OR console OR PlayStation OR Xbox OR Nintendo OR Steam OR '
    '"game update" OR "game release" OR "game trailer" OR "patch notes")'
)

GAMING_TERMS_RE = re.compile(
    r'\b(game|gaming|videogame|video game|pc|steam|playstation|xbox|nintendo|switch|ps5|ps4|'
    r'console|rpg|fps|mmorpg|indie|dlc|patch|trailer)\b',
    re.I
)

SPORTS_TERMS_RE = re.compile(
    r'\b(football|soccer|nba|nfl|mlb|nhl|cricket|tennis|rugby|golf|formula 1|f1|'
    r'uefa|fifa|champions league|premier league|la liga|bundesliga|serie a)\b',
    re.I
)

DEFAULT_DOMAINS = [
    "ign.com","gamespot.com","pcgamer.com","eurogamer.net","rockpapershotgun.com","polygon.com",
    "kotaku.com","destructoid.com","vg247.com","nintendolife.com",
    "theverge.com","arstechnica.com","wired.com"
]

def _fetch_news(api_key: str, limit: int = 8):
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": GAMING_QUERY,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": min(max(limit, 1), 20),
        "domains": ",".join(DEFAULT_DOMAINS),
    }
    r = requests.get(url, params=params, headers={"X-Api-Key": api_key}, timeout=20)
    r.raise_for_status()
    return r.json().get("articles", [])

def _filter_articles(articles):
    out = []
    for a in articles:
        title = (a.get("title") or "").strip()
        desc = (a.get("description") or "").strip()
        blob = f"{title}\n{desc}"
        if not GAMING_TERMS_RE.search(blob):
            continue
        if SPORTS_TERMS_RE.search(blob):
            continue
        out.append(a)
    return out

def register_gaming_news(tree: app_commands.CommandTree, data_dir: str):
    @app_commands.command(name="gamingnews", description="Latest PC/console gaming news (gaming-only)")
    async def gamingnews(interaction: discord.Interaction):
        api_key = os.getenv("NEWSAPI_KEY")
        if not api_key:
            await interaction.response.send_message("Missing NEWSAPI_KEY on the host.", ephemeral=True)
            return

        try:
            raw = _fetch_news(api_key, limit=10)
            articles = _filter_articles(raw)[:6]
        except Exception as e:
            await interaction.response.send_message(f"Unable to fetch gaming news: {e}", ephemeral=True)
            return

        if not articles:
            await interaction.response.send_message("No gaming-only items found right now.", ephemeral=True)
            return

        embed = discord.Embed(
            title="Gaming News (PC/Console)",
            description="Filtered to avoid sports/news drift (domains + keywords)."
        )
        for a in articles:
            t = (a.get("title") or "Untitled").strip()
            u = (a.get("url") or "").strip()
            src = (a.get("source") or {}).get("name") or "Source"
            embed.add_field(name=src, value=f"[{t}]({u})" if u else t, inline=False)

        embed.set_footer(text="Set NEWSAPI_KEY in Railway variables.")
        await interaction.response.send_message(embed=embed, ephemeral=False)

    existing = [c.name for c in tree.get_commands()]
    if "gamingnews" not in existing:
        tree.add_command(gamingnews)

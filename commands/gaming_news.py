"""
Gaming news module with three ingestion options:
1) NewsAPI (licensed aggregator) via NEWSAPI_KEY env var
2) RSS/Atom feeds from an allowlisted set (data/news_sources_allowlist.json)
3) "Allowlisted sites" mode (placeholder): you can add your own parsers later

Slash command: /gamingnews query:<text> mode:<newsapi|rss> visibility:<public|ephemeral>

This module is intentionally conservative: it only reads from known sources,
and keeps snippets short.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from bs4 import BeautifulSoup

BABY_BLUE = 0x89CFF0

def _load_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def _visibility_to_ephemeral(visibility: Optional[str]) -> bool:
    return (visibility or "public").lower().strip() != "public"

async def _fetch_newsapi(session: aiohttp.ClientSession, api_key: str, query: str, page_size: int = 6) -> List[Dict[str, Any]]:
    # NewsAPI v2 Everything endpoint
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": str(max(1, min(page_size, 10))),
    }
    headers = {"X-Api-Key": api_key}
    async with session.get(url, params=params, headers=headers, timeout=20) as r:
        if r.status != 200:
            return []
        data = await r.json(content_type=None)
    return (data or {}).get("articles", []) or []

async def _fetch_rss(session: aiohttp.ClientSession, feed_url: str, timeout_s: int = 20) -> List[Dict[str, Any]]:
    async with session.get(feed_url, timeout=timeout_s, headers={"User-Agent": "Mozilla/5.0"}) as r:
        if r.status != 200:
            return []
        xml = await r.text()
    soup = BeautifulSoup(xml, "xml")
    items = []
    for it in soup.find_all(["item", "entry"])[:10]:
        title = (it.title.get_text(strip=True) if it.title else "").strip()
        link = ""
        if it.link:
            # RSS: <link>text</link>, Atom: <link href="..."/>
            link = (it.link.get_text(strip=True) or "").strip() or (it.link.get("href") or "").strip()
        pub = ""
        if it.pubDate:
            pub = it.pubDate.get_text(strip=True)
        elif it.published:
            pub = it.published.get_text(strip=True)
        elif it.updated:
            pub = it.updated.get_text(strip=True)
        summary = ""
        if it.description:
            summary = it.description.get_text(" ", strip=True)
        elif it.summary:
            summary = it.summary.get_text(" ", strip=True)
        items.append({"title": title, "url": link, "published": pub, "summary": summary})
    return items

def _build_embed(items: List[Dict[str, Any]], title: str) -> discord.Embed:
    emb = discord.Embed(title=title, color=BABY_BLUE, timestamp=datetime.utcnow())
    if not items:
        emb.description = "No items returned."
        return emb
    lines = []
    for a in items[:6]:
        t = (a.get("title") or "").strip()
        u = (a.get("url") or a.get("link") or "").strip()
        if not t:
            continue
        if u:
            lines.append(f"• **[{t}]({u})**")
        else:
            lines.append(f"• **{t}**")
    emb.description = "\n".join(lines)[:4000]
    return emb

class GamingNewsCog(commands.Cog):
    def __init__(self, bot: commands.Bot, data_dir: str):
        self.bot = bot
        self.data_dir = data_dir
        self.allowlist_path = os.path.join(data_dir, "news_sources_allowlist.json")
        self.allowlist = _load_json(self.allowlist_path, {"rss_feeds": []})

    news = app_commands.Group(name="gamingnews", description="Gaming news via NewsAPI or allowlisted RSS feeds.")

    @news.command(name="latest", description="Fetch latest gaming news.")
    @app_commands.describe(
        query="Search query (default: video game)",
        mode="newsapi (requires NEWSAPI_KEY) or rss",
        visibility="public (default) or ephemeral",
    )
    async def latest(self, interaction: discord.Interaction, query: Optional[str] = "video game", mode: Optional[str] = "rss", visibility: Optional[str] = "public"):
        ephemeral = _visibility_to_ephemeral(visibility)
        await interaction.response.defer(thinking=True, ephemeral=ephemeral)

        mode = (mode or "rss").lower().strip()
        query = (query or "video game").strip()

        async with aiohttp.ClientSession() as session:
            if mode == "newsapi":
                key = os.getenv("NEWSAPI_KEY", "").strip()
                if not key:
                    await interaction.followup.send("NEWSAPI_KEY is missing. Set it in Railway Variables / local .env.", ephemeral=True)
                    return
                articles = await _fetch_newsapi(session, key, query, page_size=6)
                items = []
                for a in articles:
                    items.append({"title": a.get("title"), "url": a.get("url"), "published": a.get("publishedAt"), "summary": a.get("description")})
                emb = _build_embed(items, title=f"Gaming news (NewsAPI): {query}")
                await interaction.followup.send(embed=emb, ephemeral=ephemeral)
                return

            # RSS mode
            feeds: List[Dict[str, Any]] = self.allowlist.get("rss_feeds", [])
            if not feeds:
                await interaction.followup.send("RSS allowlist is empty. Add feeds to data/news_sources_allowlist.json.", ephemeral=True)
                return

            merged: List[Dict[str, Any]] = []
            for f in feeds[:8]:
                url = (f.get("url") or "").strip()
                if not url:
                    continue
                items = await _fetch_rss(session, url)
                for it in items:
                    it["source"] = f.get("name") or url
                    merged.append(it)

            # Keep it simple: just take first N after merge; (optional) you can sort later by parsed date.
            emb = _build_embed(merged[:6], title=f"Gaming news (RSS allowlist): {query}")
            await interaction.followup.send(embed=emb, ephemeral=ephemeral)

async def register_gaming_news(bot: commands.Bot, data_dir: str) -> None:
    cog = GamingNewsCog(bot, data_dir)
    await bot.add_cog(cog)
    try:
        bot.tree.add_command(cog.news)
    except Exception:
        pass

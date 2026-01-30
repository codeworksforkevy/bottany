# commands/gaming_news.py
from __future__ import annotations

import os
import json
import datetime as dt
from typing import Any, Dict, List, Optional

import discord
import aiohttp


NEWS_COLOR = 0x8EC5FF  # baby blue (matches your UX request)


def _load_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


async def _fetch_newsapi(session: aiohttp.ClientSession, api_key: str, q: str, page_size: int = 5) -> List[Dict[str, Any]]:
    # NewsAPI.org endpoint (top headlines or everything). Keep it simple + safe.
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": q,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": int(page_size),
    }
    headers = {"X-Api-Key": api_key}
    async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as r:
        r.raise_for_status()
        data = await r.json()
    return data.get("articles", []) or []


def register_gaming_news(client: discord.Client, tree: discord.app_commands.CommandTree, data_dir: str) -> None:
    """
    Register /gamingnews without using cogs (works with discord.Client).
    Expects NEWSAPI_KEY in environment. Optional config at data/news_registry.json.
    """

    @tree.command(name="gamingnews", description="Fetch latest gaming news via NewsAPI (licensed aggregator).")
    async def gamingnews(interaction: discord.Interaction, query: Optional[str] = "video games"):
        api_key = os.getenv("NEWSAPI_KEY", "").strip()
        if not api_key:
            await interaction.response.send_message("Missing NEWSAPI_KEY env var.", ephemeral=True)
            return

        await interaction.response.defer(thinking=False)
        reg = _load_json(os.path.join(data_dir, "news_registry.json"), {})
        page_size = int(reg.get("page_size", 5))

        async with aiohttp.ClientSession() as session:
            try:
                arts = await _fetch_newsapi(session, api_key=api_key, q=(query or "video games"), page_size=page_size)
            except Exception as e:
                await interaction.followup.send(f"News fetch failed: {type(e).__name__}: {e}", ephemeral=True)
                return

        if not arts:
            await interaction.followup.send("No news results right now.", ephemeral=False)
            return

        now_utc = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
        # One embed with multiple items (clean UX, avoids spam)
        e = discord.Embed(
            title="Gaming news",
            description=f"Query: **{query}**",
            color=NEWS_COLOR,
        )

        lines: List[str] = []
        for a in arts[:page_size]:
            title = (a.get("title") or "").strip()
            url = (a.get("url") or "").strip()
            source = (a.get("source") or {}).get("name") or "NewsAPI"
            published = (a.get("publishedAt") or "")[:10]  # YYYY-MM-DD
            if url:
                lines.append(f"• [{title}]({url}) — *{source}* ({published})")
            else:
                lines.append(f"• {title} — *{source}* ({published})")

        e.add_field(name="Latest", value="\n".join(lines), inline=False)
        e.set_footer(text=f"UTC day: {now_utc} • via NewsAPI")
        await interaction.followup.send(embed=e, ephemeral=False)

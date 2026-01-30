# commands/gaming_news.py
from __future__ import annotations

import os
import json
import datetime as dt
from typing import Any, Dict, List, Optional, Tuple

import discord
import aiohttp


NEWS_COLOR = 0x8EC5FF  # baby blue (matches your UX request)

# Discord embed limits (hard)
_FIELD_VALUE_LIMIT = 1024
_TITLE_LIMIT = 256
_DESC_LIMIT = 4096


def _clamp(text: str, limit: int) -> str:
    """Clamp text to a hard character limit (Discord-safe)."""
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + "…"


def _load_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


async def _fetch_newsapi(
    session: aiohttp.ClientSession,
    api_key: str,
    q: str,
    page_size: int = 10,
    sources_csv: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    NewsAPI.org endpoint (Everything). Keep it simple + safe.
    docs: https://newsapi.org/docs/endpoints/everything
    """
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": q,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": int(page_size),
    }
    # Optional: limit sources (comma-separated NewsAPI source IDs)
    if sources_csv:
        params["sources"] = sources_csv

    headers = {"X-Api-Key": api_key}
    async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as r:
        r.raise_for_status()
        data = await r.json()
    return data.get("articles", []) or []


def _chunk(items: List[Any], size: int) -> List[List[Any]]:
    if size <= 0:
        return [items]
    return [items[i : i + size] for i in range(0, len(items), size)]


def _normalize_sources(raw: Optional[str]) -> Optional[str]:
    """
    Accepts:
      - "ign, polygon, kotaku" (user input)
    Returns NewsAPI 'sources' csv:
      - "ign,polygon,kotaku"
    Notes:
      - These are NewsAPI source IDs, not domains.
      - If you want domains instead, switch to 'domains' param in _fetch_newsapi.
    """
    if not raw:
        return None
    parts = [p.strip().lower() for p in raw.split(",") if p.strip()]
    if not parts:
        return None
    # Deduplicate + cap to reduce 400s
    dedup = []
    seen = set()
    for p in parts:
        if p not in seen:
            seen.add(p)
            dedup.append(p)
    return ",".join(dedup[:20])


def _article_line(a: Dict[str, Any], compact: bool) -> str:
    title = _clamp((a.get("title") or "").strip(), 140)
    url = (a.get("url") or "").strip()
    source = (a.get("source") or {}).get("name") or "NewsAPI"
    published = (a.get("publishedAt") or "")[:10]  # YYYY-MM-DD
    desc = (a.get("description") or "").strip()

    if compact:
        if url:
            return f"• [{title}]({url}) — *{source}* ({published})"
        return f"• {title} — *{source}* ({published})"

    # Non-compact: add a short description snippet (kept small to avoid 1024 issues)
    snippet = _clamp(desc.replace("\n", " "), 160) if desc else ""
    if url:
        if snippet:
            return f"• [{title}]({url}) — {snippet} — *{source}* ({published})"
        return f"• [{title}]({url}) — *{source}* ({published})"
    if snippet:
        return f"• {title} — {snippet} — *{source}* ({published})"
    return f"• {title} — *{source}* ({published})"


def _make_embed(query: str, page_lines: List[str], page_idx: int, page_count: int) -> discord.Embed:
    e = discord.Embed(
        title=_clamp("Gaming news", _TITLE_LIMIT),
        description=_clamp(f"Query: **{query}**", _DESC_LIMIT),
        color=NEWS_COLOR,
    )
    value = _clamp("\n".join(page_lines), _FIELD_VALUE_LIMIT)
    e.add_field(name="Latest", value=value, inline=False)

    now_utc = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    e.set_footer(text=f"UTC day: {now_utc} • Page {page_idx + 1}/{page_count} • via NewsAPI")
    return e


class _Pager(discord.ui.View):
    def __init__(self, query: str, pages: List[List[str]]):
        super().__init__(timeout=15 * 60)  # 15 minutes
        self.query = query
        self.pages = pages
        self.i = 0

        # Disable buttons if only one page
        if len(self.pages) <= 1:
            for child in self.children:
                if isinstance(child, discord.ui.Button):
                    child.disabled = True

    def current_embed(self) -> discord.Embed:
        return _make_embed(self.query, self.pages[self.i], self.i, len(self.pages))

    async def on_timeout(self) -> None:
        # Disable buttons when view expires
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

    @discord.ui.button(label="Prev", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.i = (self.i - 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.current_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.i = (self.i + 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.current_embed(), view=self)


def register_gaming_news(client: discord.Client, tree: discord.app_commands.CommandTree, data_dir: str) -> None:
    """
    Register /gamingnews without using cogs (works with discord.Client).
    Expects NEWSAPI_KEY in environment. Optional config at data/news_registry.json.

    New UX:
      - compact: short bullet list
      - sources: comma-separated NewsAPI source IDs
      - pagination: Prev/Next buttons if results exceed one page
    """

    @tree.command(name="gamingnews", description="Fetch latest gaming news via NewsAPI (licensed aggregator).")
    async def gamingnews(
        interaction: discord.Interaction,
        query: Optional[str] = "video games",
        compact: Optional[bool] = False,
        sources: Optional[str] = None,
    ):
        api_key = os.getenv("NEWSAPI_KEY", "").strip()
        if not api_key:
            await interaction.response.send_message("Missing NEWSAPI_KEY env var.", ephemeral=True)
            return

        await interaction.response.defer(thinking=False)

        reg = _load_json(os.path.join(data_dir, "news_registry.json"), {})
        # Fetch more than you display; you'll paginate locally.
        fetch_n = int(reg.get("fetch_size", 15))
        fetch_n = max(5, min(fetch_n, 50))

        per_page = int(reg.get("page_size", 5))
        per_page = max(3, min(per_page, 10))

        q = (query or "video games").strip()
        src_csv = _normalize_sources(sources)

        async with aiohttp.ClientSession() as session:
            try:
                arts = await _fetch_newsapi(session, api_key=api_key, q=q, page_size=fetch_n, sources_csv=src_csv)
            except Exception as e:
                await interaction.followup.send(f"News fetch failed: {type(e).__name__}: {e}", ephemeral=True)
                return

        if not arts:
            await interaction.followup.send("No news results right now.", ephemeral=False)
            return

        # Build bullet lines with strict safety
        lines: List[str] = []
        for a in arts:
            line = _article_line(a, compact=bool(compact))
            lines.append(line)

        # Chunk into pages and ensure each page is safely under 1024 even in worst cases
        raw_pages = _chunk(lines, per_page)

        safe_pages: List[List[str]] = []
        for page in raw_pages:
            # Guard: shrink page if the joined text would overflow 1024.
            cur: List[str] = []
            for ln in page:
                trial = ("\n".join(cur + [ln])).strip()
                if len(trial) <= _FIELD_VALUE_LIMIT:
                    cur.append(ln)
                else:
                    # If even a single line is too long (shouldn't happen due to clamping),
                    # clamp harder and accept it.
                    if not cur:
                        cur.append(_clamp(ln, _FIELD_VALUE_LIMIT))
                    break
            safe_pages.append(cur if cur else [_clamp("\n".join(page), _FIELD_VALUE_LIMIT)])

        view = _Pager(query=q, pages=safe_pages)
        await interaction.followup.send(embed=view.current_embed(), view=view, ephemeral=False)

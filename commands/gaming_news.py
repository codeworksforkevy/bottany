from __future__ import annotations

import re
import logging
import xml.etree.ElementTree as ET

import discord
from discord import app_commands

log = logging.getLogger(__name__)

try:
    import aiohttp
except ImportError:
    aiohttp = None  # type: ignore

# ── Source registry ────────────────────────────────────────────────────────────

SOURCES = {
    "ign": {
        "label": "IGN",
        "url":   "https://feeds.feedburner.com/ign/games-all",
        "color": 0xE31E24,
        "kind":  "news",
        "icon":  "IGN",
    },
    "eurogamer": {
        "label": "Eurogamer",
        "url":   "https://www.eurogamer.net/?format=rss",
        "color": 0x00A859,
        "kind":  "news",
        "icon":  "EUR",
    },
    "rps": {
        "label": "Rock Paper Shotgun",
        "url":   "https://www.rockpapershotgun.com/feed",
        "color": 0xE8C840,
        "kind":  "review",
        "icon":  "RPS",
    },
    "rps_reviews": {
        "label": "RPS — Reviews",
        "url":   "https://www.rockpapershotgun.com/feed/reviews",
        "color": 0xE8C840,
        "kind":  "review",
        "icon":  "RPS",
    },
    "pcgamer": {
        "label": "PC Gamer",
        "url":   "https://www.pcgamer.com/rss/",
        "color": 0x0072CE,
        "kind":  "news",
        "icon":  "PCG",
    },
    "kotaku": {
        "label": "Kotaku",
        "url":   "https://kotaku.com/rss",
        "color": 0x00ADB5,
        "kind":  "news",
        "icon":  "KTK",
    },
    "gamespot": {
        "label": "GameSpot",
        "url":   "https://www.gamespot.com/feeds/mashup/",
        "color": 0xFF6600,
        "kind":  "review",
        "icon":  "GSP",
    },
    "vg247": {
        "label": "VG247",
        "url":   "https://www.vg247.com/feed/",
        "color": 0x5A2D82,
        "kind":  "news",
        "icon":  "VG2",
    },
    "polygon": {
        "label": "Polygon",
        "url":   "https://www.polygon.com/rss/index.xml",
        "color": 0xFF4713,
        "kind":  "review",
        "icon":  "PLY",
    },
}

# ── RSS helpers ────────────────────────────────────────────────────────────────

def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    for ent, rep in [("&amp;","&"),("&lt;","<"),("&gt;",">"),("&quot;",'"'),("&#39;","'"),("&nbsp;"," ")]:
        text = text.replace(ent, rep)
    return re.sub(r"\s+", " ", text).strip()


def _truncate(text: str, limit: int = 200) -> str:
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "..."


def _parse_rss(xml_text: str, limit: int = 5) -> list[dict]:
    items: list[dict] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items

    ns = {"atom": "http://www.w3.org/2005/Atom"}

    for item in root.iter("item"):
        if len(items) >= limit:
            break
        items.append({
            "title":   _strip_html(item.findtext("title") or ""),
            "link":    (item.findtext("link") or "").strip(),
            "summary": _truncate(_strip_html(item.findtext("description") or "")),
            "date":    (item.findtext("pubDate") or "")[:16],
        })

    if not items:
        for entry in root.findall(".//atom:entry", ns) or root.findall(".//entry"):
            if len(items) >= limit:
                break
            title_el = entry.find("atom:title", ns) or entry.find("title")
            link_el  = entry.find("atom:link",  ns) or entry.find("link")
            summ_el  = entry.find("atom:summary", ns) or entry.find("summary")
            date_el  = entry.find("atom:updated", ns) or entry.find("updated")
            items.append({
                "title":   _strip_html(title_el.text if title_el is not None else ""),
                "link":    link_el.get("href", "") if link_el is not None else "",
                "summary": _truncate(_strip_html(summ_el.text if summ_el is not None else "")),
                "date":    (date_el.text if date_el is not None else "")[:16],
            })

    return items


async def _fetch(session, url: str) -> str:
    headers = {"User-Agent": "Bottany-Bot/1.0 (gaming news reader)"}
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as r:
            return await r.text() if r.status == 200 else ""
    except Exception as e:
        log.warning("Feed fetch failed %s: %s", url, e)
        return ""


# ── Embed builders ─────────────────────────────────────────────────────────────

def _source_embed(key: str, items: list[dict]) -> discord.Embed:
    src = SOURCES[key]
    embed = discord.Embed(
        title=f"[ {src['icon']} ]  {src['label']}",
        color=src["color"],
    )
    if not items:
        embed.description = "*Feed unavailable or no articles found.*"
        return embed
    for item in items:
        name  = f"[{item['title']}]({item['link']})" if item["link"] else item["title"]
        value = item["summary"] or "*No summary.*"
        if item["date"]:
            value += f"\n*{item['date']}*"
        embed.add_field(name=name, value=value, inline=False)
    embed.set_footer(text=f"Bottany  ·  {src['label']}")
    return embed


def _digest_embed(results: list[tuple[str, list[dict]]], kind: str) -> discord.Embed:
    kind_label = {"all": "All", "news": "News", "review": "Reviews"}.get(kind, kind)
    embed = discord.Embed(
        title=f"Gaming {kind_label} Digest",
        description=f"*Top headlines from {sum(1 for _, items in results if items)} sources*",
        color=0x2B2D31,
    )
    for key, items in results:
        src = SOURCES[key]
        if not items:
            continue
        lines = []
        for item in items[:2]:
            title = item["title"] or "Untitled"
            link  = item["link"]
            lines.append(f"[{title}]({link})" if link else title)
        embed.add_field(
            name=f"[ {src['icon']} ]  {src['label']}",
            value="\n".join(lines),
            inline=False,
        )
    embed.set_footer(text="Bottany  ·  Gaming News")
    return embed


# ── Registration ───────────────────────────────────────────────────────────────

async def register(bot: discord.Client, data_dir: str) -> None:
    if aiohttp is None:
        log.error("gaming_news: aiohttp not installed — pip install aiohttp")
        return

    if bot.tree.get_command("gamingnews"):
        return

    group = app_commands.Group(
        name="gamingnews",
        description="Latest gaming news and reviews",
    )

    # /gamingnews digest
    @group.command(name="digest", description="Headlines from all sources at once")
    @app_commands.describe(
        kind="Filter by content type (default: all)",
        count="Articles per source, 1–5 (default: 2)",
    )
    @app_commands.choices(kind=[
        app_commands.Choice(name="All",     value="all"),
        app_commands.Choice(name="News",    value="news"),
        app_commands.Choice(name="Reviews", value="review"),
    ])
    async def digest(
        interaction: discord.Interaction,
        kind:  str = "all",
        count: int = 2,
    ) -> None:
        await interaction.response.defer()
        count   = max(1, min(5, count))
        srcs    = {k: v for k, v in SOURCES.items() if kind == "all" or v["kind"] == kind}
        results = []
        async with aiohttp.ClientSession() as session:
            for key, src in srcs.items():
                xml   = await _fetch(session, src["url"])
                items = _parse_rss(xml, limit=count) if xml else []
                results.append((key, items))
        await interaction.followup.send(embed=_digest_embed(results, kind))

    # /gamingnews source
    @group.command(name="source", description="Articles from one specific source")
    @app_commands.describe(
        site="Which source",
        count="Number of articles, 1–5 (default: 4)",
    )
    @app_commands.choices(site=[
        app_commands.Choice(name=v["label"], value=k)
        for k, v in SOURCES.items()
    ])
    async def source_cmd(
        interaction: discord.Interaction,
        site:  str,
        count: int = 4,
    ) -> None:
        await interaction.response.defer()
        count = max(1, min(5, count))
        if site not in SOURCES:
            await interaction.followup.send("Unknown source.", ephemeral=True)
            return
        async with aiohttp.ClientSession() as session:
            xml = await _fetch(session, SOURCES[site]["url"])
        items = _parse_rss(xml, limit=count) if xml else []
        await interaction.followup.send(embed=_source_embed(site, items))

    # /gamingnews sources
    @group.command(name="sources", description="List all tracked sources")
    async def sources_cmd(interaction: discord.Interaction) -> None:
        embed = discord.Embed(title="Tracked Gaming Sources", color=0x2B2D31)
        for key, src in SOURCES.items():
            embed.add_field(
                name=f"[ {src['icon']} ]  {src['label']}",
                value=f"`/gamingnews source {key}`  ·  *{src['kind']}*",
                inline=True,
            )
        embed.set_footer(text="Bottany")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    bot.tree.add_command(group)
    log.info("Registered /gamingnews (digest · source · sources)")

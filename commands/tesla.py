from __future__ import annotations

import asyncio
import logging
import random
from collections import Counter
from typing import Any, Dict, List, Optional

import discord
from discord import app_commands

from services.tesla_archive_service import load_archive
from services.tesla_mit_resolver import resolve_mit_patent_image
from services.tesla_wikimedia_resolver import resolve_wikimedia_patent_image

log = logging.getLogger(__name__)

# ── Autocomplete choices ──────────────────────────────────────────────────────

_CATEGORY_CHOICES = [
    app_commands.Choice(name="Alternating Current",   value="Alternating Current"),
    app_commands.Choice(name="Electric Motor",         value="Electric Motor"),
    app_commands.Choice(name="Electrical Components",  value="Electrical Components"),
    app_commands.Choice(name="Electrical System",      value="Electrical System"),
    app_commands.Choice(name="Lighting",               value="Lighting"),
    app_commands.Choice(name="Power Transmission",     value="Power Transmission"),
    app_commands.Choice(name="Radio Control",          value="Radio Control"),
    app_commands.Choice(name="Wireless Power",         value="Wireless Power"),
]

_IPC_CHOICES = [
    app_commands.Choice(name="H01C — Electrical components", value="H01C"),
    app_commands.Choice(name="H01F — Magnets / inductance",  value="H01F"),
    app_commands.Choice(name="H02K — Electric machines",     value="H02K"),
    app_commands.Choice(name="H02P — Motor control",         value="H02P"),
]


# ── Image resolution ──────────────────────────────────────────────────────────

async def _resolve_image(patent_number: str) -> Optional[str]:
    """
    Try MIT Tesla archive first (curated, higher quality).
    Fall back to Wikimedia Commons if MIT has nothing.
    Returns a URL or None. Never raises — a missing image is not an error.

    Both resolvers run inside a single 10-second timeout so a slow
    network never blocks the interaction.
    """
    try:
        async with asyncio.timeout(10):
            url = await resolve_mit_patent_image(patent_number)
            if url:
                log.debug("MIT image found for patent %s", patent_number)
                return url
            url = await resolve_wikimedia_patent_image(patent_number)
            if url:
                log.debug("Wikimedia image found for patent %s", patent_number)
            return url
    except TimeoutError:
        log.warning("Image resolution timed out for patent %s", patent_number)
        return None
    except Exception as exc:
        log.warning("Image resolution failed for patent %s: %s", patent_number, exc)
        return None


# ── Embed builders ────────────────────────────────────────────────────────────

async def _patent_embed(
    item: Dict[str, Any],
    total: Optional[int] = None,
    with_image: bool = True,
) -> discord.Embed:
    """
    Rich single-patent embed.
    When with_image=True, attempts to attach a patent drawing via MIT / Wikimedia.
    """
    patent_num = item.get("patent_number", "—")
    source_url = item.get("source_url")

    embed = discord.Embed(
        title=f"⚡ {patent_num} — {item.get('title', 'Untitled')}",
        color=0x9C27B0,
    )
    if source_url:
        embed.url = source_url  # clicking the title opens the USPTO PDF

    embed.add_field(name="Year",         value=str(item.get("year", "—")),   inline=True)
    embed.add_field(name="Jurisdiction", value=item.get("jurisdiction", "—"), inline=True)
    embed.add_field(name="Category",     value=item.get("category", "—"),     inline=True)
    embed.add_field(
        name="IPC",
        value=f"{item.get('ipc_code', '—')} — {item.get('ipc_description', '—')}",
        inline=False,
    )

    abstract = (item.get("abstract") or "").strip()
    if abstract:
        embed.add_field(name="Abstract", value=abstract[:1024], inline=False)

    citation = (item.get("apa_citation") or "").strip()
    if citation:
        embed.add_field(name="APA Citation", value=citation[:512], inline=False)

    if source_url:
        embed.add_field(name="Source", value=f"[View USPTO PDF]({source_url})", inline=False)

    # ── Image: MIT first, Wikimedia fallback ─────────────────────────────────
    image_source = None
    if with_image and patent_num not in ("—", ""):
        image_url = await _resolve_image(str(patent_num))
        if image_url:
            embed.set_image(url=image_url)
            # Detect source from URL so the footer is accurate
            if "mit.edu" in image_url:
                image_source = "MIT Tesla Archive"
            else:
                image_source = "Wikimedia Commons"

    # ── Footer ───────────────────────────────────────────────────────────────
    footer_parts: List[str] = []
    if total is not None:
        footer_parts.append(f"{total} patents in archive")
    if image_source:
        footer_parts.append(f"Drawing: {image_source}")
    elif with_image:
        footer_parts.append("No patent drawing found")
    if source_url:
        footer_parts.append("Click title to open PDF")
    if footer_parts:
        embed.set_footer(text=" · ".join(footer_parts))

    return embed


def _list_embed(
    title: str,
    items: List[Dict[str, Any]],
    page: int,
    page_size: int = 10,
) -> discord.Embed:
    """Paginated list embed — no image fetching here for speed."""
    total = len(items)
    start = page * page_size
    chunk = items[start : start + page_size]
    pages = max(1, (total - 1) // page_size + 1)

    lines = []
    for i in chunk:
        num  = i.get("patent_number", "—")
        name = i.get("title", "Untitled")
        year = i.get("year", "")
        url  = i.get("source_url")
        entry = f"[{num}]({url})" if url else f"`{num}`"
        lines.append(f"{entry} **{name}** ({year})")

    embed = discord.Embed(title=title, description="\n".join(lines), color=0x9C27B0)
    embed.set_footer(
        text=f"Page {page + 1}/{pages} · {total} result(s) · Click patent number to open PDF"
    )
    return embed


# ── Pagination view ───────────────────────────────────────────────────────────

class PatentPager(discord.ui.View):
    def __init__(self, embed_title: str, items: List[Dict[str, Any]], page_size: int = 10):
        super().__init__(timeout=120)
        self._title     = embed_title
        self._items     = items
        self._page      = 0
        self._page_size = page_size
        self._pages     = max(1, (len(items) - 1) // page_size + 1)
        self._refresh_buttons()

    def _refresh_buttons(self):
        self.prev_btn.disabled = self._page == 0
        self.next_btn.disabled = self._page >= self._pages - 1

    def current_embed(self) -> discord.Embed:
        return _list_embed(self._title, self._items, self._page, self._page_size)

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
    async def prev_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        self._page -= 1
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.current_embed(), view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        self._page += 1
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.current_embed(), view=self)


# ── Registration ──────────────────────────────────────────────────────────────

def register(bot, data_dir):

    existing = bot.tree.get_command("tesla")
    if isinstance(existing, app_commands.Group):
        return

    group = app_commands.Group(
        name="tesla",
        description="Nikola Tesla Academic Patent Archive (1885–1918)"
    )

    # ── /tesla random ─────────────────────────────────────────────────────────

    @group.command(name="random", description="Show a random Tesla patent with its drawing.")
    async def random_patent(interaction: discord.Interaction):
        await interaction.response.defer()

        data  = load_archive(data_dir)
        items = data.get("items", [])

        if not items:
            await interaction.followup.send("⚠️ Archive could not be loaded.", ephemeral=True)
            return

        item  = random.choice(items)
        embed = await _patent_embed(item, total=data.get("count"), with_image=True)
        await interaction.followup.send(embed=embed)

    # ── /tesla search ─────────────────────────────────────────────────────────

    @group.command(name="search", description="Search patents by title or abstract keyword.")
    @app_commands.describe(query="Word or phrase to search for")
    async def search(interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        data  = load_archive(data_dir)
        items = data.get("items", [])

        if not items:
            await interaction.followup.send("⚠️ Archive could not be loaded.", ephemeral=True)
            return

        q = query.lower().strip()
        matches = [
            i for i in items
            if q in i.get("title", "").lower()
            or q in i.get("abstract", "").lower()
        ]

        if not matches:
            await interaction.followup.send(
                f"😕 No patents found matching **\"{query}\"**.", ephemeral=True
            )
            return

        title = f"🔍 Search: \"{query}\""
        view  = PatentPager(title, matches)
        await interaction.followup.send(
            embed=view.current_embed(),
            view=view if len(matches) > 10 else None,
        )

    # ── /tesla category ───────────────────────────────────────────────────────

    @group.command(name="category", description="Browse patents by category.")
    @app_commands.describe(category="Patent category")
    @app_commands.choices(category=_CATEGORY_CHOICES)
    async def by_category(interaction: discord.Interaction, category: str):
        await interaction.response.defer()

        data  = load_archive(data_dir)
        items = data.get("items", [])

        if not items:
            await interaction.followup.send("⚠️ Archive could not be loaded.", ephemeral=True)
            return

        matches = [i for i in items if i.get("category", "").lower() == category.lower()]

        if not matches:
            await interaction.followup.send(
                f"😕 No patents found in category **{category}**.", ephemeral=True
            )
            return

        title = f"📂 Category: {category}"
        view  = PatentPager(title, matches)
        await interaction.followup.send(
            embed=view.current_embed(),
            view=view if len(matches) > 10 else None,
        )

    # ── /tesla ipc ────────────────────────────────────────────────────────────

    @group.command(name="ipc", description="Browse patents by IPC code.")
    @app_commands.describe(code="IPC classification code")
    @app_commands.choices(code=_IPC_CHOICES)
    async def ipc_filter(interaction: discord.Interaction, code: str):
        await interaction.response.defer()

        data  = load_archive(data_dir)
        items = data.get("items", [])

        if not items:
            await interaction.followup.send("⚠️ Archive could not be loaded.", ephemeral=True)
            return

        matches = [i for i in items if str(i.get("ipc_code", "")).startswith(code.upper())]

        if not matches:
            await interaction.followup.send(
                f"😕 No patents found for IPC **{code}**.", ephemeral=True
            )
            return

        title = f"🔬 IPC: {code}"
        view  = PatentPager(title, matches)
        await interaction.followup.send(
            embed=view.current_embed(),
            view=view if len(matches) > 10 else None,
        )

    # ── /tesla year ───────────────────────────────────────────────────────────

    @group.command(name="year", description="Browse patents filed in a specific year.")
    @app_commands.describe(year="Year between 1885 and 1918")
    async def year_filter(interaction: discord.Interaction, year: int):
        await interaction.response.defer()

        data  = load_archive(data_dir)
        items = data.get("items", [])

        if not items:
            await interaction.followup.send("⚠️ Archive could not be loaded.", ephemeral=True)
            return

        if year < 1885 or year > 1918:
            await interaction.followup.send(
                "📅 Tesla's archived patents span **1885–1918**. Please enter a year in that range.",
                ephemeral=True,
            )
            return

        matches = [i for i in items if i.get("year") == year]

        if not matches:
            await interaction.followup.send(
                f"😕 No patents found for **{year}**.", ephemeral=True
            )
            return

        title = f"📅 Year: {year}"
        view  = PatentPager(title, matches)
        await interaction.followup.send(
            embed=view.current_embed(),
            view=view if len(matches) > 10 else None,
        )

    # ── /tesla analytics ──────────────────────────────────────────────────────

    @group.command(name="analytics", description="Archive analytics overview.")
    async def analytics(interaction: discord.Interaction):
        await interaction.response.defer()

        data  = load_archive(data_dir)
        items = data.get("items", [])

        if not items:
            await interaction.followup.send("⚠️ Archive could not be loaded.", ephemeral=True)
            return

        years      = [i["year"]     for i in items if i.get("year")]
        categories = [i["category"] for i in items if i.get("category")]
        ipc_codes  = [i["ipc_code"] for i in items if i.get("ipc_code")]

        year_counter = Counter(years)
        cat_counter  = Counter(categories)
        ipc_counter  = Counter(ipc_codes)

        embed = discord.Embed(title="⚡ Tesla Patent Archive — Analytics", color=0x9C27B0)
        embed.add_field(name="Total Patents", value=str(len(items)),                inline=True)
        embed.add_field(name="Year Range",    value=f"{min(years)}–{max(years)}",  inline=True)
        embed.add_field(name="Categories",    value=str(len(cat_counter)),          inline=True)
        embed.add_field(
            name="Top 5 Active Years",
            value="\n".join(f"`{y}` — {c} patent(s)" for y, c in year_counter.most_common(5)),
            inline=True,
        )
        embed.add_field(
            name="Top Categories",
            value="\n".join(f"`{c}` — {n}" for c, n in cat_counter.most_common(5)),
            inline=True,
        )
        embed.add_field(
            name="IPC Breakdown",
            value="\n".join(f"`{c}` — {n}" for c, n in ipc_counter.most_common(4)),
            inline=True,
        )
        embed.set_footer(text="Use /tesla category or /tesla ipc to browse by group")
        await interaction.followup.send(embed=embed)

    # ─────────────────────────────────────────────────────────────────────────
    bot.tree.add_command(group)

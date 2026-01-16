from __future__ import annotations

import os
import json
import random
import discord
from discord import app_commands

REG_FILE_PART1 = "gaming_products_registry_part1.json"
REG_FILE_PART2 = "gaming_products_registry_part2.json"
TIMELINE_FILE = "gaming_timeline.json"
PART1_MAX_YEAR = 2011

ICON_GAME = "🎮"
ICON_ARCADE = "🕹️"
ICON_PC = "💻"
ICON_CONSOLE = "🧩"
ICON_TIMELINE = "🗓️"
ICON_SOURCE = "🔗"

def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _load_items(data_dir: str, filename: str) -> list[dict]:
    path = os.path.join(data_dir, filename)
    obj = _load_json(path)
    items = obj.get("items", [])
    return items if isinstance(items, list) else []

def _fmt_source(item: dict) -> str:
    src = (item.get("source") or "").strip()
    url = (item.get("source_url") or "").strip()
    if src and url:
        return f"[{src}]({url})"
    return src or url or "—"

def _decade_color(year: int | None) -> discord.Colour | None:
    if not isinstance(year, int):
        return None
    decade = (year // 10) * 10
    palette = {
        1970: discord.Colour.from_rgb(120, 88, 60),
        1980: discord.Colour.from_rgb(24, 120, 120),
        1990: discord.Colour.from_rgb(88, 72, 140),
        2000: discord.Colour.from_rgb(35, 92, 170),
        2010: discord.Colour.from_rgb(160, 60, 60),
        2020: discord.Colour.from_rgb(110, 110, 110),
    }
    return palette.get(decade)

def _category_icon(cat: str) -> str:
    c = (cat or "").strip().lower()
    if "console" in c:
        return ICON_CONSOLE
    if "computer" in c or "pc" in c:
        return ICON_PC
    return ICON_GAME

def _set_branding(embed: discord.Embed, item: dict) -> None:
    thumb = (item.get("logo_url") or "").strip()
    img = (item.get("image_url") or "").strip()
    icon = (item.get("icon_url") or "").strip()

    if icon:
        embed.set_author(name="Bottany Gaming", icon_url=icon)
    else:
        embed.set_author(name="Bottany Gaming")

    if thumb:
        embed.set_thumbnail(url=thumb)
    if img:
        embed.set_image(url=img)

def register_gaming_products(bot: discord.Client, data_dir: str) -> None:
    gaming = app_commands.Group(name="gaming", description="Gaming products & history (curated).")

    @gaming.command(
        name="product",
        description="Random product with year, intro and sources (Part 1 ≤ 2011).",
    )
    async def product(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        items = _load_items(data_dir, REG_FILE_PART1)
        if not items:
            await interaction.followup.send("Gaming products registry (Part 1) is empty.", ephemeral=True)
            return

        item = random.choice(items)

        name = item.get("name", "Unknown")
        cat = item.get("category", "product")
        mfg = item.get("manufacturer", "Unknown manufacturer")
        year = item.get("release_year", None)
        year_str = str(year) if isinstance(year, int) else "—"
        region = item.get("region_note", "")
        intro = item.get("short_intro", "")

        icon = _category_icon(cat)
        title = f"{icon} {name} ({year_str})"

        desc_lines = [
            f"**{_category_icon(cat)} Type:** {cat}",
            f"**🏷️ Manufacturer:** {mfg}",
        ]
        if region:
            desc_lines.append(f"**🧾 Release note:** {region}")
        if intro:
            desc_lines.append("")
            desc_lines.append(intro)

        embed = discord.Embed(
            title=title,
            description="\n".join(desc_lines).strip(),
            colour=_decade_color(year),
        )
        _set_branding(embed, item)
        embed.add_field(name=f"{ICON_SOURCE} Source", value=_fmt_source(item)[:1024], inline=False)
        embed.set_footer(text="Part 1 dataset (≤2011). We love Kevy")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @gaming.command(
        name="year_part1",
        description="Lists Part 1 products by year (≤2011) or shows a summary.",
    )
    @app_commands.describe(year="Year (<= 2011). Leave empty for a year summary.")
    async def year_part1(interaction: discord.Interaction, year: int | None = None):
        await interaction.response.defer(ephemeral=True)

        items = _load_items(data_dir, REG_FILE_PART1)
        if not items:
            await interaction.followup.send("Gaming products registry (Part 1) is empty.", ephemeral=True)
            return

        if year is None:
            counts: dict[int, int] = {}
            for it in items:
                y = it.get("release_year")
                if isinstance(y, int) and y <= PART1_MAX_YEAR:
                    counts[y] = counts.get(y, 0) + 1
            years = sorted(counts.keys())
            if not years:
                await interaction.followup.send("No Part 1 entries found.", ephemeral=True)
                return

            lines = [f"• **{y}**: {counts[y]} item(s)" for y in years]
            embed = discord.Embed(
                title=f"{ICON_TIMELINE} Gaming products by year — Part 1 (≤2011)",
                description="\n".join(lines)[:3900],
            )
            embed.set_footer(text="Use /gaming year_part1 <year> to list items for that year.")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        if year > PART1_MAX_YEAR:
            await interaction.followup.send(
                f"Part 1 covers up to {PART1_MAX_YEAR}. You requested {year}. Use /gaming product_part2 for 2012+.",
                ephemeral=True,
            )
            return

        year_items = [it for it in items if it.get("release_year") == year]
        year_items.sort(key=lambda x: (x.get("category", ""), x.get("name", "")))

        if not year_items:
            await interaction.followup.send(f"No Part 1 entries found for {year}.", ephemeral=True)
            return

        lines = []
        for it in year_items[:70]:
            n = it.get("name", "Untitled")
            c = it.get("category", "product")
            m = it.get("manufacturer", "—")
            lines.append(f"• {_category_icon(c)} **{n}** — {c} — {m}")

        embed = discord.Embed(
            title=f"{ICON_TIMELINE} Gaming products — {year} (Part 1)",
            description="\n".join(lines)[:3900],
            colour=_decade_color(year),
        )
        embed.set_footer(text="Entries are curated with references where available.")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @gaming.command(
        name="product_part2",
        description="Random modern gaming product (Part 2: 2012+).",
    )
    async def product_part2(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        items = _load_items(data_dir, REG_FILE_PART2)
        if not items:
            await interaction.followup.send("Gaming products registry (Part 2) is empty.", ephemeral=True)
            return

        item = random.choice(items)
        name = item.get("name", "Unknown")
        cat = item.get("category", "product")
        mfg = item.get("manufacturer", "Unknown manufacturer")
        year = item.get("release_year", None)
        year_str = str(year) if isinstance(year, int) else "—"
        intro = item.get("short_intro", "")

        embed = discord.Embed(
            title=f"{_category_icon(cat)} {name} ({year_str})",
            description=f"**{_category_icon(cat)} Type:** {cat}\n**🏷️ Manufacturer:** {mfg}\n\n{intro}".strip(),
            colour=_decade_color(year),
        )
        _set_branding(embed, item)
        embed.add_field(name=f"{ICON_SOURCE} Source", value=_fmt_source(item)[:1024], inline=False)
        embed.set_footer(text="Part 2 dataset (2012+). We love Kevy")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @gaming.command(
        name="timeline",
        description="Decade-based gaming timeline (games, consoles, computers).",
    )
    @app_commands.describe(decade="Optional decade filter, e.g., 1970s, 1980s, 1990s.")
    async def timeline(interaction: discord.Interaction, decade: str | None = None):
        await interaction.response.defer(ephemeral=True)

        path = os.path.join(data_dir, TIMELINE_FILE)
        if not os.path.exists(path):
            await interaction.followup.send("Timeline dataset is missing (gaming_timeline.json).", ephemeral=True)
            return

        obj = _load_json(path)
        decades: dict = obj.get("decades", {}) if isinstance(obj.get("decades", {}), dict) else {}

        if not decades:
            await interaction.followup.send("Timeline dataset is empty.", ephemeral=True)
            return

        keys = sorted(decades.keys())
        if decade is None:
            embed = discord.Embed(
                title=f"{ICON_TIMELINE} Gaming timeline (decades)",
                description="\n".join([f"• **{k}** ({len(decades.get(k, []))} item(s))" for k in keys])[:3900],
            )
            embed.set_footer(text="Use /gaming timeline <decade> (e.g., 1980s). We love Kevy")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        decade = decade.strip()
        if decade not in decades:
            await interaction.followup.send(
                f"Unknown decade '{decade}'. Available: " + ", ".join(keys),
                ephemeral=True,
            )
            return

        items = decades.get(decade, [])
        lines = [f"• {x}" for x in items][:120]

        year_hint = None
        try:
            year_hint = int(decade[:4])
        except Exception:
            year_hint = None

        embed = discord.Embed(
            title=f"{ICON_TIMELINE} Gaming timeline — {decade}",
            description="\n".join(lines)[:3900] if lines else "—",
            colour=_decade_color(year_hint),
        )
        embed.set_footer(text="Curated timeline: games + consoles + computers. We love Kevy")
        await interaction.followup.send(embed=embed, ephemeral=True)

    bot.tree.add_command(gaming)

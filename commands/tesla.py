from __future__ import annotations

import random
import asyncio
import discord
from discord import app_commands
from collections import Counter

from services.tesla_catalog_service import get_tesla_catalog
from services.tesla_mit_resolver import resolve_mit_patent_image
from services.tesla_wikimedia_resolver import resolve_wikimedia_patent_image


# -------------------------------------------------
# IMAGE RESOLVER (parallel + safe)
# -------------------------------------------------

async def _resolve_image_safe(patent_number: str):

    try:
        mit = asyncio.create_task(resolve_mit_patent_image(patent_number))
        wiki = asyncio.create_task(resolve_wikimedia_patent_image(patent_number))

        done, pending = await asyncio.wait(
            [mit, wiki],
            timeout=6,
            return_when=asyncio.FIRST_COMPLETED
        )

        for task in pending:
            task.cancel()

        for task in done:
            img = task.result()
            if img:
                return img

    except Exception:
        pass

    return None


# -------------------------------------------------
# REGISTER
# -------------------------------------------------

def register(bot, DATA_DIR):

    existing = bot.tree.get_command("tesla")

    if isinstance(existing, app_commands.Group):
        group = existing
    else:
        group = app_commands.Group(
            name="tesla",
            description="Nikola Tesla official U.S. patents."
        )
        bot.tree.add_command(group)

    # -------------------------------------------------
    # RANDOM
    # -------------------------------------------------

    @group.command(name="random", description="Show one official Tesla patent.")
    async def tesla_random(interaction: discord.Interaction):

        await interaction.response.defer(thinking=True)

        catalog = await get_tesla_catalog(DATA_DIR)
        items = catalog.get("items", [])

        if not items:
            await interaction.followup.send("No Tesla items available.")
            return

        it = random.choice(items)
        patent = it.get("patent_number", "")
        title = (it.get("title") or "Untitled")[:200]

        embed = discord.Embed(
            title=f"U.S. Patent {patent} — {title}"[:256],
            color=0x9C27B0
        )

        if it.get("source_url"):
            embed.add_field(
                name="Source",
                value=it["source_url"][:1024],
                inline=False
            )

        img = await _resolve_image_safe(patent)
        if img:
            embed.set_image(url=img)

        embed.set_footer(text=f"Catalog size: {catalog.get('count',0)}")

        await interaction.followup.send(embed=embed)

    # -------------------------------------------------
    # ANALYTICS
    # -------------------------------------------------

    @group.command(name="analytics", description="Patent analytics overview.")
    async def tesla_analytics(interaction: discord.Interaction):

        await interaction.response.defer()

        catalog = await get_tesla_catalog(DATA_DIR)
        items = catalog.get("items", [])

        if not items:
            await interaction.followup.send("No Tesla items available.")
            return

        years = [
            int(i.get("year"))
            for i in items
            if str(i.get("year")).isdigit()
        ]

        if not years:
            await interaction.followup.send("Year data unavailable.")
            return

        counter = Counter(years)
        total = len(items)

        min_year = min(years)
        max_year = max(years)

        top_years = counter.most_common(5)

        embed = discord.Embed(
            title="📊 Tesla Patent Analytics",
            color=0x9C27B0
        )

        embed.add_field(name="Total patents", value=str(total), inline=True)
        embed.add_field(name="Year range", value=f"{min_year} – {max_year}", inline=True)

        year_lines = [
            f"{year}: {count}"
            for year, count in top_years
        ]

        embed.add_field(
            name="Top active years",
            value="\n".join(year_lines)[:1024],
            inline=False
        )

        embed.set_footer(text="Based on catalog dataset")

        await interaction.followup.send(embed=embed)

    # -------------------------------------------------
    # YEAR FILTER
    # -------------------------------------------------

    @group.command(name="year", description="Show patents from a specific year.")
    async def tesla_year(interaction: discord.Interaction, year: int):

        await interaction.response.defer()

        if year < 1800 or year > 1950:
            await interaction.followup.send("Year outside Tesla patent era.")
            return

        catalog = await get_tesla_catalog(DATA_DIR)
        items = catalog.get("items", [])

        matches = [
            i for i in items
            if str(i.get("year")) == str(year)
        ]

        if not matches:
            await interaction.followup.send(
                f"No patents found for {year}."
            )
            return

        embed = discord.Embed(
            title=f"⚡ Tesla Patents — {year}",
            color=0x9C27B0
        )

        lines = []

        for it in matches[:25]:  # guard
            pat = it.get("patent_number", "")
            title = (it.get("title") or "")[:120]
            lines.append(f"• {pat} — {title}")

        embed.description = "\n".join(lines)[:4000]

        if len(matches) > 25:
            embed.set_footer(text=f"Showing first 25 of {len(matches)} patents")
        else:
            embed.set_footer(text=f"{len(matches)} patent(s) found")

        await interaction.followup.send(embed=embed)

    # -------------------------------------------------
    # SOURCES
    # -------------------------------------------------

    @group.command(name="sources", description="Show institutional sources.")
    async def tesla_sources(interaction: discord.Interaction):

        embed = discord.Embed(
            title="Nikola Tesla — Institutional Sources",
            color=0x9C27B0
        )

        embed.add_field(
            name="MIT Tesla Patent Collection",
            value="https://web.mit.edu/most/Public/Tesla1/alpha_tesla.html",
            inline=False
        )

        embed.add_field(
            name="USPTO Database",
            value="https://ppubs.uspto.gov/",
            inline=False
        )

        embed.set_footer(text="Institutional archival sources")

        await interaction.response.send_message(embed=embed)

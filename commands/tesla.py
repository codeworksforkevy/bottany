from __future__ import annotations

import random
from collections import Counter
import discord
from discord import app_commands

from services.tesla_archive_service import load_archive


# =====================================================
# REGISTER
# =====================================================

def register(bot, data_dir):

    # Prevent duplicate registration
    existing = bot.tree.get_command("tesla")
    if isinstance(existing, app_commands.Group):
        return

    group = app_commands.Group(
        name="tesla",
        description="Tesla Academic Patent Archive"
    )

    # =====================================================
    # RANDOM
    # =====================================================

    @group.command(name="random", description="Show random Tesla patent.")
    async def random_patent(interaction: discord.Interaction):

        await interaction.response.defer()

        data = load_archive(data_dir)
        items = data.get("items", [])

        if not items:
            await interaction.followup.send("Archive not loaded.")
            return

        it = random.choice(items)

        embed = discord.Embed(
            title=f"{it.get('patent_number','—')} — {it.get('title','Untitled')}",
            color=0x9C27B0
        )

        embed.add_field(name="Jurisdiction", value=it.get("jurisdiction", "—"), inline=True)
        embed.add_field(name="Issue Date", value=it.get("issue_date", "—"), inline=True)
        embed.add_field(name="IPC", value=it.get("ipc_code", "—"), inline=True)
        embed.add_field(name="Family ID", value=it.get("patent_family_id", "—"), inline=True)

        embed.add_field(
            name="APA Citation",
            value=it.get("apa_citation", "—")[:1024],
            inline=False
        )

        embed.set_footer(text=f"Archive size: {data.get('count',0)}")

        await interaction.followup.send(embed=embed)

    # =====================================================
    # ANALYTICS
    # =====================================================

    @group.command(name="analytics", description="Archive analytics overview.")
    async def analytics(interaction: discord.Interaction):

        await interaction.response.defer()

        data = load_archive(data_dir)
        items = data.get("items", [])

        if not items:
            await interaction.followup.send("Archive not loaded.")
            return

        years = [
            int(str(i.get("issue_date",""))[:4])
            for i in items
            if i.get("issue_date")
        ]

        if not years:
            await interaction.followup.send("No year data available.")
            return

        counter = Counter(years)
        top_years = counter.most_common(5)

        embed = discord.Embed(
            title="Tesla Patent Analytics",
            color=0x9C27B0
        )

        embed.add_field(name="Total Patents", value=str(len(items)), inline=True)
        embed.add_field(
            name="Top Active Years",
            value="\n".join(f"{y}: {c}" for y, c in top_years),
            inline=False
        )

        await interaction.followup.send(embed=embed)

    # =====================================================
    # IPC FILTER (supports subclass prefix)
    # =====================================================

    @group.command(name="ipc", description="Filter by IPC code (e.g. H02K).")
    async def ipc_filter(interaction: discord.Interaction, code: str):

        await interaction.response.defer()

        data = load_archive(data_dir)
        items = data.get("items", [])

        code = code.upper().strip()

        # Prefix match → supports H02K vs H02P separation
        matches = [
            i for i in items
            if str(i.get("ipc_code","")).startswith(code)
        ]

        if not matches:
            await interaction.followup.send("No patents for this IPC.")
            return

        lines = [
            f"{i.get('patent_number','—')} — {i.get('title','Untitled')}"
            for i in matches[:25]
        ]

        embed = discord.Embed(
            title=f"Tesla IPC {code}",
            description="\n".join(lines),
            color=0x9C27B0
        )

        if len(matches) > 25:
            embed.set_footer(text=f"Showing first 25 of {len(matches)} results")

        await interaction.followup.send(embed=embed)

    # =====================================================
    # YEAR FILTER
    # =====================================================

    @group.command(name="year", description="Filter patents by issue year.")
    async def year_filter(interaction: discord.Interaction, year: int):

        await interaction.response.defer()

        data = load_archive(data_dir)
        items = data.get("items", [])

        matches = [
            i for i in items
            if str(i.get("issue_date","")).startswith(str(year))
        ]

        if not matches:
            await interaction.followup.send("No patents that year.")
            return

        lines = [
            f"{i.get('patent_number','—')} — {i.get('title','Untitled')}"
            for i in matches[:25]
        ]

        embed = discord.Embed(
            title=f"Tesla Patents — {year}",
            description="\n".join(lines),
            color=0x9C27B0
        )

        if len(matches) > 25:
            embed.set_footer(text=f"Showing first 25 of {len(matches)} results")

        await interaction.followup.send(embed=embed)

    # =====================================================

    bot.tree.add_command(group)

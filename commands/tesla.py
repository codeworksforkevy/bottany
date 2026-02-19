from __future__ import annotations

import random
from collections import Counter
import discord
from discord import app_commands

from services.tesla_archive_service import load_archive


def register(bot, DATA_DIR):

    group = app_commands.Group(
        name="tesla",
        description="Tesla Academic Patent Archive"
    )

    # -----------------------------------------
    # RANDOM
    # -----------------------------------------
    @group.command(name="random")
    async def random_patent(interaction: discord.Interaction):

        data = load_archive(DATA_DIR)
        items = data["items"]

        if not items:
            await interaction.response.send_message("Archive not loaded.")
            return

        it = random.choice(items)

        embed = discord.Embed(
            title=f"{it['patent_number']} — {it['title']}",
            color=0x9C27B0
        )

        embed.add_field(name="Jurisdiction", value=it.get("jurisdiction", "—"))
        embed.add_field(name="Issue Date", value=it.get("issue_date", "—"))
        embed.add_field(name="IPC", value=it.get("ipc_code", "—"))
        embed.add_field(name="Family ID", value=it.get("patent_family_id", "—"))
        embed.add_field(name="APA Citation", value=it.get("apa_citation", "—"), inline=False)

        embed.set_footer(text=f"Archive size: {data['count']}")

        await interaction.response.send_message(embed=embed)


    # -----------------------------------------
    # ANALYTICS
    # -----------------------------------------
    @group.command(name="analytics")
    async def analytics(interaction: discord.Interaction):

        data = load_archive(DATA_DIR)
        items = data["items"]

        years = [
            int(str(i["issue_date"])[:4])
            for i in items
            if i.get("issue_date")
        ]

        counter = Counter(years)

        top_years = counter.most_common(5)

        embed = discord.Embed(
            title="Tesla Patent Analytics",
            color=0x9C27B0
        )

        embed.add_field(name="Total Patents", value=str(len(items)))
        embed.add_field(name="Top Active Years",
                        value="\n".join(f"{y}: {c}" for y, c in top_years),
                        inline=False)

        await interaction.response.send_message(embed=embed)


    # -----------------------------------------
    # IPC FILTER
    # -----------------------------------------
    @group.command(name="ipc")
    async def ipc_filter(interaction: discord.Interaction, code: str):

        data = load_archive(DATA_DIR)
        items = [i for i in data["items"] if i.get("ipc_code") == code.upper()]

        if not items:
            await interaction.response.send_message("No patents for this IPC.")
            return

        lines = [f"{i['patent_number']} — {i['title']}" for i in items[:20]]

        embed = discord.Embed(
            title=f"Tesla IPC {code.upper()}",
            description="\n".join(lines),
            color=0x9C27B0
        )

        await interaction.response.send_message(embed=embed)


    # -----------------------------------------
    # YEAR FILTER
    # -----------------------------------------
    @group.command(name="year")
    async def year_filter(interaction: discord.Interaction, year: int):

        data = load_archive(DATA_DIR)
        items = [
            i for i in data["items"]
            if str(i.get("issue_date", "")).startswith(str(year))
        ]

        if not items:
            await interaction.response.send_message("No patents that year.")
            return

        lines = [f"{i['patent_number']} — {i['title']}" for i in items[:20]]

        embed = discord.Embed(
            title=f"Tesla Patents — {year}",
            description="\n".join(lines),
            color=0x9C27B0
        )

        await interaction.response.send_message(embed=embed)

    bot.tree.add_command(group)

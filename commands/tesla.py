
import random
import discord
from discord import app_commands
from services.tesla_catalog_service import get_tesla_catalog
from services.tesla_mit_resolver import resolve_mit_patent_image
from services.tesla_wikimedia_resolver import resolve_wikimedia_patent_image

def register_tesla(bot, DATA_DIR):

    group = app_commands.Group(
        name="tesla",
        description="Nikola Tesla official U.S. patents."
    )

    @group.command(name="random", description="Show one official Tesla patent.")
    async def tesla_random(interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        catalog = await get_tesla_catalog(DATA_DIR)
        items = catalog.get("items", [])
        if not items:
            await interaction.followup.send("No Tesla items available.")
            return
        it = random.choice(items)
        pat = it.get("patent_number","")
        embed = discord.Embed(
            title=f"U.S. Patent {pat} — {it.get('title')}"
        )
        embed.add_field(name="Source", value=it.get("source_url"), inline=False)

        img = await resolve_mit_patent_image(pat)
        if not img:
            img = await resolve_wikimedia_patent_image(pat)
        if img:
            embed.set_image(url=img)

        embed.set_footer(text=f"Catalog size: {catalog.get('count',0)}")
        await interaction.followup.send(embed=embed)

    @group.command(name="patent", description="Lookup a specific patent.")
    async def tesla_patent(interaction: discord.Interaction, number: str):
        await interaction.response.defer(thinking=True)
        catalog = await get_tesla_catalog(DATA_DIR)
        match = next((i for i in catalog.get("items",[]) if i["patent_number"] == number), None)
        if not match:
            await interaction.followup.send("Patent not found in catalog.")
            return
        embed = discord.Embed(
            title=f"U.S. Patent {number} — {match.get('title')}"
        )
        await interaction.followup.send(embed=embed)

    @group.command(name="sources", description="Show institutional sources.")
    async def tesla_sources(interaction: discord.Interaction):
        embed = discord.Embed(title="Tesla — Institutional Sources")
        embed.add_field(
            name="MIT Tesla U.S. Patent Collection",
            value="https://web.mit.edu/most/Public/Tesla1/alpha_tesla.html",
            inline=False
        )
        await interaction.response.send_message(embed=embed)

    bot.tree.add_command(group)

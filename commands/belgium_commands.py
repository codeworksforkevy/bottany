
import os
import json
import discord
from utils.pagination import PaginationView
from utils.fuzzy_search import fuzzy_search
from utils.embed_utils import apply_source_footer

async def register(bot, data_dir):

    path = os.path.join(data_dir, "belgium_beverages_professional_v2.json")

    @bot.tree.command(name="belgium_search", description="Search Belgian dataset.")
    async def belgium_search(interaction: discord.Interaction, query: str):

        await interaction.response.defer()

        try:
            with open(path, "r", encoding="utf-8") as f:
                reg = json.load(f)
        except Exception:
            await interaction.followup.send("Dataset not found.")
            return

        items = reg.get("items", [])
        results = fuzzy_search(query, items)

        if not results:
            await interaction.followup.send("No matches found.")
            return

        embeds = []
        for chunk in [results[i:i+5] for i in range(0, len(results), 5)]:
            embed = discord.Embed(title=f"Belgium Search: {query}")
            for item in chunk:
                embed.add_field(
                    name=item.get("name"),
                    value=f"Category: {item.get('category')} | Region: {item.get('region')}",
                    inline=False
                )
            embeds.append(embed)

        view = PaginationView(embeds)
        await interaction.followup.send(embed=view.embeds[0], view=view)

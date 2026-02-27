import discord
from discord import app_commands

async def register(bot, data_dir):

    @bot.tree.command(
        name="belgium_search",
        description="Search across Belgian cultural datasets"
    )
    async def belgium_search(
        interaction: discord.Interaction,
        query: str
    ):

        await interaction.response.defer()

        items = load_all_belgium(data_dir)

        if not items:
            await interaction.followup.send("No datasets loaded.")
            return

        results = fuzzy_search(query, items)

        if not results:
            await interaction.followup.send("No matches found.")
            return

        def dataset_badge(item):

            if item.get("dataset_type") == "chocolate":
                return "🍫"

            category = (item.get("category") or "").lower()

            if category == "beer":
                return "🍺"
            if category == "soft_drinks":
                return "🥤"
            if category == "water":
                return "🚰"
            if category == "coffee":
                return "☕"

            return "📦"

        embeds = []

        for chunk in [results[i:i+5] for i in range(0, len(results), 5)]:

            embed = discord.Embed(
                title="Belgium Search Results",
                description=f"Query: **{query}**",
                color=0x5865F2
            )

            for item in chunk:

                badge = dataset_badge(item)

                name = item.get("name", "Unknown")
                category = item.get("category", "N/A")
                region = item.get("region", "N/A")
                year = item.get("foundation_year")

                value = f"Category: {category}\nRegion: {region}"

                if year:
                    value += f"\nFounded: {year}"

                embed.add_field(
                    name=f"{badge} {name}",
                    value=value,
                    inline=False
                )

            apply_source_footer(embed, source="Belgium Professional Registry")

            embeds.append(embed)

        view = PaginationView(embeds)

        await interaction.followup.send(
            embed=embeds[0],
            view=view
        )


import discord
import aiohttp
import datetime as dt
from utils.pagination import PaginationView
from utils.fuzzy_search import fuzzy_search

PLATFORM_COLORS = {
    "epic": 0x001F3F,       # Navy
    "luna": 0xCC5500,       # Burnt orange
    "humble": 0x303030,     # Anthracite
    "gog": 0xF4C2C2         # Baby pink
}

EPIC_ENDPOINT = "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions"

async def fetch_epic(session):
    async with session.get(EPIC_ENDPOINT, timeout=15) as resp:
        data = await resp.json()

    offers = []
    elements = data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", [])

    now = dt.datetime.utcnow()

    for el in elements:
        promotions = el.get("promotions")
        if not promotions:
            continue

        promo = promotions.get("promotionalOffers")
        if not promo:
            continue

        for p in promo:
            for offer in p.get("promotionalOffers", []):
                start = dt.datetime.fromisoformat(offer["startDate"].replace("Z", "+00:00"))
                end = dt.datetime.fromisoformat(offer["endDate"].replace("Z", "+00:00"))

                if start <= now <= end:
                    offers.append({
                        "platform": "epic",
                        "kind": "free_to_keep",
                        "title": el.get("title"),
                        "url": f"https://store.epicgames.com/en-US/p/{el.get('productSlug')}",
                        "thumbnail": None,
                        "expires_at": end
                    })

    return offers

async def register(bot, data_dir):

    @bot.tree.command(name="freegames_now", description="Currently active free games.")
    async def freegames_now(interaction: discord.Interaction, platform: str = None):

        await interaction.response.defer()

        async with aiohttp.ClientSession() as session:
            epic_offers = await fetch_epic(session)

        offers = epic_offers  # Extendable for GOG/Humble/Luna

        if platform:
            offers = [o for o in offers if o["platform"] == platform.lower()]

        if not offers:
            await interaction.followup.send("No active offers found.")
            return

        embeds = []
        for chunk in [offers[i:i+5] for i in range(0, len(offers), 5)]:
            embed = discord.Embed(
                title="Free Games Now",
                color=PLATFORM_COLORS.get(chunk[0]["platform"], 0x2F3136)
            )

            for offer in chunk:
                expiry = offer["expires_at"].strftime("%Y-%m-%d")
                embed.add_field(
                    name=offer["title"],
                    value=f"Platform: {offer['platform'].upper()}\nType: {offer['kind']}\nEnds: {expiry}",
                    inline=False
                )

            embeds.append(embed)

        view = PaginationView(embeds)
        await interaction.followup.send(embed=embeds[0], view=view)

    @bot.tree.command(name="freegames_search", description="Search free games.")
    async def freegames_search(interaction: discord.Interaction, query: str):

        await interaction.response.defer()

        async with aiohttp.ClientSession() as session:
            epic_offers = await fetch_epic(session)

        offers = epic_offers
        results = fuzzy_search(query, offers)

        if not results:
            await interaction.followup.send("No matches found.")
            return

        embeds = []
        for chunk in [results[i:i+5] for i in range(0, len(results), 5)]:
            embed = discord.Embed(
                title=f"Search Results: {query}",
                color=PLATFORM_COLORS.get(chunk[0]["platform"], 0x2F3136)
            )

            for offer in chunk:
                embed.add_field(
                    name=offer["title"],
                    value=f"Platform: {offer['platform'].upper()}",
                    inline=False
                )

            embeds.append(embed)

        view = PaginationView(embeds)
        await interaction.followup.send(embed=embeds[0], view=view)

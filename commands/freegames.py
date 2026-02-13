
import discord
import aiohttp
import asyncio
import datetime as dt
from utils.pagination import PaginationView
from utils.fuzzy_search import fuzzy_search

PLATFORM_COLORS = {
    "epic": 0x001F3F,
    "gog": 0xF4C2C2,
    "humble": 0x303030,
    "luna": 0xCC5500
}

EPIC_ENDPOINT = "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions"
GOG_ENDPOINT = "https://www.gog.com/games/ajax/filtered?mediaType=game&price=free&sort=popularity"
HUMBLE_ENDPOINT = "https://www.humblebundle.com/store/api/search?sort=bestselling&filter=onsale"
LUNA_ENDPOINT = "https://luna.amazon.com/"

async def fetch_epic(session):
    try:
        async with session.get(EPIC_ENDPOINT, timeout=10) as resp:
            data = await resp.json()
    except:
        return []

    offers = []
    now = dt.datetime.utcnow()

    elements = data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", [])

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
                        "expires_at": end
                    })

    return offers

async def fetch_gog(session):
    try:
        async with session.get(GOG_ENDPOINT, timeout=10) as resp:
            data = await resp.json()
    except:
        return []

    offers = []
    for item in data.get("products", []):
        if item.get("price", {}).get("isFree"):
            offers.append({
                "platform": "gog",
                "kind": "free_to_keep",
                "title": item.get("title"),
                "url": item.get("url"),
                "expires_at": None
            })
    return offers

async def fetch_humble(session):
    try:
        async with session.get(HUMBLE_ENDPOINT, timeout=10) as resp:
            data = await resp.json()
    except:
        return []

    offers = []
    for item in data.get("results", []):
        if item.get("price", {}).get("is_free"):
            offers.append({
                "platform": "humble",
                "kind": "free_to_keep",
                "title": item.get("human_name"),
                "url": item.get("product_url"),
                "expires_at": None
            })
    return offers

async def fetch_luna(session):
    # Placeholder live fetch
    return []

async def register(bot, data_dir):

    @bot.tree.command(name="freegames_now", description="Currently active free games.")
    async def freegames_now(interaction: discord.Interaction, platform: str = None):

        await interaction.response.defer()

        async with aiohttp.ClientSession() as session:
            results = await asyncio.gather(
                fetch_epic(session),
                fetch_gog(session),
                fetch_humble(session),
                fetch_luna(session)
            )

        offers = [o for sub in results for o in sub]

        if platform:
            offers = [o for o in offers if o["platform"] == platform.lower()]

        if not offers:
            await interaction.followup.send("No active offers found.")
            return

        embeds = []
        for chunk in [offers[i:i+5] for i in range(0, len(offers), 5)]:
            color = PLATFORM_COLORS.get(chunk[0]["platform"], 0x2F3136)

            embed = discord.Embed(
                title="Free Games Now",
                color=color
            )

            for offer in chunk:
                expiry = offer["expires_at"].strftime("%Y-%m-%d") if offer["expires_at"] else "N/A"
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
            results = await asyncio.gather(
                fetch_epic(session),
                fetch_gog(session),
                fetch_humble(session),
                fetch_luna(session)
            )

        offers = [o for sub in results for o in sub]
        results = fuzzy_search(query, offers)

        if not results:
            await interaction.followup.send("No matches found.")
            return

        embeds = []
        for chunk in [results[i:i+5] for i in range(0, len(results), 5)]:
            color = PLATFORM_COLORS.get(chunk[0]["platform"], 0x2F3136)

            embed = discord.Embed(
                title=f"Search Results: {query}",
                color=color
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

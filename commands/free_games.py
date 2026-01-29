from discord import app_commands, Embed
import discord
from freegames_logic import fetch_all_offers

BABY_BLUE = 0x9AD0EC
BABY_PINK = 0xF4B6C2
BURNT_ORANGE = 0xE67E22

async def register_free_games(client):
    @client.tree.command(name="freegames", description="Free, discounted and subscription games")
    @app_commands.describe(only_free="Only show free-to-keep games")
    async def freegames(interaction: discord.Interaction, only_free: bool = False):
        offers = await fetch_all_offers()
        groups = {"free": [], "discount": [], "subscription": []}
        for o in offers:
            groups[o.kind].append(o)

        await interaction.response.defer()

        if groups["free"]:
            e = Embed(title="Free Games", color=BABY_BLUE)
            for o in groups["free"]:
                e.add_field(name=o.title, value=o.url, inline=False)
            await interaction.followup.send(embed=e)

        if not only_free and groups["discount"]:
            e = Embed(title="Discounted Deals", color=BABY_PINK)
            for o in groups["discount"]:
                e.add_field(name=o.title, value=o.url, inline=False)
            await interaction.followup.send(embed=e)

        if not only_free and groups["subscription"]:
            e = Embed(title="Subscription Picks", color=BURNT_ORANGE)
            for o in groups["subscription"]:
                e.add_field(name=o.title, value=o.url, inline=False)
            await interaction.followup.send(embed=e)

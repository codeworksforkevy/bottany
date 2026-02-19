import discord
from discord import app_commands
from services.twitch_service import twitch_service
from services.drop_registry import DropRegistry
from services.http_client import http_client

COLOR_TWITCH = 0x9146FF
COLOR_EVENT = 0xF59E0B

def register_twitch_unified_feed(client, tree, data_dir):

    registry = DropRegistry(data_dir)

    @tree.command(name="twitchfeed", description="Unified Twitch feed.")
    async def twitchfeed(interaction: discord.Interaction):

        await interaction.response.defer(thinking=True)

        badges = twitch_service._badge_cache
        drops = registry.get_active()

        embeds = []

        if badges:
            e = discord.Embed(
                title="👩‍💻 Twitch Badges",
                description="Latest global Twitch chat badges.",
                color=COLOR_TWITCH
            )
            if badges[0].get("img"):
                e.set_thumbnail(url=badges[0]["img"])
            e.set_footer(text=f"{len(badges)} cached badges")
            embeds.append(e)

        if drops:
            e2 = discord.Embed(
                title="🎁 Active Twitch Drops",
                color=COLOR_EVENT
            )
            e2.description = "\n".join(
                f"• {d.get('game','Unknown')} — {d.get('campaign','')}"
                for d in drops[:5]
            )
            embeds.append(e2)

        if not embeds:
            await interaction.followup.send("No Twitch data available.")
            return

        await interaction.followup.send(embeds=embeds)

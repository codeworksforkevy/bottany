import discord
from discord import app_commands

from services.twitch_service import twitch_service
from services.drop_registry import DropRegistry

COLOR_TWITCH = 0x9146FF
COLOR_EVENT = 0xF59E0B


def register_twitch_unified_feed(client, tree, data_dir):

    registry = DropRegistry(data_dir)

    @tree.command(
        name="twitchfeed",
        description="Unified Twitch feed (badges + active drops)."
    )
    async def twitchfeed(interaction: discord.Interaction):

        await interaction.response.defer(thinking=True)

        badges = twitch_service.get_cached_badges()
        drops = registry.get_active()

        embeds = []

        # -------------------------
        # BADGES
        # -------------------------
        if badges:

            badge_titles = [
                f"• {b.get('title','Unknown')}"
                for b in badges[:3]
            ]

            e = discord.Embed(
                title="👩‍💻 Twitch Global Badges",
                description="\n".join(badge_titles),
                color=COLOR_TWITCH
            )

            if badges[0].get("img"):
                e.set_thumbnail(url=badges[0]["img"])

            e.set_footer(text=f"{len(badges)} cached badges")

            embeds.append(e)

        # -------------------------
        # DROPS
        # -------------------------
        if drops:

            drop_lines = [
                f"• **{d.get('game','Unknown')}** — {d.get('campaign','')}"
                for d in drops[:5]
            ]

            e2 = discord.Embed(
                title="🎁 Active Twitch Drops",
                description="\n".join(drop_lines),
                color=COLOR_EVENT
            )

            e2.set_footer(text=f"{len(drops)} active campaigns")

            embeds.append(e2)

        # -------------------------
        # EMPTY STATE
        # -------------------------
        if not embeds:
            await interaction.followup.send(
                "Twitch data is not available yet. Please try again shortly."
            )
            return

        await interaction.followup.send(embeds=embeds)

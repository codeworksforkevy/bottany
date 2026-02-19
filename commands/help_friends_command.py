
import discord
from discord import app_commands


def register(bot):

    @bot.tree.command(name="help_friends", description="Show help for the Twitch watch system")
    async def help_friends(interaction: discord.Interaction):

        embed = discord.Embed(
            title="🔴 Twitch Stream Watch System",
            description=(
                "This feature allows Bottany to automatically post a message "
                "in a Discord channel when selected Twitch streamers go live.\n\n"
                "Bottany listens to official Twitch EventSub notifications in real time.\n\n"
                "If you encounter any issues, please contact Sim."
            ),
            color=0x9146FF
        )

        embed.add_field(
            name="🇳🇱 Vlaamse Versie",
            value=(
                "Deze functie laat Bottany automatisch een bericht plaatsen "
                "in een Discord-kanaal wanneer geselecteerde Twitch-streamers live gaan.\n\n"
                "Bottany luistert in real-time naar officiële Twitch EventSub-meldingen.\n\n"
                "Als je problemen ondervindt, neem dan contact op met Sim."
            ),
            inline=False
        )

        embed.set_footer(text="Bottany Twitch System — Production Ready")

        await interaction.response.send_message(embed=embed, ephemeral=False)

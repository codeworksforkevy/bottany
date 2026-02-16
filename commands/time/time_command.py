
import discord
from discord import app_commands
from .time_api import TimeAPI


async def register(bot, data_dir):

    api = TimeAPI(data_dir)
    api.load_cache()

    # Refresh timezone list if empty
    if not api.timezones:
        try:
            await api.fetch_timezones()
        except Exception:
            pass

    async def timezone_autocomplete(
        interaction: discord.Interaction,
        current: str,
    ):
        if not api.timezones:
            return []

        filtered = [
            tz for tz in api.timezones
            if current.lower() in tz.lower()
        ][:25]

        return [
            app_commands.Choice(name=tz, value=tz)
            for tz in filtered
        ]

    @bot.tree.command(
        name="time",
        description="Get current local time for any timezone"
    )
    @app_commands.describe(
        timezone="Select a timezone (e.g., Europe/Istanbul)"
    )
    @app_commands.autocomplete(timezone=timezone_autocomplete)
    async def time_command(
        interaction: discord.Interaction,
        timezone: str
    ):

        data = await api.get_time(timezone)

        if not data:
            await interaction.response.send_message(
                "Unable to retrieve time.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"🕒 {data['timeZone']}",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="Local Time",
            value=f"{data['hour']:02}:{data['minute']:02}:{data['seconds']:02}",
            inline=False
        )

        embed.add_field(
            name="Day",
            value=data["dayOfWeek"],
            inline=True
        )

        embed.add_field(
            name="DST Active",
            value="Yes" if data["dstActive"] else "No",
            inline=True
        )

        await interaction.response.send_message(embed=embed)

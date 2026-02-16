import discord
from discord import app_commands
import asyncio
import logging
from .time_api import TimeAPI

logger = logging.getLogger("bottany.time")

# Country → canonical timezone map
COUNTRY_FALLBACK = {
    "turkey": "Europe/Istanbul",
    "italy": "Europe/Rome",
    "belgium": "Europe/Brussels",
    "japan": "Asia/Tokyo",
    "germany": "Europe/Berlin",
    "france": "Europe/Paris",
    "spain": "Europe/Madrid",
    "united kingdom": "Europe/London",
    "uk": "Europe/London",
    "usa": "America/New_York",
    "united states": "America/New_York",
    "canada": "America/Toronto",
    "australia": "Australia/Sydney",
    "sweden": "Europe/Stockholm",
}


async def register(bot, data_dir):

    api = TimeAPI(data_dir)
    api.load_cache()

    # -------------------------------------------------
    # INITIAL FETCH
    # -------------------------------------------------
    if not api.timezones:
        try:
            await api.fetch_timezones()
            logger.info("Initial timezone list fetched.")
        except Exception as e:
            logger.warning("Initial timezone fetch failed: %s", e)

    if not api.timezones:
        logger.warning("Timezone list is empty after initialization.")

    # -------------------------------------------------
    # AUTO REFRESH TASK (24h)
    # -------------------------------------------------
    async def refresh_task():
        await bot.wait_until_ready()
        while not bot.is_closed():
            await asyncio.sleep(86400)  # 24 hours
            try:
                await api.fetch_timezones()
                logger.info("Timezone list auto-refreshed.")
            except Exception as e:
                logger.warning("Auto-refresh failed: %s", e)

    bot.loop.create_task(refresh_task())

    # -------------------------------------------------
    # AUTOCOMPLETE
    # -------------------------------------------------
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

    # -------------------------------------------------
    # SMART RESOLVE
    # -------------------------------------------------
    def resolve_timezone(user_input: str):

        if not api.timezones:
            return None

        key = user_input.lower().strip()

        # 1️⃣ Direct full match
        for tz in api.timezones:
            if tz.lower() == key:
                return tz

        # 2️⃣ Exact city match (after slash)
        for tz in api.timezones:
            city_part = tz.split("/")[-1].lower()
            if city_part == key:
                return tz

        # 3️⃣ Partial match
        for tz in api.timezones:
            if key in tz.lower():
                return tz

        # 4️⃣ Country fallback
        if key in COUNTRY_FALLBACK:
            return COUNTRY_FALLBACK[key]

        return None

    # -------------------------------------------------
    # COMMAND
    # -------------------------------------------------
    @bot.tree.command(
        name="time",
        description="Get current time by timezone or country"
    )
    @app_commands.describe(
        timezone="Enter timezone (Europe/Istanbul) or city (Stockholm) or country (Sweden)"
    )
    @app_commands.autocomplete(timezone=timezone_autocomplete)
    async def time_command(
        interaction: discord.Interaction,
        timezone: str
    ):

        resolved = resolve_timezone(timezone)

        if not resolved:
            await interaction.response.send_message(
                f"Unknown location: {timezone}",
                ephemeral=True
            )
            return

        data = await api.get_time(resolved)

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


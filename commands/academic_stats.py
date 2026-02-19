import discord
from discord import app_commands
from services.trivia_memory_pg import stats


async def register(bot, data_dir):

    guild = discord.Object(id=1446560723122520207)

    @bot.tree.command(
        name="academic_stats",
        description="View academic distribution statistics",
        guild=guild
    )
    async def academic_stats(interaction: discord.Interaction):

        data = stats()

        embed = discord.Embed(
            title="Academic Distribution Engine Stats",
            color=0x5865F2
        )

        embed.add_field(
            name="Tracked Entries",
            value=str(data["tracked_entries"]),
            inline=False
        )

        embed.add_field(
            name="Total Distribution Score",
            value=str(round(data["total_score"], 2)),
            inline=False
        )

        embed.add_field(
            name="Active Fields",
            value=str(data["diversity_count"]),
            inline=False
        )

        # Field diversity breakdown
        if data["field_distribution"]:
            field_text = "\n".join(
                f"{field} → {percent}%"
                for field, percent in data["field_distribution"][:8]
            )
        else:
            field_text = "No data yet."

        embed.add_field(
            name="Field Diversity %",
            value=field_text,
            inline=False
        )

        await interaction.response.send_message(embed=embed)

import discord
from discord import app_commands
from services.trivia_memory_pg import stats, TARGET_FIELD_RATIO


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

        # ------------------------------
        # Core Metrics
        # ------------------------------
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

        # ------------------------------
        # Entropy & Health
        # ------------------------------
        embed.add_field(
            name="Entropy Score",
            value=str(data["entropy_score"]),
            inline=True
        )

        embed.add_field(
            name="Distribution Health %",
            value=f"{data['health_percent']}%",
            inline=True
        )

        embed.add_field(
            name="Target Field Ratio",
            value=f"{int(TARGET_FIELD_RATIO * 100)}%",
            inline=True
        )

        # ------------------------------
        # Field Diversity Breakdown
        # ------------------------------
        if data["field_distribution"]:

            field_lines = []
            dominance_warning = False

            for field, percent in data["field_distribution"][:10]:

                field_upper = field.upper()
                field_lines.append(f"{field_upper} → {percent}%")

                if percent > TARGET_FIELD_RATIO * 100:
                    dominance_warning = True

            field_text = "\n".join(field_lines)

        else:
            field_text = "No field data yet."
            dominance_warning = False

        embed.add_field(
            name="Field Diversity %",
            value=field_text,
            inline=False
        )

        # ------------------------------
        # Dominance Warning
        # ------------------------------
        if dominance_warning:
            embed.add_field(
                name="⚠ Field Dominance Warning",
                value="One or more fields exceed the target diversity ratio.",
                inline=False
            )

        await interaction.response.send_message(embed=embed)


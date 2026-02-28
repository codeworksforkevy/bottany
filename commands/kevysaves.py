from __future__ import annotations

import discord
from discord import app_commands


def register(bot):

    group = app_commands.Group(
        name="kevysaves",
        description="Kevy saves puppies."
    )

    # -----------------------------------------
    # MAIN COMMAND
    # -----------------------------------------
    @group.command(name="apuppieagain")
    async def save_puppie(interaction: discord.Interaction):

        user_id = interaction.user.id

        async with bot.db.acquire() as conn:

            # Insert or update atomically
            await conn.execute("""
                INSERT INTO kevy_saves (user_id, save_count)
                VALUES ($1, 1)
                ON CONFLICT (user_id)
                DO UPDATE SET save_count = kevy_saves.save_count + 1;
            """, user_id)

            # Get user's new count
            user_count = await conn.fetchval("""
                SELECT save_count FROM kevy_saves
                WHERE user_id = $1
            """, user_id)

            # Get global total
            global_total = await conn.fetchval("""
                SELECT COALESCE(SUM(save_count), 0)
                FROM kevy_saves
            """)

        message = (
            "Kevy saved an another puppie. It wasn't a suprise.\n"
            f"🐶 You saved: {user_count}\n"
            f"🌍 Global saves: {global_total}"
        )

        await interaction.response.send_message(message)

    # -----------------------------------------
    # LEADERBOARD
    # -----------------------------------------
    @group.command(name="leaderboard")
    async def leaderboard(interaction: discord.Interaction):

        async with bot.db.acquire() as conn:

            rows = await conn.fetch("""
                SELECT user_id, save_count
                FROM kevy_saves
                ORDER BY save_count DESC
                LIMIT 10
            """)

        if not rows:
            await interaction.response.send_message(
                "No puppies saved yet."
            )
            return

        embed = discord.Embed(
            title="🐶 Kevy Global Puppy Leaderboard",
            color=0xF5C542
        )

        for index, row in enumerate(rows, start=1):
            user = interaction.guild.get_member(row["user_id"])
            name = user.display_name if user else f"User {row['user_id']}"

            embed.add_field(
                name=f"#{index} {name}",
                value=f"{row['save_count']} puppies",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    bot.tree.add_command(group)

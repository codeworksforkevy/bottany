from __future__ import annotations

import random
import discord
from discord import app_commands

COOLDOWN_SECONDS = 30

TIERS = [
    (500, "Mythic", "Puppy Savior", 0xF1C40F),
    (150, "Epic", "Legendary Rescuer", 0x9B59B6),
    (50, "Rare", "Shelter Guardian", 0x3498DB),
    (10, "Uncommon", "Street Rescuer", 0x2ECC71),
    (1, "Common", "Puppy Helper", 0x95A5A6),
]


def resolve_tier(count: int):
    for min_count, tier_name, role_name, color in TIERS:
        if count >= min_count:
            return {
                "tier": tier_name,
                "role": role_name,
                "color": color
            }
    return None


def check_rare_drop():
    return random.random() < 0.05


def register(bot):

    group = app_commands.Group(
        name="kevysaves",
        description="Kevy saves puppies."
    )

    # -----------------------------------------
    # SAVE COMMAND
    # -----------------------------------------
    @group.command(name="apuppieagain")
    @app_commands.checks.cooldown(1, COOLDOWN_SECONDS)
    async def save_puppie(interaction: discord.Interaction):

        guild_id = interaction.guild.id
        user_id = interaction.user.id

        async with bot.db.acquire() as conn:

            await conn.execute("""
                INSERT INTO kevy_saves (guild_id, user_id, save_count)
                VALUES ($1, $2, 1)
                ON CONFLICT (guild_id, user_id)
                DO UPDATE SET save_count = kevy_saves.save_count + 1;
            """, guild_id, user_id)

            user_count = await conn.fetchval("""
                SELECT save_count FROM kevy_saves
                WHERE guild_id = $1 AND user_id = $2
            """, guild_id, user_id)

            global_total = await conn.fetchval("""
                SELECT COALESCE(SUM(save_count), 0)
                FROM kevy_saves
                WHERE guild_id = $1
            """, guild_id)

            old_tier = await conn.fetchval("""
                SELECT tier FROM kevy_saves
                WHERE guild_id = $1 AND user_id = $2
            """, guild_id, user_id)

            tier_data = resolve_tier(user_count)

            await conn.execute("""
                UPDATE kevy_saves
                SET tier = $1
                WHERE guild_id = $2 AND user_id = $3
            """, tier_data["tier"], guild_id, user_id)

        # Role Sync
        await sync_role(interaction.user, tier_data)

        # Tier Announcement
        if old_tier != tier_data["tier"]:
            await interaction.channel.send(
                f"🎉 {interaction.user.mention} reached **{tier_data['tier']} Tier!**"
            )

        # Rare Drop
        if check_rare_drop():
            async with bot.db.acquire() as conn:
                await conn.execute("""
                    UPDATE kevy_saves
                    SET save_count = save_count + 5
                    WHERE guild_id = $1 AND user_id = $2
                """, guild_id, user_id)

            await interaction.channel.send(
                "✨ A Rare Golden Puppie appeared! +5 bonus help!"
            )

        embed = discord.Embed(
            title="🐶 Kevy Saves a Puppie Again",
            description="Kevy saved an another puppie. It wasn't a suprise.",
            color=tier_data["color"]
        )

        embed.add_field(name="You helped", value=str(user_count))
        embed.add_field(name="Server total helped", value=str(global_total))
        embed.add_field(name="Tier", value=tier_data["tier"])

        await interaction.response.send_message(embed=embed)

    # -----------------------------------------
    # LEADERBOARD
    # -----------------------------------------
    @group.command(name="leaderboard")
    async def leaderboard(interaction: discord.Interaction):

        guild_id = interaction.guild.id

        async with bot.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT user_id, save_count
                FROM kevy_saves
                WHERE guild_id = $1
                ORDER BY save_count DESC
                LIMIT 10
            """, guild_id)

        embed = discord.Embed(
            title="🐶 Server Puppy Leaderboard",
            color=0xF5C542
        )

        for i, row in enumerate(rows, start=1):
            member = interaction.guild.get_member(row["user_id"])
            name = member.display_name if member else f"User {row['user_id']}"
            embed.add_field(
                name=f"#{i} {name}",
                value=f"{row['save_count']} helped",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    bot.tree.add_command(group)


async def sync_role(member: discord.Member, tier_data: dict):

    guild = member.guild
    role_name = tier_data["role"]

    role = discord.utils.get(guild.roles, name=role_name)

    if role is None:
        role = await guild.create_role(name=role_name)

    tier_role_names = [t[2] for t in TIERS]

    for r in member.roles:
        if r.name in tier_role_names and r.name != role_name:
            await member.remove_roles(r)

    await member.add_roles(role)

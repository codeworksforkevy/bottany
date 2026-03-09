from __future__ import annotations

import random
import logging
import discord
from discord import app_commands

logger = logging.getLogger("bottany")

COOLDOWN_SECONDS = 30

ROMAN = ["I", "II", "III", "IV", "V"]

TIERS = [
    (500, "Mythic", "Puppy Savior", 0xF1C40F),
    (150, "Epic", "Legendary Puppie Rescuer", 0x9B59B6),
    (50, "Rare", "Guardian of Puppies", 0x3498DB),
    (10, "Uncommon", "Puppie Rescuer", 0x2ECC71),
    (1, "Common", "Puppie Helper", 0x95A5A6),
]


# =================================================
# TIER RESOLVER
# =================================================

def resolve_tier(count: int):
    for index, (min_count, tier_name, role_name, color) in enumerate(TIERS, start=1):
        if count >= min_count:
            tier_number = len(TIERS) - index + 1
            return {
                "tier": tier_name,
                "tier_number": tier_number,
                "role": role_name,
                "color": color
            }
    return None


def check_rare_drop():
    return random.random() < 0.05


# =================================================
# REGISTER
# =================================================

def register(bot):

    group = app_commands.Group(
        name="kevysaves",
        description="Kevy saves puppies."
    )

    # =================================================
    # SAVE COMMAND
    # =================================================

    @group.command(name="apuppieagain")
    @app_commands.checks.cooldown(1, COOLDOWN_SECONDS)
    async def save_puppie(interaction: discord.Interaction):

        if interaction.guild is None:
            await interaction.response.send_message(
                "This command can only be used in servers.",
                ephemeral=True
            )
            return

        guild_id = interaction.guild.id
        user_id = interaction.user.id

        try:
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

        except Exception:
            logger.exception("Kevy DB error")
            await interaction.response.send_message(
                "Database error occurred.",
                ephemeral=True
            )
            return

        # =================================================
        # ROLE SYNC
        # =================================================

        member = interaction.guild.get_member(user_id)

        if member:
            try:
                await sync_role(member, tier_data)
            except Exception:
                logger.exception("Role sync failed")

        # =================================================
        # TIER ANNOUNCEMENT
        # =================================================

        if old_tier != tier_data["tier"]:
            await interaction.channel.send(
                f"⚔ {interaction.user.mention} has ascended to **{tier_data['role']}**!"
            )

        # =================================================
        # RARE DROP
        # =================================================

        if check_rare_drop():
            try:
                async with bot.db.acquire() as conn:
                    await conn.execute("""
                        UPDATE kevy_saves
                        SET save_count = save_count + 5
                        WHERE guild_id = $1 AND user_id = $2
                    """, guild_id, user_id)

                    user_count += 5

                await interaction.channel.send(
                    "✨ A Rare Golden Puppie appeared! +5 bonus help!"
                )
            except Exception:
                logger.exception("Rare drop update failed")

        # =================================================
        # EMBED
        # =================================================

        embed = discord.Embed(
            title="🐶 Puppy Rescue Stats",
            color=tier_data["color"]
        )

        embed.add_field(
            name="🐶 You Helped",
            value=f"**{user_count}** puppies",
            inline=True
        )

        embed.add_field(
            name="🐾 Server's Help",
            value=f"**{global_total}** puppies",
            inline=True
        )

        embed.add_field(
            name="🐕 Tier",
            value=f"**{ROMAN[tier_data['tier_number'] - 1]}**",
            inline=False
        )

        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        embed.set_footer(
            text="🐶 You helped puppies • 🐾 Server's help grows • 🐕 You climb the tiers"
        )

        await interaction.response.send_message(embed=embed)

    # =================================================
    # COOLDOWN ERROR
    # =================================================

    @save_puppie.error
    async def save_error(interaction: discord.Interaction, error):

        if isinstance(error, app_commands.errors.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏳ Wait {int(error.retry_after)} seconds before helping again.",
                ephemeral=True
            )
        else:
            logger.exception("Kevy command crashed")
            try:
                await interaction.response.send_message(
                    "Unexpected error occurred.",
                    ephemeral=True
                )
            except:
                pass

    # =================================================
    # LEADERBOARD
    # =================================================

    @group.command(name="leaderboard")
    async def leaderboard(interaction: discord.Interaction):

        if interaction.guild is None:
            await interaction.response.send_message(
                "Server only command.",
                ephemeral=True
            )
            return

        guild_id = interaction.guild.id

        try:
            async with bot.db.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT user_id, save_count
                    FROM kevy_saves
                    WHERE guild_id = $1
                    ORDER BY save_count DESC
                    LIMIT 10
                """, guild_id)
        except Exception:
            logger.exception("Leaderboard query failed")
            await interaction.response.send_message(
                "Database error.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🐾 Puppy Rescue Leaderboard",
            color=0xF5C542
        )

        for i, row in enumerate(rows, start=1):
            member = interaction.guild.get_member(row["user_id"])
            name = member.display_name if member else f"User {row['user_id']}"

            embed.add_field(
                name=f"🐶 #{i} {name}",
                value=f"{row['save_count']} puppies helped",
                inline=False
            )

        embed.set_footer(
            text="🐶 You helped puppies • 🐾 Server's help grows • 🐕 You climb the tiers"
        )

        await interaction.response.send_message(embed=embed)

    bot.tree.add_command(group)


# =================================================
# SAFE ROLE SYNC
# =================================================

async def sync_role(member: discord.Member, tier_data: dict):

    guild = member.guild
    role_name = tier_data["role"]

    role = discord.utils.get(guild.roles, name=role_name)

    if role is None:
        logger.warning("Role %s not found in guild %s", role_name, guild.name)
        return

    tier_role_names = [t[2] for t in TIERS]

    for r in member.roles:
        if r.name in tier_role_names and r.name != role_name:
            try:
                await member.remove_roles(r)
            except Exception:
                logger.exception("Failed removing role %s", r.name)

    if role not in member.roles:
        try:
            await member.add_roles(role)
        except Exception:
            logger.exception("Failed adding role %s", role_name)

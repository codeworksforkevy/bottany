from __future__ import annotations

import random
import logging
import discord
from discord import app_commands
from datetime import datetime

logger = logging.getLogger("bottany")

COOLDOWN_SECONDS = 20

ROMAN = ["I", "II", "III", "IV", "V"]

# =================================================
# RANDOM KITTY MESSAGES
# =================================================

KITTY_MESSAGES = [

    "🐱 You gave kittens a treat, purring sounds is the company.",
    "🐾 Pet and hug a kittie!",
    "🐱 You are just petting a kittie, want to adopt them as well?",
    "🐅 3 kittens in one hug!",
    "🐈 The kitten rolls over for belly rubs.",
    "🐾 The kitten accepts your friendship.",
    "🐱 The kitten stares at you, then blinks."
]

# =================================================
# TIERS
# =================================================

KITTY_TIERS = [

    (500, "True Friend of Animals", 0xF39C12),
    (150, "Friend of the Animals", 0x9B59B6),
    (50, "Deep Cat Love", 0x3498DB),
    (10, "Kitten Companion", 0x2ECC71),
    (1, "Cats", 0x95A5A6),
]

# =================================================
# MILESTONE ACHIEVEMENTS
# =================================================

MILESTONES = {

    1: "First Purr",
    10: "Kitten Companion",
    50: "Certified Cat Friend",
    100: "Seen Too Much",
    500: "True Friend of Animals"
}

# =================================================
# EVENT ACHIEVEMENTS
# =================================================

EVENTS = {

    "Wrong Cat": "🦁 Wait... that's not a kitten.\nYou accidentally pet a lion.",
    "Murder Mitten": "🐱 The kitten bites your finger.",
    "Chosen by Cats": "👑 All kittens suddenly gather around you."
}


# =================================================
# TIER RESOLVER
# =================================================

def resolve_tier(count: int):

    for index, (min_count, name, color) in enumerate(KITTY_TIERS, start=1):

        if count >= min_count:

            tier_number = len(KITTY_TIERS) - index + 1

            return {
                "tier": name,
                "tier_number": tier_number,
                "color": color
            }

    return None


# =================================================
# REGISTER
# =================================================

def register(bot):

    @bot.tree.command(name="petakitten", description="Pet a cute kitten.")
    @app_commands.checks.cooldown(1, COOLDOWN_SECONDS)

    async def pet_kitten(interaction: discord.Interaction):

        if interaction.guild is None:

            await interaction.response.send_message(
                "Server only command.",
                ephemeral=True
            )
            return

        guild_id = interaction.guild.id
        user_id = interaction.user.id

        try:

            async with bot.db.acquire() as conn:

                await conn.execute("""
                    INSERT INTO kitten_pets (guild_id, user_id, pet_count, achievements)
                    VALUES ($1,$2,1,ARRAY[]::TEXT[])
                    ON CONFLICT (guild_id,user_id)
                    DO UPDATE SET pet_count = kitten_pets.pet_count + 1
                """, guild_id, user_id)

                user_count = await conn.fetchval("""
                    SELECT pet_count
                    FROM kitten_pets
                    WHERE guild_id=$1 AND user_id=$2
                """, guild_id, user_id)

                server_total = await conn.fetchval("""
                    SELECT COALESCE(SUM(pet_count),0)
                    FROM kitten_pets
                    WHERE guild_id=$1
                """, guild_id)

                old_tier = await conn.fetchval("""
                    SELECT tier
                    FROM kitten_pets
                    WHERE guild_id=$1 AND user_id=$2
                """, guild_id, user_id)

                achievements = await conn.fetchval("""
                    SELECT achievements
                    FROM kitten_pets
                    WHERE guild_id=$1 AND user_id=$2
                """, guild_id, user_id)

                if achievements is None:
                    achievements = []

                tier_data = resolve_tier(user_count)

                await conn.execute("""
                    UPDATE kitten_pets
                    SET tier=$1
                    WHERE guild_id=$2 AND user_id=$3
                """, tier_data["tier"], guild_id, user_id)

        except Exception:

            logger.exception("Kitten DB error")

            await interaction.response.send_message(
                "Database error occurred.",
                ephemeral=True
            )
            return

        # =================================================
        # TIER ANNOUNCEMENT
        # =================================================

        if old_tier != tier_data["tier"]:

            await interaction.channel.send(
                f"🐅 {interaction.user.mention} reached **{tier_data['tier']}**!"
            )

        # =================================================
        # RANDOM MESSAGE
        # =================================================

        random_text = random.choice(KITTY_MESSAGES)

        # =================================================
        # RANDOM EVENTS
        # =================================================

        achievement_unlocked = None

        event_roll = random.randint(1,100)

        if event_roll <= 5 and "Wrong Cat" not in achievements:

            achievement_unlocked = "Wrong Cat"
            random_text = EVENTS["Wrong Cat"]

        elif event_roll <= 10 and "Murder Mitten" not in achievements:

            achievement_unlocked = "Murder Mitten"
            random_text = EVENTS["Murder Mitten"]

        elif event_roll <= 12 and "Chosen by Cats" not in achievements:

            achievement_unlocked = "Chosen by Cats"
            random_text = EVENTS["Chosen by Cats"]

        # =================================================
        # NIGHT CAT
        # =================================================

        hour = datetime.utcnow().hour

        if 0 <= hour <= 6 and "Night Cat" not in achievements:

            achievement_unlocked = "Night Cat"

        # =================================================
        # MILESTONE CHECK
        # =================================================

        if user_count in MILESTONES and MILESTONES[user_count] not in achievements:

            achievement_unlocked = MILESTONES[user_count]

        # =================================================
        # SAVE ACHIEVEMENT
        # =================================================

        if achievement_unlocked:

            async with bot.db.acquire() as conn:

                await conn.execute("""

                    UPDATE kitten_pets
                    SET achievements = array_append(achievements,$1)
                    WHERE guild_id=$2 AND user_id=$3

                """, achievement_unlocked, guild_id, user_id)

            await interaction.channel.send(
                f"🏆 **Achievement unlocked:** {achievement_unlocked}\n{interaction.user.mention}"
            )

        # =================================================
        # EMBED
        # =================================================

        embed = discord.Embed(
            title="🐱 Pet a Kitten",
            description=random_text,
            color=tier_data["color"]
        )

        embed.add_field(
            name="🐱 Your Interaction",
            value=f"**{user_count}**",
            inline=True
        )

        embed.add_field(
            name="🐾 Server's Help",
            value=f"**{server_total}**",
            inline=True
        )

        embed.add_field(
            name="🦁 Tier",
            value=f"**{ROMAN[tier_data['tier_number']-1]}**",
            inline=False
        )

        await interaction.response.send_message(embed=embed)


    # =================================================
    # COOLDOWN ERROR
    # =================================================

    @pet_kitten.error
    async def pet_error(interaction: discord.Interaction, error):

        if isinstance(error, app_commands.errors.CommandOnCooldown):

            await interaction.response.send_message(
                f"🐾 The kittens are resting. Try again in {int(error.retry_after)} seconds.",
                ephemeral=True
            )

        else:

            logger.exception("Kitten command crashed")

            try:
                await interaction.response.send_message(
                    "Unexpected error occurred.",
                    ephemeral=True
                )
            except:
                pass

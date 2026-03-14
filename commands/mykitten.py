from __future__ import annotations

import random
import logging
import discord
from discord import app_commands
from datetime import datetime

logger = logging.getLogger("bottany")

# =================================================
# COOLDOWN
# =================================================
COOLDOWN_SECONDS = 20

# =================================================
# JOKE / SCENARIO DATASET
# =================================================
KITTEN_SCENARIOS = [
    # Daily / Home Adventures
    "{} knocked over your plant pot. The cat looks innocent. Could it be tho?",
    "Your kitten stares at the void. The void stares back.",
    "{} sat on your keyboard again. You can't kill anyone in CS2 anymore. In fact, a fight started in the team about kicking you :O",
    "Kitten blocked your keyboard. You can't type that important message.",
    "Your kitten sabotaged the raffle chances again, and guess what? Jordan won again!",
    "The kitten entered the carrier. Against its will.",
    "Kitten forgave you after the stress of the vet visit. Eventually.",
    # Legendary Lore
    "This kitten once stared at a black hole. The black hole blinked first.",
    "Your kitten briefly understood the structure of the universe. Then it chased a toy.",
    # Interactive / Choice
    "The kitten is trying to drink from your glass. Will you let it?",
    "Important question: Would you buy an expensive automatic litter box? Or a water fountain? :O"
]

# Global Events
GLOBAL_EVENTS = [
    "🌍 At exactly midnight, every kitten runs across the house simultaneously. Hopefully neighbors are okay.",
    "🎧 All kittens today chewed through headphone cables!",
    "🥫 Demand for wet food continues in every household.",
    "🛋 Cozy cat-human time brought happiness today."
]

# =================================================
# REGISTER
# =================================================
def register(bot):

    @bot.tree.command(name="mykitten", description="See what your adopted kitten is up to today!")
    @app_commands.checks.cooldown(1, COOLDOWN_SECONDS)
    @app_commands.describe(kitten_name="Optional: select a specific kitten you adopted")
    async def mykitten(interaction: discord.Interaction, kitten_name: str = None):
        if interaction.guild is None:
            await interaction.response.send_message("Server only command.", ephemeral=True)
            return

        guild_id = interaction.guild.id
        user_id = interaction.user.id

        try:
            async with bot.db.acquire() as conn:
                # Get user's kittens
                kittens = await conn.fetch(
                    """
                    SELECT kitten_name
                    FROM kitten_adoptions
                    WHERE guild_id=$1 AND user_id=$2
                    """,
                    guild_id, user_id
                )

                if not kittens:
                    await interaction.response.send_message(
                        "You haven't adopted any kittens yet! Use `/kittenadoption` first.",
                        ephemeral=True
                    )
                    return

                # Select kitten
                if kitten_name:
                    selected = next((k['kitten_name'] for k in kittens if k['kitten_name'].lower() == kitten_name.lower()), None)
                    if not selected:
                        selected = kittens[0]['kitten_name']
                else:
                    selected = random.choice(kittens)['kitten_name']

                # Random scenario
                scenario = random.choice(KITTEN_SCENARIOS)
                scenario_text = scenario.format(selected) if "{}" in scenario else scenario

                # Global Event chance (%8)
                global_event_text = None
                if random.randint(1, 100) <= 8:
                    global_event_text = random.choice(GLOBAL_EVENTS)

        except Exception:
            logger.exception("MyKitten DB error")
            await interaction.response.send_message("Database error occurred.", ephemeral=True)
            return

        # =================================================
        # Embed
        # =================================================
        embed = discord.Embed(
            title=f"🐱 {selected}'s Daily Scenario",
            description=scenario_text,
            color=0xFFD700
        )

        embed.add_field(
            name="Owner",
            value=interaction.user.mention,
            inline=True
        )

        embed.add_field(
            name="Total adopted kittens",
            value=str(len(kittens)),
            inline=True
        )

        if global_event_text:
            embed.add_field(
                name="🌐 Global Kitten Event",
                value=global_event_text,
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    # =================================================
    # COOLDOWN ERROR
    # =================================================
    @mykitten.error
    async def mykitten_error(interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.CommandOnCooldown):
            await interaction.response.send_message(
                f"🐾 Your kittens are resting. Try again in {int(error.retry_after)} seconds.",
                ephemeral=True
            )
        else:
            logger.exception("MyKitten command crashed")
            try:
                await interaction.response.send_message(
                    "Unexpected error occurred.",
                    ephemeral=True
                )
            except:
                pass

from __future__ import annotations
import random
import logging
import discord
from discord import app_commands
from datetime import datetime

logger = logging.getLogger("bottany")
COOLDOWN_SECONDS = 20

# =================================================
# SCENARIOS / JOKES / LEGENDARY
# =================================================

KITTEN_SCENARIOS = [
    "{} knocked over your plant pot. The cat looks innocent. Could it be tho?",
    "Your kitten stares at the void. The void stares back.",
    "{} sat on your keyboard again. You can't kill anyone in CS2 anymore. In fact a fight started in the team about kicking you :O",
    "Kitten blocked your keyboard. You can't type that important message.",
    "Your kitten sabotaged the raffle chances again, and guess what? Jordan won again!",
    "The kitten entered the carrier. Against its will (to vet visit).",
    "Kitten forgave you after the stress of the vet visit. Eventually.",
    "This kitten once stared at a black hole. The black hole blinked first.",
    "Your kitten briefly understood the structure of the universe. Then it chased a toy.",
    "The kitten is trying to drink from your glass. Will you let {}?",
    "Important question: Would you buy an expensive automatic litter box? Or a water fountain? :O",
    "Every time {} purrs, an electron somewhere changes direction.",
    "The kitten knocked over your pens. You finally found the pen you've been wondering about for a while. Plus, the kitten brought you one of your AirPods with its paw.",
    "{} started playing games late at night. Hopefully the neighbors don't report us.",
    "A kitten infiltrated Jordan's computer. Jordan's raffle win probability decreased by %0.0001. (Still extremely high, but it's a start!)",
    "{}, deleted the 'Subscriber Goal' with a single paw strike. Now everyone watches for free!",
    "{} used your computer to order the most expensive wet food, premium kibble, and gourmet cat treats available online."
]

LEGENDARY_LORE = [
    "🌌 Legendary Kitten Lore\n\nThis kitten once stared at a black hole.\nThe black hole blinked first.",
    "📜 Legendary Kitten Lore\n\nAncient scholars wrote about a cosmic kitten.\nThey were not joking.",
    "🪐 Legendary Kitten Lore\n\nYour kitten briefly understood the structure of the universe.\nIt immediately forgot and chased a dust particle.",
    "⚡ Legendary Kitten Lore\n\nWhen the universe was young, a kitten stepped on the keyboard of reality.\nThat is why chaos exists.",
    "🌠 Legendary Kitten Lore\n\nSome say every galaxy contains a kitten.\nScientists are still investigating."
]

GLOBAL_EVENTS = [
    "🌍 At exactly midnight, every kitten runs across the house simultaneously. Hopefully neighbors are okay.",
    "🎧 All kittens today chewed through headphone cables!",
    "🥫 Demand for wet food continues in every household.",
    "🛋 Cozy cat-human time brought happiness today.",
    "🌌 At midnight, every kitten simultaneously yawned. The universe sighed back."
]

# =================================================
# GLOBAL EVENT SYSTEM (SERVER-WIDE)
# =================================================

async def get_or_create_global_event(conn, guild_id):

    row = await conn.fetchrow("""
        SELECT event_text, last_event
        FROM kitten_global_events
        WHERE guild_id=$1
    """, guild_id)

    today = datetime.utcnow().date()

    if row is None or row["last_event"] is None or row["last_event"].date() < today:

        event_text = random.choice(GLOBAL_EVENTS)

        await conn.execute("""
            INSERT INTO kitten_global_events (guild_id, event_text, last_event)
            VALUES ($1,$2,NOW())
            ON CONFLICT (guild_id)
            DO UPDATE SET event_text=$2, last_event=NOW()
        """, guild_id, event_text)

        return event_text

    return row["event_text"]

# =================================================
# REGISTER COMMAND
# =================================================

def register(bot):

    @bot.tree.command(name="mykitten", description="See what your adopted kitten is up to today!")
    @app_commands.checks.cooldown(1, COOLDOWN_SECONDS)

    async def mykitten(interaction: discord.Interaction, kitten_name: str = None):

        if interaction.guild is None:
            await interaction.response.send_message("Server only command.", ephemeral=True)
            return

        guild_id = interaction.guild.id
        user_id = interaction.user.id

        try:
            async with bot.db.acquire() as conn:

                kittens = await conn.fetch("""
                    SELECT kitten_name
                    FROM kitten_adoptions
                    WHERE guild_id=$1 AND user_id=$2
                """, guild_id, user_id)

                if not kittens:
                    await interaction.response.send_message(
                        "You haven't adopted any kittens yet! Use `/kittenadoption` first.",
                        ephemeral=True
                    )
                    return

                # Select kitten
                if kitten_name:
                    selected = next(
                        (k['kitten_name'] for k in kittens if k['kitten_name'].lower() == kitten_name.lower()),
                        None
                    )
                    if not selected:
                        selected = kittens[0]['kitten_name']
                else:
                    selected = random.choice(kittens)['kitten_name']

                # Scenario or Legendary
                if random.randint(1, 100) <= 5:
                    scenario_text = random.choice(LEGENDARY_LORE)
                else:
                    scenario = random.choice(KITTEN_SCENARIOS)
                    scenario_text = scenario.format(selected) if "{}" in scenario else scenario

                # SERVER-WIDE GLOBAL EVENT
                global_event_text = await get_or_create_global_event(conn, guild_id)

        except Exception:
            logger.exception("MyKitten DB error")
            await interaction.response.send_message("Database error occurred.", ephemeral=True)
            return

        # =================================================
        # EMBED
        # =================================================

        embed = discord.Embed(
            title=f"🐱 What is {selected} Up To?",
            description=f"ദ്ദി/ᐠ｡‸｡ᐟ\\\n\n{scenario_text}",
            color=0x89CFF0 # Baby Blue
        )

        embed.add_field(name="Owner", value=interaction.user.mention, inline=True)
        embed.add_field(name="Total adopted kittens", value=str(len(kittens)), inline=True)

        # GLOBAL EVENT (always visible now)
        embed.add_field(name="🌐 Global Kitten Event", value=global_event_text, inline=False)

        await interaction.response.send_message(embed=embed)

    # =================================================
    # ERROR HANDLER
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

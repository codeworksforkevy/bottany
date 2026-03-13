from __future__ import annotations

import random
import logging
import discord
from discord import app_commands

logger = logging.getLogger("bottany")


ADOPTION_JOKES = [

"📦 The kitten found a cardboard box. Somehow better than your expensive toy choices.",

"🐈 Your kitten stepped on your keyboard during a raffle.\nInstead of typing !join, you wrote !joxcnvbyyyyyy.\nJordan won the raffle. :D",

"🎮 Your kitten is sitting between you and the monitor.\nGetting a kill in Counter-Strike is now impossible.",

"📦 The kitten prefers boxes over expensive furniture.",

"🐱 Your kitten prefers sitting on books.\nReading is now physically impossible.",

"🌌 The kitten stares at the void.\nThe void stares back.",

"🏥 Vet visit scheduled.\nThe kitten sensed the carrier box.",

"😼 The kitten entered the carrier.\nAgainst its will.",

"🐱 The kitten forgave you after the stress of the vet visit.\nEventually.",

"🏠 Daily Exploration Report\n\nThe kitten explored the house four times today.",

"🌠 You thought the kitten was distracted.\nIt was actually contemplating the astrophysical laws of the universe."

]


LEGENDARY_LORE = [

"🌌 Legendary Kitten Lore\n\nThis kitten once stared at a black hole.\nThe black hole blinked first.",

"📜 Legendary Kitten Lore\n\nAncient scholars wrote about a cosmic kitten.\nThey were not joking.",

"🪐 Legendary Kitten Lore\n\nYour kitten briefly understood the structure of the universe.\nIt immediately forgot and chased a dust particle.",

"⚡ Legendary Kitten Lore\n\nWhen the universe was young, a kitten stepped on the keyboard of reality.\nThat is why chaos exists.",

"🌠 Legendary Kitten Lore\n\nSome say every galaxy contains a kitten.\nScientists are still investigating."

]


def register(bot):

    @bot.tree.command(name="kittenadoption", description="Adopt a kitten.")
    @app_commands.describe(name="Name of your kitten")

    async def kittenadoption(interaction: discord.Interaction, name: str):

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

                exists = await conn.fetchval("""

                    SELECT 1
                    FROM kitten_adoptions
                    WHERE guild_id=$1 AND user_id=$2

                """, guild_id, user_id)

                if exists:

                    await interaction.response.send_message(
                        "🐱 You already adopted a kitten.",
                        ephemeral=True
                    )
                    return

                await conn.execute("""

                    INSERT INTO kitten_adoptions
                    (guild_id,user_id,kitten_name)
                    VALUES ($1,$2,$3)

                """, guild_id, user_id, name)

        except Exception:

            logger.exception("Kitten adoption DB error")

            await interaction.response.send_message(
                "Database error occurred.",
                ephemeral=True
            )
            return

        # Legendary chance
        if random.randint(1,100) <= 5:

            text = random.choice(LEGENDARY_LORE)

        else:

            text = random.choice(ADOPTION_JOKES)

        embed = discord.Embed(

            title="🐾 Kitten Adoption Complete",
            description=text,
            color=0xF1C40F

        )

        embed.add_field(
            name="Kitten Name",
            value=name,
            inline=False
        )

        embed.set_footer(
            text=f"{interaction.user.display_name} adopted a kitten"
        )

        await interaction.response.send_message(embed=embed)

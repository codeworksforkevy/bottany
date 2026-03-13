from __future__ import annotations

import random
import logging
import discord
from discord import app_commands

logger = logging.getLogger("bottany")

# =================================================
# ADOPTION JOKES
# =================================================

ADOPTION_JOKES = [

"📦 The kitten found a cardboard box. Somehow better than your expensive toy choices.",

"🐈 Your kitten stepped on your keyboard during a raffle.\nInstead of typing !join, you wrote !joxcnvbyyyyyy\nJordan won the raffle. :D",

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

# =================================================
# GLOBAL EVENTS
# =================================================

GLOBAL_EVENTS = [

"🌙 At exactly midnight, every kitten runs across the house simultaneously.\nHopefully your neighbors don't get angry.",

"🎧 It has been reported that all kittens today chewed through headphone cables.",

"🥫 The demand for wet food continues in every household.",

"🛋 Cozy cat-human time has brought happiness today."
]

# =================================================
# LEGENDARY LORE
# =================================================

LEGENDARY_LORE = [

"🌌 Legendary Kitten Lore\n\nThis kitten once stared at a black hole.\nThe black hole blinked first.",

"📜 Legendary Kitten Lore\n\nAncient scholars wrote about a cosmic kitten.\nThey were not joking.",

"🪐 Legendary Kitten Lore\n\nYour kitten briefly understood the structure of the universe.\nIt immediately forgot and chased a dust particle.",

"⚡ Legendary Kitten Lore\n\nWhen the universe was young, a kitten stepped on the keyboard of reality.\nThat is why chaos exists.",

"🌠 Legendary Kitten Lore\n\nSome say every galaxy contains a kitten.\nScientists are still investigating."

]

# =================================================
# CONFIRM VIEW
# =================================================

class KittenAdoptView(discord.ui.View):

    def __init__(self, bot, guild_id, user_id, kitten_name):

        super().__init__(timeout=60)

        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id
        self.kitten_name = kitten_name


    # ==============================================
    # ADOPT BUTTON
    # ==============================================

    @discord.ui.button(label="Adopt", style=discord.ButtonStyle.green)
    async def adopt(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user.id != self.user_id:

            await interaction.response.send_message(
                "This adoption request belongs to another user.",
                ephemeral=True
            )
            return

        try:

            async with self.bot.db.acquire() as conn:

                exists = await conn.fetchval("""

                    SELECT 1 FROM kitten_adoptions
                    WHERE guild_id=$1 AND user_id=$2

                """, self.guild_id, self.user_id)

                if exists:

                    await interaction.response.send_message(
                        "🐱 You already adopted a kitten.",
                        ephemeral=True
                    )
                    return

                await conn.execute("""

                    INSERT INTO kitten_adoptions (guild_id,user_id,kitten_name)
                    VALUES ($1,$2,$3)

                """, self.guild_id, self.user_id, self.kitten_name)

        except Exception:

            logger.exception("Kitten adoption DB error")

            await interaction.response.send_message(
                "Database error occurred.",
                ephemeral=True
            )
            return


        # ==========================================
        # JOKE OR LEGENDARY
        # ==========================================

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
            value=self.kitten_name,
            inline=False
        )

        embed.set_footer(
            text=f"{interaction.user.display_name} adopted a kitten"
        )

        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=None
        )

        # ==========================================
        # GLOBAL EVENT CHANCE
        # ==========================================

        if random.randint(1,100) <= 8:

            event = random.choice(GLOBAL_EVENTS)

            await interaction.channel.send(
                f"🌍 **Global Kitten Event**\n\n{event}"
            )


    # ==============================================
    # CANCEL BUTTON
    # ==============================================

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user.id != self.user_id:
            return

        await interaction.response.edit_message(
            content="Kitten adoption cancelled.",
            embed=None,
            view=None
        )

# =================================================
# REGISTER COMMAND
# =================================================

def register(bot):

    @bot.tree.command(name="kittenadoption", description="Adopt a kitten.")
    @app_commands.describe(name="Choose a name for your kitten")

    async def kittenadoption(interaction: discord.Interaction, name: str):

        if interaction.guild is None:

            await interaction.response.send_message(
                "Server only command.",
                ephemeral=True
            )
            return


        embed = discord.Embed(

            title="🐾 Kitten Adoption Request",

            description=(
                f"You are about to adopt a kitten.\n\n"
                f"Name: **{name}**\n\n"
                f"Your life will become warmer now.\n\n"
                f"Are you sure you want to proceed?"
            ),

            color=0x2ECC71

        )

        view = KittenAdoptView(
            bot,
            interaction.guild.id,
            interaction.user.id,
            name
        )

        await interaction.response.send_message(
            embed=embed,
            view=view
        )

import discord
from discord import app_commands

async def register(bot, app_state, session):
    @bot.tree.command(name="versus", description="Check the global stats: Kittens vs Puppies")
    async def versus(interaction: discord.Interaction):
        # Bu veriler DB'deki toplam pet ve save sayılarından çekilmeli
        kitten_total = 2540 
        puppy_total = 2110
        
        embed = discord.Embed(
            title="Global Interaction Stats",
            color=0x000033 # Dark Navy
        )
        
        embed.add_field(name="🐱 Kittens", value=f"Total Pets: **{kitten_total}**", inline=True)
        embed.add_field(name="🐶 Puppies", value=f"Total Rescues: **{puppy_total}**", inline=True)
        
        leader = "Kittens" if kitten_total > puppy_total else "Puppies"
        embed.set_footer(text=f"Current Lead: {leader}")
        
        await interaction.response.send_message(embed=embed)

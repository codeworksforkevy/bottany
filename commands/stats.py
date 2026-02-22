import discord
from discord import app_commands
from services.stats_service import get_stats, log_command

def register(bot):

    @bot.tree.command(name="stats", description="Bot usage statistics")
    async def stats(interaction: discord.Interaction):
        stats = get_stats()
        log_command("stats", interaction.user.id)

        total = stats["total_calls"]
        most_used = max(stats["commands"], key=stats["commands"].get) if stats["commands"] else "None"
        users = len(stats["unique_users"])

        msg = f"""
Total Commands: {total}
Most Used: {most_used}
Unique Users: {users}
"""
        await interaction.response.send_message(msg)
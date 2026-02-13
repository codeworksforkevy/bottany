
import os
import json
import discord
from discord import app_commands

STATE_FILE = "follower_milestones.json"


def next_target(current: int) -> int:
    if current < 1000:
        return current + 50
    elif current < 2000:
        return current + 100
    else:
        return current + 500


def load_state(data_dir: str):
    path = os.path.join(data_dir, STATE_FILE)
    if not os.path.exists(path):
        return {"last_milestone": 0, "history": []}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(data_dir: str, state: dict):
    path = os.path.join(data_dir, STATE_FILE)
    os.makedirs(data_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


async def register(bot, data_dir):

    @bot.tree.command(name="followers", description="Post a Twitch follower milestone.")
    @app_commands.describe(milestone="Follower count reached")
    async def followers(interaction: discord.Interaction, milestone: int):

        # Admin only check
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "Admins only.",
                ephemeral=True
            )
            return

        state = load_state(data_dir)

        # Update state
        state["last_milestone"] = milestone
        history = state.get("history", [])
        history.append(milestone)
        state["history"] = history[-20:]  # keep last 20 milestones
        save_state(data_dir, state)

        next_goal = next_target(milestone)

        embed = discord.Embed(
            title="🎉 FOLLOWER MILESTONE REACHED!",
            color=0x9146FF
        )

        embed.description = (
            f"We just hit {milestone} followers on Twitch!\n\n"
            f"Thank you for supporting Kevy 💜\n"
            f"I Love Kevy.. 😳🙄\n\n"
            f"Next goal: {next_goal} followers 🚀"
        )

        await interaction.response.send_message(embed=embed)


    @bot.tree.command(name="followers_history", description="Show follower milestone history.")
    async def followers_history(interaction: discord.Interaction):

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "Admins only.",
                ephemeral=True
            )
            return

        state = load_state(data_dir)
        history = state.get("history", [])

        if not history:
            await interaction.response.send_message("No milestones recorded yet.", ephemeral=True)
            return

        embed = discord.Embed(
            title="📊 Follower Milestone History",
            color=0x9146FF
        )

        embed.description = "\n".join(
            [f"• {m} followers" for m in reversed(history)]
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

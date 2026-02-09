import discord
from discord import app_commands


def register_kevy(bot):
    """
    /kevy command
    - embed + emoji
    - optional @user mention
    - optional ephemeral response
    Safe to call multiple times.
    """

    if getattr(bot, "_kevy_registered", False):
        return

    @bot.tree.command(name="kevy", description="Send love to Kevy 💙")
    @app_commands.describe(
        user="Mention someone (optional)",
        ephemeral="Only you can see the message"
    )
    async def kevy(
        interaction: discord.Interaction,
        user: discord.User | None = None,
        ephemeral: bool = False,
    ):
        heart = "💙"
        text = "We love you Kevy"

        if user:
            text = f"{user.mention} — {text}"

        embed = discord.Embed(
            description=f"{heart} **{text}** {heart}",
            color=0x5865F2  # Discord blurple
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=ephemeral
        )

    bot._kevy_registered = True

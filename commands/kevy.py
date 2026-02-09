import discord
from discord import app_commands

# Simple in-memory counter (process lifetime)
# Restart sonrası sıfırlanır (bilinçli tercih)
_KEVY_COUNT = 0


def register_kevy(bot):
    """
    /kevy command set
    - embed + confetti emoji 🎉
    - optional @user mention
    - optional ephemeral
    - /kevy count
    Safe to call multiple times.
    """

    global _KEVY_COUNT

    if getattr(bot, "_kevy_registered", False):
        return

    kevy_group = app_commands.Group(
        name="kevy",
        description="Spread love to Kevy 🎉"
    )

    # -------------------------
    # /kevy  (default action)
    # -------------------------
    @kevy_group.command(name="love", description="Send love to Kevy 💙")
    @app_commands.describe(
        user="Mention someone (optional)",
        ephemeral="Only you can see the message"
    )
    async def kevy_love(
        interaction: discord.Interaction,
        user: discord.User | None = None,
        ephemeral: bool = False,
    ):
        global _KEVY_COUNT
        _KEVY_COUNT += 1

        confetti = "🎉"
        heart = "💙"
        text = "We love you Kevy"

        if user:
            text = f"{user.mention} — {text}"

        embed = discord.Embed(
            description=f"{confetti} {heart} **{text}** {heart} {confetti}",
            color=0x5865F2  # Discord blurple
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=ephemeral
        )

    # -------------------------
    # /kevy count
    # -------------------------
    @kevy_group.command(name="count", description="Show how many times /kevy was used.")
    async def kevy_count(interaction: discord.Interaction):
        embed = discord.Embed(
            title="Kevy Love Counter 🎉",
            description=f"**/kevy** has been used **{_KEVY_COUNT}** times 💙",
            color=0x57F287  # green
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    bot.tree.add_command(kevy_group)
    bot._kevy_registered = True

# -----------------------------------------------------
# HELP
# -----------------------------------------------------
@app_commands.command(
    name="help",
    description="Show help for utility commands"
)
async def help_utility(self, interaction: discord.Interaction):

    embed = discord.Embed(
        title="📦 Utility Commands",
        description=(
            "### 🕒 Time Conversion\n"
            "**/utility schedule <text>**\n"
            "Convert any HH:MM time inside your text into a Discord timestamp.\n"
            "Example: `Stream at 12:00 and 18:30`\n"
            "Everyone will automatically see the correct local time.\n\n"

            "### 🧑‍💻 Timezone Settings\n"
            "**/utility timezone <IANA name>**\n"
            "Set the default timezone for this server.\n"
            "Example: `Europe/Brussels`\n\n"

            "**/utility mytimezone <IANA name>**\n"
            "Set your personal timezone for time conversion.\n\n"

            "### 📝 Reminders\n"
            "**/utility remind <minutes> <text> [repeat]**\n"
            "Set a reminder after a number of minutes.\n"
            "Optional repeat: `daily` or `weekly`.\n"
            "Example: `/utility remind 30 Study notes daily`\n\n"

            "**/utility reminders**\n"
            "See all your active reminders and their numbers.\n\n"

            "**/utility cancel <number>**\n"
            "Cancel a reminder using its number.\n\n"

            "### 📊 Server Tools\n"
            "**/utility poll**\n"
            "Create a quick poll with 2 to 5 options.\n\n"

            "**/utility serverinfo**\n"
            "Show essential information about this server.\n\n"

            "**/utility ping**\n"
            "Check the bot's connection latency."
        ),
        color=0x5865F2
    )

    embed.set_footer(
        text="Times automatically adjust to each user's local timezone."
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

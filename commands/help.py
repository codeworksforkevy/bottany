import discord
from discord import app_commands

# -------------------------
# Help pages configuration
# -------------------------
HELP_PAGES = [
    {
        "title": "📘 General",
        "description": (
            "**/help** – Show all commands\n"
            "**/time** – World clock\n"
            "**/kevy** – Spread love to Kevy 💙"
        ),
    },
    {
        "title": "🎓 Trivia & Knowledge",
        "description": (
            "**/trivia now** – Academic trivia\n"
            "**/davinci** – Leonardo da Vinci registry"
        ),
    },
    {
        "title": "🎮 Gaming",
        "description": (
            "**/freegames** – Free games & deals\n"
            "**/badges** – Twitch badge tracking\n"
            "**/drops** – Twitch Drops registry"
        ),
    },
]

# -------------------------
# Pagination View
# -------------------------
class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.page = 0

    def make_embed(self):
        data = HELP_PAGES[self.page]
        embed = discord.Embed(
            title=data["title"],
            description=data["description"]
        )
        embed.set_footer(text=f"Page {self.page + 1}/{len(HELP_PAGES)}")
        return embed

    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = (self.page - 1) % len(HELP_PAGES)
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = (self.page + 1) % len(HELP_PAGES)
        await interaction.response.edit_message(embed=self.make_embed(), view=self)


# -------------------------
# Help command
# -------------------------
help_group = app_commands.Group(
    name="help",
    description="Show Bottany command documentation"
)

@help_group.command(name="all", description="Show all available commands (paginated).")
async def help_all(interaction: discord.Interaction):
    view = HelpView()
    await interaction.response.send_message(
        embed=view.make_embed(),
        view=view
    )


def register_help(bot, DATA_DIR=None):
    bot.tree.add_command(help_group)

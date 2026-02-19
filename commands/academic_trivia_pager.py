import discord
from discord import app_commands
import random
from pathlib import Path

from services.academic_trivia_loader import get_random_batch


class TriviaPager(discord.ui.View):
    def __init__(self, items, index=0):
        super().__init__(timeout=180)
        self.items = items
        self.index = index

    def make_embed(self):
        item = self.items[self.index]

        embed = discord.Embed(
            title="Academic Trivia",
            description=item["text"],
            color=0x5865F2
        )

        footer_parts = []

        if item.get("author"):
            footer_parts.append(item["author"])

        if item.get("field"):
            footer_parts.append(item["field"])

        if footer_parts:
            embed.set_footer(text=" | ".join(footer_parts))

        embed.add_field(
            name="Item",
            value=f"{self.index + 1}/{len(self.items)}",
            inline=False
        )

        return embed

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index - 1) % len(self.items)
        await interaction.response.edit_message(
            embed=self.make_embed(),
            view=self
        )

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index + 1) % len(self.items)
        await interaction.response.edit_message(
            embed=self.make_embed(),
            view=self
        )


async def register(bot, data_dir):

    guild = discord.Object(id=1446560723122520207)

    academic_group = app_commands.Group(
        name="academic",
        description="Academic tools"
    )

    @academic_group.command(
        name="trivia",
        description="Browse academic trivia"
    )
    async def academic_trivia(interaction: discord.Interaction):

        BASE_DIR = Path(__file__).resolve().parent.parent

        items = get_random_batch(BASE_DIR, size=25)

        if not items:
            await interaction.response.send_message(
                "Academic trivia dataset not loaded.",
                ephemeral=True
            )
            return

        view = TriviaPager(items)

        await interaction.response.send_message(
            embed=view.make_embed(),
            view=view
        )

    bot.tree.add_command(academic_group, guild=guild)




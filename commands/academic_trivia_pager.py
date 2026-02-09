
import discord
from discord import app_commands
import json
import random
from pathlib import Path

DATA_PATH = Path("data/academic_trivia_pool.json")

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
        if "source" in item:
            embed.set_footer(text=item["source"])
        embed.add_field(name="Item", value=f"{self.index + 1}/{len(self.items)}", inline=False)
        return embed

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index - 1) % len(self.items)
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index + 1) % len(self.items)
        await interaction.response.edit_message(embed=self.make_embed(), view=self)


def load_trivia():
    if not DATA_PATH.exists():
        return []
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def register_trivia(tree: app_commands.CommandTree):

    @tree.command(name="trivia", description="Academic trivia")
    @app_commands.describe(mode="Use 'now' for instant trivia")
    async def trivia(interaction: discord.Interaction, mode: str = "now"):
        items = load_trivia()
        if not items:
            await interaction.response.send_message("Trivia pool is empty.", ephemeral=True)
            return

        random.shuffle(items)
        view = TriviaPager(items[:25])
        await interaction.response.send_message(embed=view.make_embed(), view=view)

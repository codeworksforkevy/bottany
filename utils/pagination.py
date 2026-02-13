
import discord
from utils.embed_utils import apply_source_footer

class PaginationView(discord.ui.View):

    def __init__(self, embeds):
        super().__init__(timeout=180)
        self.embeds = [apply_source_footer(e) for e in embeds]
        self.index = 0

    async def update(self, interaction):
        self.reset_timeout()
        await interaction.response.edit_message(
            embed=self.embeds[self.index],
            view=self
        )

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index > 0:
            self.index -= 1
            await self.update(interaction)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index < len(self.embeds) - 1:
            self.index += 1
            await self.update(interaction)

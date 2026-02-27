from __future__ import annotations

import discord
from typing import List, Dict


class TriviaPager(discord.ui.View):

    def __init__(self, items: List[Dict], index: int = 0):
        super().__init__(timeout=180)
        self.items = items
        self.index = index

    def make_embed(self) -> discord.Embed:
        item = self.items[self.index]

        embed = discord.Embed(
            title="Academic Trivia",
            description=item.get("text", "No text provided."),
            color=0x5865F2
        )

        footer_parts = []

        if item.get("author"):
            footer_parts.append(item["author"])

        if item.get("field"):
            footer_parts.append(item["field"].upper())

        if footer_parts:
            embed.set_footer(text=" | ".join(footer_parts))

        embed.add_field(
            name="Item",
            value=f"{self.index + 1}/{len(self.items)}",
            inline=False
        )

        return embed

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

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

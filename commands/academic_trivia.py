from __future__ import annotations

import discord
from discord import app_commands
from typing import Optional, List, Dict

from services.academic_trivia_loader import AcademicTriviaService


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


async def register(bot, data_dir):

    guild = discord.Object(id=1446560723122520207)

    trivia_group = app_commands.Group(
        name="academictrivia",
        description="Academic Daily Trivia"
    )

    @trivia_group.command(name="random")
    @app_commands.describe(
        category="Optional category (e.g. cicero, neuroscience)"
    )
    async def random_trivia(
        interaction: discord.Interaction,
        category: Optional[str] = None
    ):

        items = AcademicTriviaService.get_batch(
            user_id=interaction.user.id,
            size=25,
            category=category
        )

        if not items:
            await interaction.response.send_message(
                "No trivia found.",
                ephemeral=True
            )
            return

        view = TriviaPager(items)

        await interaction.response.send_message(
            embed=view.make_embed(),
            view=view
        )

    bot.tree.add_command(trivia_group, guild=guild)

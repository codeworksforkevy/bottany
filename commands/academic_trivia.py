from __future__ import annotations

import discord
from discord import app_commands
from typing import Optional
from pathlib import Path

from services.academic_trivia_loader import AcademicTriviaService
from commands.academic_trivia_pager import TriviaPager


async def category_autocomplete(interaction: discord.Interaction, current: str):

    categories = AcademicTriviaService.get_categories()

    return [
        app_commands.Choice(name=cat, value=cat)
        for cat in categories
        if current.lower() in cat.lower()
    ][:25]


async def register(bot, data_dir):

    guild = discord.Object(id=1446560723122520207)

    trivia_group = app_commands.Group(
        name="academictrivia",
        description="Academic Daily Trivia Engine"
    )

    @trivia_group.command(name="random")
    @app_commands.autocomplete(category=category_autocomplete)
    async def random_trivia(
        interaction: discord.Interaction,
        category: Optional[str] = None
    ):

        if not AcademicTriviaService.is_ready():
            await interaction.response.send_message(
                "Trivia engine not initialized.",
                ephemeral=True
            )
            return

        items = AcademicTriviaService.get_batch(
            user_id=interaction.user.id,
            size=25,
            category=category
        )

        if not items:
            await interaction.response.send_message(
                "No trivia found for this category.",
                ephemeral=True
            )
            return

        view = TriviaPager(
            items=items,
            user_id=interaction.user.id
        )

        await interaction.response.send_message(
            embed=view.make_embed(),
            view=view
        )

        view.message = await interaction.original_response()

    bot.tree.add_command(trivia_group, guild=guild)

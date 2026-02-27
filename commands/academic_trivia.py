from __future__ import annotations

import discord
from discord import app_commands
from typing import Optional, List, Dict
from pathlib import Path

from services.academic_trivia_loader import AcademicTriviaService


# =====================================================
# PAGINATION VIEW
# =====================================================

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


# =====================================================
# AUTOCOMPLETE
# =====================================================

async def category_autocomplete(
    interaction: discord.Interaction,
    current: str
):

    categories = AcademicTriviaService.get_categories()

    return [
        app_commands.Choice(name=cat, value=cat)
        for cat in categories
        if current.lower() in cat.lower()
    ][:25]


# =====================================================
# COMMAND REGISTRATION
# =====================================================

async def register(bot, data_dir):

    guild = discord.Object(id=1446560723122520207)

    trivia_group = app_commands.Group(
        name="academictrivia",
        description="Academic Daily Trivia Engine"
    )

    # -------------------------------------------------
    # RANDOM
    # -------------------------------------------------

    @trivia_group.command(name="random")
    @app_commands.describe(
        category="Optional category (e.g. cicero, neuroscience)"
    )
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

        view = TriviaPager(items)

        await interaction.response.send_message(
            embed=view.make_embed(),
            view=view
        )

    # -------------------------------------------------
    # STATS
    # -------------------------------------------------

    @trivia_group.command(name="stats")
    async def trivia_stats(interaction: discord.Interaction):

        stats = AcademicTriviaService.get_stats()

        embed = discord.Embed(
            title="Academic Trivia Statistics",
            color=0x3498DB
        )

        embed.add_field(
            name="Total Quotes",
            value=str(stats["total"]),
            inline=False
        )

        for cat, count in sorted(
            stats["categories"].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            embed.add_field(
                name=cat.capitalize(),
                value=str(count),
                inline=True
            )

        await interaction.response.send_message(embed=embed)

    # -------------------------------------------------
    # CACHE INFO
    # -------------------------------------------------

    @trivia_group.command(name="cache")
    async def cache_info(interaction: discord.Interaction):

        info = AcademicTriviaService.get_cache_info()

        embed = discord.Embed(
            title="Trivia Cache Info",
            color=0x9B59B6
        )

        embed.add_field(
            name="Initialized",
            value=str(info["initialized"]),
            inline=True
        )

        embed.add_field(
            name="Total Items",
            value=str(info["total_items"]),
            inline=True
        )

        embed.add_field(
            name="Categories",
            value=str(info["categories"]),
            inline=True
        )

        embed.add_field(
            name="Users Tracked",
            value=str(info["users_tracked"]),
            inline=True
        )

        embed.add_field(
            name="Last Loaded (UTC)",
            value=str(info["last_loaded"]),
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    # -------------------------------------------------
    # HEALTH CHECK
    # -------------------------------------------------

    @trivia_group.command(name="health")
    async def health_check(interaction: discord.Interaction):

        ready = AcademicTriviaService.is_ready()

        embed = discord.Embed(
            title="Academic Trivia Health Check",
            color=0x2ECC71 if ready else 0xE74C3C
        )

        embed.add_field(
            name="Engine Ready",
            value=str(ready),
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    # -------------------------------------------------
    # RELOAD (ADMIN ONLY)
    # -------------------------------------------------

    @trivia_group.command(name="reload")
    async def reload_trivia(interaction: discord.Interaction):

        if interaction.user.id != bot.owner_id:
            await interaction.response.send_message(
                "You are not authorized to reload trivia.",
                ephemeral=True
            )
            return

        BASE_DIR = Path(__file__).resolve().parent.parent

        AcademicTriviaService.initialize(BASE_DIR, force=True)

        info = AcademicTriviaService.get_cache_info()

        embed = discord.Embed(
            title="Trivia Cache Reloaded",
            color=0x2ECC71
        )

        embed.add_field(
            name="Total Items",
            value=str(info["total_items"]),
            inline=True
        )

        embed.add_field(
            name="Categories",
            value=str(info["categories"]),
            inline=True
        )

        embed.add_field(
            name="Last Loaded (UTC)",
            value=str(info["last_loaded"]),
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    # -------------------------------------------------

    bot.tree.add_command(trivia_group, guild=guild)

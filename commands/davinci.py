import os
import random
import discord
from discord import app_commands

from utils.json_utils import load_json


BASE_GUILD_ID = 1446560723122520207


# =================================================
# REGISTRY HELPERS
# =================================================

def _get_registry(data_dir):
    path = os.path.join(data_dir, "davinci_registry.json")
    return load_json(path) if os.path.exists(path) else {}


def _davinci_items(registry, category: str = ""):
    items = (registry.get("items", []) or [])
    cat = (category or "").strip().lower()

    if cat and cat != "all":
        items = [
            it for it in items
            if it.get("category", "").lower() == cat
        ]

    return items


# =================================================
# PAGINATION VIEW
# =================================================

class DavinciPager(discord.ui.View):

    def __init__(self, registry, items, category, page_size):
        super().__init__(timeout=180)
        self.registry = registry
        self.items = items
        self.category = category
        self.page_size = page_size
        self.page = 1

    def make_embed(self):

        total_pages = max(
            1,
            (len(self.items) + self.page_size - 1) // self.page_size
        )

        start = (self.page - 1) * self.page_size
        end = start + self.page_size
        chunk = self.items[start:end]

        embed = discord.Embed(
            title=f"Da Vinci — {self.category.upper()} (Page {self.page}/{total_pages})",
            color=0x8E5A3C
        )

        lines = []

        for it in chunk:
            name = it.get("title", "Untitled")
            note = it.get("note", "")
            url = it.get("url", "")

            line = f"• **{name}**"
            if note:
                line += f" — {note}"
            if url:
                line += f"\n  {url}"

            lines.append(line)

        embed.description = "\n".join(lines[:15])[:4000]

        return embed

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):

        self.page = max(1, self.page - 1)
        await interaction.response.edit_message(
            embed=self.make_embed(),
            view=self
        )

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):

        total_pages = max(
            1,
            (len(self.items) + self.page_size - 1) // self.page_size
        )

        self.page = min(total_pages, self.page + 1)

        await interaction.response.edit_message(
            embed=self.make_embed(),
            view=self
        )


# =================================================
# REGISTER (HYBRID LOADER COMPATIBLE)
# =================================================

async def register(bot, data_dir):

    guild = discord.Object(id=BASE_GUILD_ID)

    if getattr(bot, "_davinci_registered", False):
        return

    registry = _get_registry(data_dir)

    davinci_group = app_commands.Group(
        name="davinci",
        description="Leonardo da Vinci — registry-based resources (official sources)."
    )

    # -------------------------------------------------
    # LIST
    # -------------------------------------------------

    @davinci_group.command(
        name="list",
        description="List Da Vinci items with pagination."
    )
    @app_commands.describe(category="all|machine|drawing|manuscript|painting")
    async def davinci_list(
        interaction: discord.Interaction,
        category: str = "all"
    ):

        items = _davinci_items(registry, category)

        if not items:
            await interaction.response.send_message(
                "No Da Vinci items found for that category.",
                ephemeral=True
            )
            return

        page_size = int(
            (registry.get("pagination", {}) or {}).get("page_size", 8)
        )

        view = DavinciPager(registry, items, category, page_size)

        await interaction.response.send_message(
            embed=view.make_embed(),
            view=view
        )

    # -------------------------------------------------
    # RANDOM
    # -------------------------------------------------

    @davinci_group.command(
        name="random",
        description="Show one Da Vinci item."
    )
    @app_commands.describe(category="all|machine|drawing|manuscript|painting")
    async def davinci_random(
        interaction: discord.Interaction,
        category: str = "all"
    ):

        items = _davinci_items(registry, category)

        if not items:
            await interaction.response.send_message(
                "No Da Vinci items found for that category.",
                ephemeral=True
            )
            return

        it = random.choice(items)

        embed = discord.Embed(
            title=f"Da Vinci — {it.get('title', 'Untitled')}",
            color=0x8E5A3C
        )

        if it.get("note"):
            embed.description = it.get("note")

        if it.get("url"):
            embed.add_field(
                name="Official / Institutional link",
                value=it["url"],
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    # -------------------------------------------------
    # SOURCES
    # -------------------------------------------------

    @davinci_group.command(
        name="sources",
        description="Show official/institutional sources."
    )
    async def davinci_sources(interaction: discord.Interaction):

        sources = (registry.get("sources", []) or [])

        if not sources:
            await interaction.response.send_message(
                "No sources configured.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="Da Vinci — Official / Institutional Sources",
            color=0x8E5A3C
        )

        for s in sources[:10]:
            embed.add_field(
                name=s.get("name", "Source"),
                value=s.get("url", ""),
                inline=False
            )

        if len(sources) > 10:
            embed.set_footer(
                text=f"+{len(sources) - 10} more in registry"
            )

        await interaction.response.send_message(embed=embed)

    # -------------------------------------------------
    # REGISTER TO GUILD
    # -------------------------------------------------

    bot.tree.add_command(davinci_group, guild=guild)
    bot._davinci_registered = True

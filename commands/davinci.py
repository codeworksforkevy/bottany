import os
import random
import discord
from discord import app_commands

from utils.json_utils import load_json  # sende farklıysa düzelt

# -------------------------
# Da Vinci module (registry + pagination)
# Official / institutional public sources only
# -------------------------

def _get_registry(DATA_DIR):
    path = os.path.join(DATA_DIR, "davinci_registry.json")
    return load_json(path) if os.path.exists(path) else {}

def _davinci_items(registry, category: str = ""):
    items = (registry.get("items", []) or [])
    cat = (category or "").strip().lower()
    if cat and cat != "all":
        items = [it for it in items if it.get("category", "").lower() == cat]
    return items


class DavinciPager(discord.ui.View):
    def __init__(self, registry, items, category, page_size):
        super().__init__(timeout=180)
        self.registry = registry
        self.items = items
        self.category = category
        self.page_size = page_size
        self.page = 1

    def make_embed(self):
        total_pages = (len(self.items) + self.page_size - 1) // self.page_size
        start = (self.page - 1) * self.page_size
        end = start + self.page_size
        chunk = self.items[start:end]

        embed = discord.Embed(
            title=f"Da Vinci — {self.category.upper()} (Page {self.page}/{total_pages})"
        )

        lines = []
        for it in chunk:
            name = it.get("title", "Untitled")
            note = it.get("note", "")
            url = it.get("url", "")
            if url:
                lines.append(f"• **{name}** — {note}\n  {url}")
            else:
                lines.append(f"• **{name}** — {note}")

        embed.description = "\n".join(lines[:15])
        return embed

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = max(1, self.page - 1)
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        total_pages = (len(self.items) + self.page_size - 1) // self.page_size
        self.page = min(total_pages, self.page + 1)
        await interaction.response.edit_message(embed=self.make_embed(), view=self)


def register_davinci(bot, DATA_DIR):
    """
    Safe, idempotent registration.
    Called from on_ready().
    """

    if getattr(bot, "_davinci_registered", False):
        return

    registry = _get_registry(DATA_DIR)

    davinci_group = app_commands.Group(
        name="davinci",
        description="Leonardo da Vinci — registry-based resources (official sources)."
    )

    # -------- list --------
    @davinci_group.command(name="list", description="List Da Vinci items with pagination.")
    @app_commands.describe(category="all|machine|drawing|manuscript|painting")
    async def davinci_list(interaction: discord.Interaction, category: str = "all"):
        items = _davinci_items(registry, category)
        if not items:
            await interaction.response.send_message(
                "No Da Vinci items found for that category.",
                ephemeral=True
            )
            return

        page_size = int((registry.get("pagination", {}) or {}).get("page_size", 8))
        view = DavinciPager(registry, items, category, page_size)
        await interaction.response.send_message(
            embed=view.make_embed(),
            view=view
        )

    # -------- random --------
    @davinci_group.command(name="random", description="Show one Da Vinci item.")
    @app_commands.describe(category="all|machine|drawing|manuscript|painting")
    async def davinci_random(interaction: discord.Interaction, category: str = "all"):
        items = _davinci_items(registry, category)
        if not items:
            await interaction.response.send_message(
                "No Da Vinci items found for that category.",
                ephemeral=True
            )
            return

        it = random.choice(items)
        embed = discord.Embed(
            title=f"Da Vinci — {it.get('title', 'Untitled')}"
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

    # -------- sources --------
    @davinci_group.command(name="sources", description="Show official/institutional sources.")
    async def davinci_sources(interaction: discord.Interaction):
        sources = (registry.get("sources", []) or [])
        if not sources:
            await interaction.response.send_message(
                "No sources configured.",
                ephemeral=True
            )
            return

        embed = discord.Embed(title="Da Vinci — Official / Institutional Sources")
        for s in sources[:10]:
            embed.add_field(
                name=s.get("name", "Source"),
                value=s.get("url", ""),
                inline=False
            )

        if len(sources) > 10:
            embed.set_footer(text=f"+{len(sources) - 10} more in registry")

        await interaction.response.send_message(embed=embed)

    bot.tree.add_command(davinci_group)
    bot._davinci_registered = True

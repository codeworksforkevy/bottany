# belgian_chocolate.py
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
import random
from pathlib import Path
import json

data_dir = Path(__file__).parent / "data"  # dataset path

def _load_dataset(data_dir):
    try:
        with open(data_dir / "belgian_chocolate.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def _format_item(item):
    desc = f"Founded: {item.get('foundation_year', 'Unknown')}\n"
    certs = ", ".join(item.get("certifications", []))
    desc += f"Certifications: {certs or 'None'}\n"
    desc += f"Production: {item.get('production_model', 'Unknown')}"
    return desc

class Chocolate(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    group = app_commands.Group(
        name="belgian_chocolate",
        description="Belgian chocolate houses commands"
    )

    @group.command(
        name="chocolate_brands",
        description="Filter Belgian chocolate houses or get a random one"
    )
    @app_commands.describe(
        year_before="Show brands founded before this year",
        year_after="Show brands founded after this year",
        certification="Filter by certification keyword",
        production_model="bean_to_bar | couverture | hybrid",
        random_choice="Show only one random brand"
    )
    async def chocolate_brands(
        self,
        interaction: discord.Interaction,
        year_before: Optional[int] = None,
        year_after: Optional[int] = None,
        certification: Optional[str] = None,
        production_model: Optional[str] = None,
        random_choice: bool = False
    ):
        items = _load_dataset(data_dir)
        if not items:
            await interaction.response.send_message("Chocolate dataset not found.", ephemeral=True)
            return

        # Filters
        if year_before:
            items = [i for i in items if i.get("foundation_year") and i["foundation_year"] < year_before]
        if year_after:
            items = [i for i in items if i.get("foundation_year") and i["foundation_year"] > year_after]
        if certification:
            cert_lower = certification.lower()
            items = [i for i in items if any(cert_lower in c.lower() for c in i.get("certifications", []))]
        if production_model:
            items = [i for i in items if (i.get("production_model") or "").lower() == production_model.lower()]

        if not items:
            await interaction.response.send_message("No brands matched your filters.", ephemeral=True)
            return

        if random_choice:
            items = [random.choice(items)]

        # Embedleri gönder (ilk mesaj response, sonrası followup)
        first_item = items[0]
        embed = discord.Embed(
            title=first_item.get('name', 'Unknown'),
            description=_format_item(first_item),
            color=0x4B2E2E
        )
        image_url = first_item.get("logo_url") or first_item.get("image_url") or "https://via.placeholder.com/300x150.png?text=Chocolate"
        embed.set_thumbnail(url=image_url)
        await interaction.response.send_message(embed=embed)

        # Eğer 1'den fazla item varsa followup ile gönder
        for item in items[1:10]:
            embed = discord.Embed(
                title=item.get('name', 'Unknown'),
                description=_format_item(item),
                color=0x4B2E2E
            )
            image_url = item.get("logo_url") or item.get("image_url") or "https://via.placeholder.com/300x150.png?text=Chocolate"
            embed.set_thumbnail(url=image_url)
            await interaction.followup.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Chocolate(bot))

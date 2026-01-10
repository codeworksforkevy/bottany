import io
import discord
from discord import app_commands

from utils.help_loader import load_help_registry
from utils.help_exporter import generate_readme_markdown


def register_help(bot: discord.Client, data_dir: str) -> None:
    """Register /help command.

    /help
    /help <category>
    /help export  -> sends README.md generated from help_registry.json
    """

    @app_commands.command(
        name="help",
        description="Shows all available commands of Bottany or commands in a specific category. We love Kevy"
    )
    @app_commands.describe(category="Optional command category (e.g., gaming) or 'export' to generate README.md")
    async def help_cmd(interaction: discord.Interaction, category: str = None):
        # Export mode: README.md
        if category and category.strip().lower() == "export":
            md = generate_readme_markdown(data_dir)
            file = discord.File(fp=io.BytesIO(md.encode("utf-8")), filename="README.md")
            await interaction.response.send_message(
                content="Here is the generated README.md for Bottany commands.",
                file=file,
                ephemeral=True,
            )
            return

        registry = load_help_registry(data_dir)

        embed = discord.Embed(
            title="Bottany Help",
            description="Available command categories",
        )

        # Category view
        if category:
            key = category.strip().lower()
            cat = registry.get(key)
            if not cat:
                embed.description = f"No category named **{category}** found."
                embed.set_footer(text="Tip: use /help to list categories, or /help export to generate README.md")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            embed.title = f"Bottany Help — {key}"
            embed.description = (cat or {}).get("description", "")

            for cmd in (cat or {}).get("commands", []) or []:
                name = cmd.get("name", "")
                usage = cmd.get("usage", "")
                desc = cmd.get("description", "")
                if not name:
                    continue
                embed.add_field(
                    name=name,
                    value=(f"**Usage:** `{usage}`\n{desc}").strip(),
                    inline=False,
                )

            embed.set_footer(text="Tip: /help export generates a README.md from the registry")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Index view (list categories)
        for cat_name, cat in registry.items():
            d = (cat or {}).get("description", "")
            embed.add_field(name=cat_name, value=d or "-", inline=False)

        embed.set_footer(text="Use /help <category> or /help export")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    bot.tree.add_command(help_cmd)

from __future__ import annotations
import discord
from discord import app_commands

def register(bot, data_dir=None):
    if bot.tree.get_command("code-testing"):
        return

    code_group = app_commands.Group(name="code-testing", description="Developer utilities and execution")

    @code_group.command(name="run", description="Test a small snippet of code safely.")
    @app_commands.choices(language=[
        app_commands.Choice(name="Python", value="python"),
        app_commands.Choice(name="JavaScript", value="javascript")
    ])
    async def run(interaction: discord.Interaction, language: str, snippet: str):
        embed = discord.Embed(title=f"👩‍💻 Code Execution ({language.title()})", color=0x0047AB)
        embed.description = "### Sandbox Environment\n*Secure code execution output.*"
        embed.add_field(name="Output", value="```\nHello, World! (Mock Execution)\n```", inline=False)
        embed.set_footer(text="Execution by Bottany 🤖")
        await interaction.response.send_message(embed=embed)

    bot.tree.add_command(code_group)

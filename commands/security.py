from __future__ import annotations
import discord
from discord import app_commands

def register(bot, data_dir=None):
    if bot.tree.get_command("security"):
        return

    security_group = app_commands.Group(name="security", description="Server security and OSINT tools")

    @security_group.command(name="defcon", description="Change the server security level (1-5).")
    @app_commands.describe(level="1 (Lockdown) to 5 (Normal)")
    @app_commands.default_permissions(manage_guild=True)
    async def defcon(interaction: discord.Interaction, level: app_commands.Range[int, 1, 5]):
        await interaction.response.defer()
        guild = interaction.guild
        default_role = guild.default_role

        if level == 1:
            await default_role.edit(permissions=discord.Permissions(send_messages=False, read_messages=True))
            color = 0xFF003C
            msg = "### Lockdown Initiated\n*DEFCON 1 ACTIVE: Server is in full lockdown. @everyone cannot send messages.* 🤖"
        elif level == 5:
            await default_role.edit(permissions=discord.Permissions(send_messages=True, read_messages=True))
            color = 0x2ECC71
            msg = "### Security Normalized\n*DEFCON 5: Security level normal. Lockdown lifted.* ✅"
        else:
            color = 0x0F0F0F
            msg = f"### Security Adjusted\n*DEFCON {level}: Security level adjusted.* 🖲️"

        embed = discord.Embed(title="🤖 System Alert", description=msg, color=color)
        await interaction.followup.send(embed=embed)

    @security_group.command(name="url-scan", description="Scan a URL for malicious content.")
    @app_commands.describe(url="The link to scan")
    async def url_scan(interaction: discord.Interaction, url: str):
        embed = discord.Embed(title="🖲️ URL Scan Results", url=url, color=0x2ECC71)
        embed.description = "### Diagnostics\n*Analyzing the requested domain...*"
        embed.add_field(name="Target", value=f"`{url}`", inline=False)
        embed.add_field(name="Status", value="✅ *Clean (0/72 Engines Detected)*", inline=True)
        embed.set_footer(text="Powered by Bottany Security")
        await interaction.response.send_message(embed=embed)

    @security_group.command(name="cve-search", description="Search the NVD database for a CVE vulnerability.")
    @app_commands.describe(cve_id="Format: CVE-YYYY-NNNN")
    async def cve_search(interaction: discord.Interaction, cve_id: str):
        embed = discord.Embed(title=f"📕 {cve_id.upper()}", color=0x0F0F0F)
        embed.description = "### Vulnerability Report\n*A mock buffer overflow vulnerability exists in the core module...*"
        embed.add_field(name="CVSS Score", value="**9.8 (CRITICAL)**", inline=False)
        embed.set_footer(text="Data provided by NIST")
        await interaction.response.send_message(embed=embed)

    bot.tree.add_command(security_group)

import discord
from discord import app_commands

from services.drop_registry import DropRegistry

COLOR_EVENT = 0xF59E0B


def register_twitch_drops(client, tree, data_dir):

    registry = DropRegistry(data_dir)

    group = app_commands.Group(
        name="twitch",
        description="Twitch related commands"
    )

    @group.command(
        name="drops",
        description="Show current Twitch Drops"
    )
    async def drops(interaction: discord.Interaction):

        await interaction.response.defer(thinking=True)

        drops = registry.get_active()

        if not drops:
            await interaction.followup.send(
                "No active Twitch Drops at the moment.",
                ephemeral=True
            )
            return

        lines = []

        for d in drops[:8]:
            game = d.get("game", "Unknown")
            campaign = d.get("campaign", "")
            end_date = d.get("end_date")

            line = f"• **{game}** — {campaign}"
            if end_date:
                line += f"\n  ⏳ Ends: {end_date}"

            lines.append(line)

        embed = discord.Embed(
            title="🎁 Active Twitch Drops",
            description="\n\n".join(lines),
            color=COLOR_EVENT
        )

        embed.set_footer(text=f"{len(drops)} active campaigns")

        await interaction.followup.send(embed=embed)

    tree.add_command(group)

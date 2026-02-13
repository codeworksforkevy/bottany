
import os
import json
import discord

def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

async def register(bot, data_dir):

    registry_path = os.path.join(data_dir, "awards_registry.json")

    @bot.tree.command(name="awards_v2", description="Show curated game awards data.")
    async def awards_v2(interaction: discord.Interaction):

        await interaction.response.defer()

        try:
            reg = _load_json(registry_path)
            items = reg.get("awards", [])

            if not items:
                await interaction.followup.send("No awards data found.")
                return

            for item in items[:10]:
                embed = discord.Embed(
                    title=item.get("title"),
                    description=item.get("winner"),
                    url=item.get("url"),
                    color=0xFFD700
                )
                embed.add_field(name="Year", value=item.get("year"), inline=False)
                await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"Sync failed: {e}")
            raise

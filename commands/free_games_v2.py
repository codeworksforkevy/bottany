
import os
import json
import datetime as dt
import discord

def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _active_this_week(item):
    today = dt.datetime.utcnow().date()
    start = dt.datetime.strptime(item["start_date"], "%Y-%m-%d").date()
    end = dt.datetime.strptime(item["end_date"], "%Y-%m-%d").date()
    return start <= today <= end

async def register(bot, data_dir):

    registry_path = os.path.join(data_dir, "freegames_registry.json")

    @bot.tree.command(name="freegames_v2", description="Active free games this week (multi-platform).")
    async def freegames_v2(interaction: discord.Interaction):

        await interaction.response.defer()

        reg = _load_json(registry_path)
        items = reg.get("offers", [])

        active = [i for i in items if _active_this_week(i)]

        if not active:
            await interaction.followup.send("No active free games this week.")
            return

        for item in active:
            embed = discord.Embed(
                title=item["title"],
                url=item["url"],
                color=0x2F3136,
                timestamp=dt.datetime.utcnow()
            )
            embed.add_field(name="Platform", value=item["platform"], inline=False)
            embed.add_field(name="Type", value=item["type"], inline=False)
            embed.add_field(name="Ends", value=item["end_date"], inline=False)

            if item.get("thumbnail"):
                embed.set_thumbnail(url=item["thumbnail"])

            await interaction.followup.send(embed=embed)

from __future__ import annotations
import os, json, random
import discord
from discord import app_commands

def _load(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path,"r",encoding="utf-8") as f:
        return json.load(f)

def register_twitch_drops(bot, data_dir: str) -> None:
    reg_path = os.path.join(data_dir, "twitch_drops_registry.json")
    REG = _load(reg_path)

    drops_group = app_commands.Group(name="drops", description="Twitch Drops (curated registry, official links).")

    @drops_group.command(name="list", description="List curated drops programs, optionally filtered by game.")
    @app_commands.describe(game="Optional game filter (case-insensitive substring)")
    async def drops_list(interaction: discord.Interaction, game: str = ""):
        items = (REG.get("items", []) or [])
        if game:
            g = game.strip().lower()
            items = [x for x in items if g in (x.get("game","").lower())]
        if not items:
            await interaction.response.send_message("No matching items in twitch_drops_registry.json.", ephemeral=True)
            return
        e = discord.Embed(title="Twitch Drops — curated registry")
        for it in items[:8]:
            name = it.get("name") or it.get("game") or "Drops program"
            line = []
            if it.get("game"):
                line.append(f"Game: **{it['game']}**")
            if it.get("official_url"):
                line.append(f"Official: {it['official_url']}")
            if it.get("notes"):
                line.append(str(it["notes"]))
            e.add_field(name=name, value="\n".join(line)[:1024], inline=False)
        if len(items) > 8:
            e.set_footer(text=f"+ {len(items)-8} more in registry")
        await interaction.response.send_message(embed=e, ephemeral=True)

    @drops_group.command(name="random", description="Pick a random curated drops program.")
    async def drops_random(interaction: discord.Interaction):
        items = (REG.get("items", []) or [])
        if not items:
            await interaction.response.send_message("Registry is empty.", ephemeral=True)
            return
        it = random.choice(items)
        e = discord.Embed(title=it.get("name") or "Twitch Drops")
        if it.get("game"):
            e.add_field(name="Game", value=str(it["game"]), inline=True)
        if it.get("official_url"):
            e.add_field(name="Official source", value=str(it["official_url"]), inline=False)
        if it.get("notes"):
            e.description = str(it["notes"])[:4000]
        await interaction.response.send_message(embed=e, ephemeral=True)

    twitch_group = None
    # Attach as /twitch drops if /twitch group exists; otherwise register standalone
    for c in bot.tree.get_commands():
        if isinstance(c, app_commands.Group) and c.name == "twitch":
            twitch_group = c
            break
    if twitch_group:
        twitch_group.add_command(drops_group)
    else:
        bot.tree.add_command(drops_group)

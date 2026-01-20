import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

import discord
from discord import app_commands

UTILITY_REMINDERS_FILE = "utility_reminders.json"

def _load_json(path: str, default: Any) -> Any:
    try:
        if not os.path.exists(path):
            return default
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def _save_json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def _path(data_dir: str) -> str:
    return os.path.join(data_dir, UTILITY_REMINDERS_FILE)

def _utc_now() -> datetime:
    return datetime.utcnow().replace(microsecond=0)

class UtilityGroup(app_commands.Group):
    def __init__(self, bot: discord.Client, data_dir: str):
        super().__init__(name="utility", description="Utility commands")
        self._bot = bot
        self._data_dir = data_dir

    @app_commands.command(name="ping", description="Check bot latency")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Pong. Latency: {int(self._bot.latency*1000)}ms")

    @app_commands.command(name="serverinfo", description="Show server info")
    async def serverinfo(self, interaction: discord.Interaction):
        g = interaction.guild
        if not g:
            await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
            return
        embed = discord.Embed(title="Server info")
        embed.add_field(name="Name", value=g.name, inline=True)
        embed.add_field(name="Members", value=str(g.member_count or 0), inline=True)
        embed.add_field(name="Created", value=g.created_at.isoformat(), inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="poll", description="Create a quick poll with up to 5 options")
    @app_commands.describe(question="Poll question", option1="Option 1", option2="Option 2", option3="Option 3", option4="Option 4", option5="Option 5")
    async def poll(self, interaction: discord.Interaction, question: str, option1: str, option2: str, option3: str = "", option4: str = "", option5: str = ""):
        opts = [option1, option2, option3, option4, option5]
        opts = [o.strip() for o in opts if o and o.strip()]
        if len(opts) < 2:
            await interaction.response.send_message("Provide at least 2 options.", ephemeral=True)
            return
        emoji = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣"]
        desc = "
".join([f"{emoji[i]} {opts[i]}" for i in range(len(opts))])
        embed = discord.Embed(title=question.strip()[:256], description=desc[:4096])
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        for i in range(len(opts)):
            await msg.add_reaction(emoji[i])

    @app_commands.command(name="remind", description="Set a simple reminder (minutes)")
    @app_commands.describe(minutes="Minutes from now", text="Reminder text")
    async def remind(self, interaction: discord.Interaction, minutes: int, text: str):
        if minutes < 1 or minutes > 10080:
            await interaction.response.send_message("Minutes must be between 1 and 10080.", ephemeral=True)
            return
        due = _utc_now() + timedelta(minutes=int(minutes))
        obj = _load_json(_path(self._data_dir), {"version": 1, "items": []})
        obj["items"].append({
            "guild_id": int(interaction.guild_id or 0),
            "channel_id": int(interaction.channel_id),
            "user_id": int(interaction.user.id),
            "due_utc": due.isoformat() + "Z",
            "text": (text or "").strip()[:500]
        })
        _save_json(_path(self._data_dir), obj)
        await interaction.response.send_message(f"Reminder set for {minutes} minute(s).", ephemeral=True)

async def register_utility(bot: discord.Client, data_dir: str) -> None:
    group = UtilityGroup(bot, data_dir)
    bot.tree.add_command(group)

    # Reminder background loop
    if not hasattr(bot, "_utility_reminders_task"):
        async def _reminder_loop():
            await bot.wait_until_ready()
            while not bot.is_closed():
                try:
                    path = _path(data_dir)
                    obj = _load_json(path, {"version": 1, "items": []})
                    items = obj.get("items", [])
                    if items:
                        now = _utc_now()
                        keep = []
                        for it in items:
                            try:
                                due = datetime.fromisoformat(it.get("due_utc","").replace("Z",""))
                            except Exception:
                                keep.append(it)
                                continue
                            if due <= now:
                                gid = int(it.get("guild_id", 0) or 0)
                                cid = int(it.get("channel_id", 0) or 0)
                                uid = int(it.get("user_id", 0) or 0)
                                txt = it.get("text", "")
                                ch = None
                                if gid:
                                    g = bot.get_guild(gid)
                                    if g:
                                        ch = g.get_channel(cid)
                                if isinstance(ch, discord.TextChannel):
                                    await ch.send(f"<@{uid}> Reminder: {txt}")
                            else:
                                keep.append(it)
                        obj["items"] = keep
                        _save_json(path, obj)
                except Exception:
                    pass
                await asyncio.sleep(15)
        bot._utility_reminders_task = asyncio.create_task(_reminder_loop())

    await bot.tree.sync()

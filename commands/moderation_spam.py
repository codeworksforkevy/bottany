import os
import json
import re
from typing import Any, Dict, List

import discord
from discord import app_commands

SPAM_FILE = "spam_keywords.json"

def _path(data_dir: str) -> str:
    return os.path.join(data_dir, SPAM_FILE)

def _load(data_dir: str) -> Dict[str, Any]:
    default = {"version": 1, "enabled": True, "keywords": ["free nitro", "steam gift", "airdrop"], "regex": []}
    try:
        p = _path(data_dir)
        if not os.path.exists(p):
            return default
        with open(p, "r", encoding="utf-8") as f:
            obj = json.load(f)
        if not isinstance(obj, dict):
            return default
        obj.setdefault("enabled", True)
        obj.setdefault("keywords", [])
        obj.setdefault("regex", [])
        return obj
    except Exception:
        return default

def _save(data_dir: str, obj: Dict[str, Any]) -> None:
    os.makedirs(data_dir, exist_ok=True)
    with open(_path(data_dir), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

class ModerationGroup(app_commands.Group):
    def __init__(self, bot: discord.Client, data_dir: str):
        super().__init__(name="moderation", description="Moderation tools (keyword/spam detection)")
        self._bot = bot
        self._data_dir = data_dir

    @app_commands.command(name="spam_status", description="Show spam filter status")
    async def spam_status(self, interaction: discord.Interaction):
        obj = _load(self._data_dir)
        embed = discord.Embed(title="Spam filter status")
        embed.add_field(name="Enabled", value=str(bool(obj.get("enabled", True))), inline=True)
        embed.add_field(name="Keywords", value=str(len(obj.get("keywords", []) or [])), inline=True)
        embed.add_field(name="Regex", value=str(len(obj.get("regex", []) or [])), inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="spam_enable", description="Admin: enable/disable spam filter")
    @app_commands.describe(enabled="Enable or disable")
    async def spam_enable(self, interaction: discord.Interaction, enabled: bool):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need Manage Server permission.", ephemeral=True)
            return
        obj = _load(self._data_dir)
        obj["enabled"] = bool(enabled)
        _save(self._data_dir, obj)
        await interaction.response.send_message(f"Spam filter enabled: {enabled}", ephemeral=True)

    @app_commands.command(name="spam_add", description="Admin: add keyword to spam filter")
    @app_commands.describe(keyword="Keyword (case-insensitive substring match)")
    async def spam_add(self, interaction: discord.Interaction, keyword: str):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need Manage Server permission.", ephemeral=True)
            return
        k = (keyword or "").strip().lower()
        if not k:
            await interaction.response.send_message("Keyword cannot be empty.", ephemeral=True)
            return
        obj = _load(self._data_dir)
        kws = set([str(x).lower() for x in (obj.get("keywords", []) or [])])
        kws.add(k)
        obj["keywords"] = sorted(kws)
        _save(self._data_dir, obj)
        await interaction.response.send_message("Added.", ephemeral=True)

    @app_commands.command(name="spam_remove", description="Admin: remove keyword from spam filter")
    @app_commands.describe(keyword="Keyword to remove")
    async def spam_remove(self, interaction: discord.Interaction, keyword: str):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need Manage Server permission.", ephemeral=True)
            return
        k = (keyword or "").strip().lower()
        obj = _load(self._data_dir)
        obj["keywords"] = [x for x in (obj.get("keywords", []) or []) if str(x).lower() != k]
        _save(self._data_dir, obj)
        await interaction.response.send_message("Removed.", ephemeral=True)

    @app_commands.command(name="spam_list", description="List spam keywords")
    async def spam_list(self, interaction: discord.Interaction):
        obj = _load(self._data_dir)
        kws = obj.get("keywords", []) or []
        rx = obj.get("regex", []) or []
        embed = discord.Embed(title="Spam filter lists")
        embed.add_field(name="Keywords", value=("
".join([f"• {x}" for x in kws])[:1024] or "(none)"), inline=False)
        embed.add_field(name="Regex", value=("
".join([f"• {x}" for x in rx])[:1024] or "(none)"), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def register_moderation_spam(bot: discord.Client, data_dir: str) -> None:
    group = ModerationGroup(bot, data_dir)
    bot.tree.add_command(group)

    @bot.event
    async def on_message(message: discord.Message):
        # Allow other handlers
        try:
            await bot.process_commands(message)
        except Exception:
            pass

        if not message.guild or message.author.bot:
            return
        obj = _load(data_dir)
        if not obj.get("enabled", True):
            return
        content = (message.content or "").lower()
        keywords = obj.get("keywords", []) or []
        regexes = obj.get("regex", []) or []

        hit = any(k in content for k in keywords if isinstance(k, str) and k)
        if not hit:
            for r in regexes:
                try:
                    if re.search(r, content, flags=re.IGNORECASE):
                        hit = True
                        break
                except Exception:
                    continue
        if hit:
            # Best-effort delete
            try:
                await message.delete()
            except Exception:
                pass
            try:
                await message.channel.send(f"{message.author.mention} Your message was removed by the spam filter.")
            except Exception:
                pass

    await bot.tree.sync()

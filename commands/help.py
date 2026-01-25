from __future__ import annotations
import os, json
from typing import Any, Dict, Optional
import discord
from discord import app_commands

def _load(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path,"r",encoding="utf-8") as f:
        return json.load(f)

def register_help(bot, data_dir: str) -> None:
    """
    Hybrid help:
    - auto-discovers commands from bot.tree
    - allows curated overrides (categories, descriptions, examples) via data/help_registry.json
    """
    reg_path = os.path.join(data_dir, "help_registry.json")
    REG = _load(reg_path)

    help_group = app_commands.Group(name="help", description="Help & command guide.")

    def _cmd_key(cmd: app_commands.Command) -> str:
        # group command becomes "group sub" in UI; use qualified name when possible
        try:
            return cmd.qualified_name
        except Exception:
            return cmd.name

    def _auto_entries() -> list[dict]:
        entries = []
        for cmd in bot.tree.walk_commands():
            if isinstance(cmd, app_commands.Group):
                continue
            if getattr(cmd, "hidden", False):
                continue
            entries.append({
                "name": _cmd_key(cmd),
                "description": (cmd.description or "").strip(),
            })
        entries.sort(key=lambda x: x["name"].lower())
        return entries

    def _merged_entries() -> list[dict]:
        auto = {e["name"]: e for e in _auto_entries()}
        curated = {e.get("name",""): e for e in (REG.get("entries", []) or []) if e.get("name")}
        # merge curated on top of auto
        out = []
        for name, a in auto.items():
            c = curated.get(name, {})
            m = dict(a)
            m.update({k:v for k,v in c.items() if v not in (None,"")})
            out.append(m)
        # add curated entries for commands not introspected (future)
        for name, c in curated.items():
            if name not in auto:
                out.append(c)
        out.sort(key=lambda x: x.get("name","").lower())
        return out

    @help_group.command(name="commands", description="List all commands (auto + curated).")
    async def help_commands(interaction: discord.Interaction):
        entries = _merged_entries()
        if not entries:
            await interaction.response.send_message("No commands discovered.", ephemeral=True)
            return
        e = discord.Embed(title="Commands", description="Auto-discovered with curated overrides.")
        # compact list
        lines = []
        for it in entries[:60]:
            desc = (it.get("description","") or "").strip()
            lines.append(f"• **/{it.get('name')}** — {desc}" if desc else f"• **/{it.get('name')}**")
        e.description = "\n".join(lines)[:4000]
        if len(entries) > 60:
            e.set_footer(text=f"+ {len(entries)-60} more commands. Use /help command <name> for details.")
        await interaction.response.send_message(embed=e, ephemeral=True)

    @help_group.command(name="command", description="Explain one command (curated if available).")
    @app_commands.describe(name="Command name, e.g. 'twitch watch' or 'ping'")
    async def help_command(interaction: discord.Interaction, name: str):
        q = (name or "").strip().lstrip("/").lower()
        entries = _merged_entries()
        hit = None
        for it in entries:
            if (it.get("name","").lower() == q):
                hit = it
                break
        if not hit:
            # fuzzy: startswith
            cand = [it for it in entries if it.get("name","").lower().startswith(q)]
            hit = cand[0] if cand else None
        if not hit:
            await interaction.response.send_message("Command not found. Try /help commands.", ephemeral=True)
            return

        e = discord.Embed(title=f"/{hit.get('name')}")
        if hit.get("description"):
            e.description = hit["description"]
        if hit.get("usage"):
            e.add_field(name="Usage", value=str(hit["usage"])[:1024], inline=False)
        ex = hit.get("examples", []) or []
        if ex:
            e.add_field(name="Examples", value="\n".join(f"• {x}" for x in ex[:8])[:1024], inline=False)
        cat = hit.get("category")
        if cat:
            e.set_footer(text=f"Category: {cat}")
        await interaction.response.send_message(embed=e, ephemeral=True)

    bot.tree.add_command(help_group)


from __future__ import annotations
import datetime as dt
import json
import os
import discord
from discord import app_commands
from discord.ext import tasks

CONFIG_FILE = "weekly_config.json"
LAST_POST_AT = None

DEFAULT_IMAGE_URL = "https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/discord.svg"

def _cfg_path(data_dir: str) -> str:
    return os.path.join(data_dir, CONFIG_FILE)

def _load_cfg(data_dir: str) -> dict:
    if not os.path.exists(_cfg_path(data_dir)):
        return {
            "enabled": True,
            "channel": "gaming",
            "image_url": DEFAULT_IMAGE_URL,
        }
    try:
        with open(_cfg_path(data_dir), "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if "image_url" not in cfg:
            cfg["image_url"] = DEFAULT_IMAGE_URL
        return cfg
    except Exception:
        return {
            "enabled": True,
            "channel": "gaming",
            "image_url": DEFAULT_IMAGE_URL,
        }

def _save_cfg(data_dir: str, cfg: dict) -> None:
    with open(_cfg_path(data_dir), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

async def _build_weekly_embed(data_dir: str, preview: bool = False) -> discord.Embed:
    cfg = _load_cfg(data_dir)
    e = discord.Embed(
        title="🎮 Weekly Gaming Digest",
        description="Highlights of the week: free games & Twitch activity.",
        color=0x5865F2,
    )
    e.timestamp = dt.datetime.utcnow()
    footer = "Preview • Bottany" if preview else "Automated weekly post • Bottany"
    e.set_footer(text=footer)

    # Weekly image
    if cfg.get("image_url"):
        e.set_image(url=cfg["image_url"])

    # Free games
    try:
        from freegames_logic import fetch_offers
        reg_path = os.path.join(data_dir, "freegames_registry.json")
        reg = json.load(open(reg_path, "r", encoding="utf-8")) if os.path.exists(reg_path) else {}
        offers = await fetch_offers(reg, timeout_s=15)
        titles = [o.title for o in offers[:5]]
        if titles:
            e.add_field(
                name="🆓 Free Games",
                value="\n".join(f"• {t}" for t in titles),
                inline=False,
            )
        else:
            e.add_field(name="🆓 Free Games", value="No active free games.", inline=False)
    except Exception:
        e.add_field(name="🆓 Free Games", value="Source unavailable.", inline=False)

    # Twitch Drops
    try:
        drops_path = os.path.join(data_dir, "twitch_drops_registry.json")
        if os.path.exists(drops_path):
            drops = json.load(open(drops_path, "r", encoding="utf-8")).get("drops", [])
            active = [d for d in drops if str(d.get("status")).lower() == "active"]
            if active:
                lines = [f"• {d.get('game','')} — {d.get('campaign','')}" for d in active[:5]]
                e.add_field(name="🎁 Twitch Drops", value="\n".join(lines), inline=False)
            else:
                e.add_field(name="🎁 Twitch Drops", value="No active drops.", inline=False)
        else:
            e.add_field(name="🎁 Twitch Drops", value="Registry not found.", inline=False)
    except Exception:
        e.add_field(name="🎁 Twitch Drops", value="Source unavailable.", inline=False)

    return e

async def _post_weekly(client: discord.Client, data_dir: str):
    global LAST_POST_AT
    cfg = _load_cfg(data_dir)
    if not cfg.get("enabled", True):
        return

    channel_name = cfg.get("channel", "gaming")
    embed = await _build_weekly_embed(data_dir, preview=False)

    for g in client.guilds:
        ch = discord.utils.get(g.text_channels, name=channel_name)
        if not ch:
            continue
        await ch.send(embed=embed)
        LAST_POST_AT = dt.datetime.utcnow()

def register_weekly(client: discord.Client, tree: app_commands.CommandTree, data_dir: str):
    @tree.command(name="weekly_preview", description="Preview the next weekly post (ephemeral).")
    async def weekly_preview(interaction: discord.Interaction):
        embed = await _build_weekly_embed(data_dir, preview=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tree.command(name="weekly_status", description="Show weekly post status.")
    async def weekly_status(interaction: discord.Interaction):
        if LAST_POST_AT:
            await interaction.response.send_message(
                f"Last weekly post: {LAST_POST_AT} UTC", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "Weekly post has not run yet.", ephemeral=True
            )

    @tree.command(name="weekly_force", description="Force weekly post now.")
    async def weekly_force(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await _post_weekly(interaction.client, data_dir)
        await interaction.followup.send("Weekly post sent.", ephemeral=True)

    @tree.command(name="weekly_config", description="Configure weekly post.")
    @app_commands.describe(
        channel="Target channel name",
        enabled="Enable or disable weekly posts",
        image_url="Image URL for weekly post"
    )
    async def weekly_config(
        interaction: discord.Interaction,
        channel: str = "",
        enabled: bool = True,
        image_url: str = "",
    ):
        cfg = _load_cfg(data_dir)
        if channel:
            cfg["channel"] = channel
        cfg["enabled"] = enabled
        if image_url:
            cfg["image_url"] = image_url
        _save_cfg(data_dir, cfg)
        await interaction.response.send_message(
            f"Weekly config updated: {cfg}", ephemeral=True
        )

    @tasks.loop(hours=168)
    async def weekly_loop():
        await _post_weekly(client, data_dir)

    weekly_loop.start()

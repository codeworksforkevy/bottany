
import datetime
import discord
from discord.ext import tasks
from discord import app_commands

# ---- safe imports from shared logic ----
try:
    from freegames_logic import (
        fetch_epic_free_games,
        fetch_gog_deals,
        fetch_amazon_luna,
        fetch_humble_bundle,
    )
except Exception:
    def fetch_epic_free_games(): return []
    def fetch_gog_deals(): return []
    def fetch_amazon_luna(): return []
    def fetch_humble_bundle(): return []

# ---- helpers ----
def _fmt(items, limit=10):
    return "\n".join(f"• {i}" for i in items[:limit])

def _has_any(*groups):
    return any(bool(g) for g in groups)

def build_weekly_embed(epic, gog, luna, humble):
    embed = discord.Embed(
        title="Weekly Gaming Digest",
        description="Free games & discounts – weekly roundup",
        timestamp=datetime.datetime.utcnow(),
        color=0x2F3136,
    )

    if epic:
        embed.add_field(name="🎮 Epic Games (Free)", value=_fmt(epic), inline=False)
    if gog:
        embed.add_field(name="🎮 GOG (Deals)", value=_fmt(gog), inline=False)
    if luna:
        embed.add_field(name="☁️ Amazon Luna", value=_fmt(luna), inline=False)
    if humble:
        embed.add_field(name="📦 Humble Bundle", value=_fmt(humble), inline=False)

    return embed

# ---- main registration ----
def register_weekly(client, tree, data_dir):
    CHANNEL_ID = None  # keep your existing resolution logic if present

    # -------- admin-only preview --------
    @tree.command(name="weekly", description="Weekly gaming digest tools")
    async def weekly_root(interaction: discord.Interaction):
        pass

    @weekly_root.command(name="preview", description="Admin-only weekly preview")
    async def weekly_preview(interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Admins only.", ephemeral=True)
            return

        epic = fetch_epic_free_games()
        gog = fetch_gog_deals()
        luna = fetch_amazon_luna()
        humble = fetch_humble_bundle()

        if not _has_any(epic, gog, luna, humble):
            await interaction.response.send_message("No weekly content available.", ephemeral=True)
            return

        embed = build_weekly_embed(epic, gog, luna, humble)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # -------- Friday auto post --------
    @tasks.loop(hours=24)
    async def friday_poster():
        now = datetime.datetime.utcnow()
        if now.weekday() != 4:  # 0=Mon ... 4=Fri
            return

        epic = fetch_epic_free_games()
        gog = fetch_gog_deals()
        luna = fetch_amazon_luna()
        humble = fetch_humble_bundle()

        if not _has_any(epic, gog, luna, humble):
            return

        channel = client.get_channel(CHANNEL_ID) if CHANNEL_ID else None
        if not channel:
            return

        embed = build_weekly_embed(epic, gog, luna, humble)
        await channel.send(embed=embed)

    if not getattr(client, "_weekly_started", False):
        client._weekly_started = True
        friday_poster.start()

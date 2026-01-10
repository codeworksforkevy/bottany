from __future__ import annotations

import os
import aiohttp
import discord
from discord import app_commands

from utils.twitch_oauth import TwitchAppTokenCache
from utils.twitch_helix import get_drops_entitlements
from utils.twitch_registry import load_curated_items

def register_twitch_badges_and_drops(bot: discord.Client, data_dir: str) -> None:
    """Registers /twitch badges_and_drops (displayed as: /twitch badges and drops)."""

    twitch = app_commands.Group(name="twitch", description="Twitch commands (curated + official).")

    @twitch.command(
        name="badges_and_drops",
        description="Shows Twitch badges and drops (official/authorized + curated/global).",
    )
    @app_commands.describe(game="Optional filter for curated items (best-effort)")
    async def badges_and_drops(interaction: discord.Interaction, game: str | None = None):
        await interaction.response.defer(ephemeral=True)

        # --- GLOBAL (curated) ---
        curated = load_curated_items(data_dir)
        if game:
            q = game.strip().lower()
            curated = [x for x in curated if q in (x.get("game","").lower()) or q in (x.get("title","").lower())]

        # --- LIVE (official/authorized scope) ---
        live_summary = ""
        client_id = os.getenv("TWITCH_CLIENT_ID", "").strip()
        client_secret = os.getenv("TWITCH_CLIENT_SECRET", "").strip()
        game_id = os.getenv("TWITCH_GAME_ID", "").strip() or None

        if client_id and client_secret:
            try:
                async with aiohttp.ClientSession() as session:
                    token = await TwitchAppTokenCache().get(session, client_id, client_secret)
                    entitlements = await get_drops_entitlements(
                        session,
                        client_id=client_id,
                        bearer_token=token,
                        game_id=game_id,
                        first=20,
                    )
                live_summary = f"Found {len(entitlements)} entitlement item(s) (authorized scope)."
            except Exception as e:
                live_summary = f"Live (API) unavailable: {e}"
        else:
            live_summary = "Live (API) disabled: missing TWITCH_CLIENT_ID / TWITCH_CLIENT_SECRET."

        embed = discord.Embed(
            title="Twitch — Badges and Drops",
            description="Combined view: LIVE (official/authorized) + GLOBAL (curated).",
        )
        embed.add_field(name="LIVE (Official / Authorized)", value=live_summary[:1024], inline=False)

        if curated:
            lines = []
            for item in curated[:10]:
                title = item.get("title", "Untitled")
                game_name = item.get("game", "Unknown game")
                source = item.get("source", "")
                when = item.get("end", "") or item.get("start", "")
                extra = []
                if when:
                    extra.append(str(when))
                if source:
                    extra.append(str(source))
                suffix = " — " + ", ".join(extra) if extra else ""
                lines.append(f"• **{title}** — {game_name}{suffix}")
            embed.add_field(name="GLOBAL (Curated)", value="\n".join(lines)[:1024], inline=False)
        else:
            embed.add_field(name="GLOBAL (Curated)", value="No curated items matched.", inline=False)

        embed.set_footer(text="Use /help twitch badges and drops for guidance. We love Kevy")
        await interaction.followup.send(embed=embed, ephemeral=True)

    bot.tree.add_command(twitch)

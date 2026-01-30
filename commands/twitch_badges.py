# commands/twitch_badges.py
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import discord
import aiohttp


BADGES_COLOR = 0x9146FF  # Twitch purple


async def _fetch_global_badges(session: aiohttp.ClientSession, client_id: str, token: str) -> List[Dict[str, Any]]:
    """
    Helix Chat Badges (global):
      GET https://api.twitch.tv/helix/chat/badges/global
    Requires:
      - TWITCH_CLIENT_ID
      - TWITCH_OAUTH_TOKEN (App Access Token or User Token that passes validation)
    """
    url = "https://api.twitch.tv/helix/chat/badges/global"
    headers = {
        "Client-Id": client_id,
        "Authorization": f"Bearer {token}",
    }
    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as r:
        r.raise_for_status()
        data = await r.json()
    return data.get("data", []) or []


def register_twitch_badges(client: discord.Client, tree: discord.app_commands.CommandTree) -> None:
    """
    Registers /badges (top-level). This avoids 'CommandNotFound: badges' as long as
    you import + call this registrar from main.py before tree.sync().
    """

    @tree.command(name="badges", description="Show latest Twitch global chat badges (via official Helix API).")
    async def badges(interaction: discord.Interaction):
        client_id = os.getenv("TWITCH_CLIENT_ID", "").strip()
        token = os.getenv("TWITCH_OAUTH_TOKEN", "").strip()

        if not client_id or not token:
            await interaction.response.send_message(
                "Missing TWITCH_CLIENT_ID or TWITCH_OAUTH_TOKEN env vars.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=False)

        async with aiohttp.ClientSession() as session:
            try:
                sets = await _fetch_global_badges(session, client_id=client_id, token=token)
            except Exception as e:
                await interaction.followup.send(f"Unable to fetch Twitch badges: {type(e).__name__}: {e}", ephemeral=True)
                return

        # Show a compact list to avoid embed overflows
        lines: List[str] = []
        for s in sets[:10]:
            set_id = s.get("set_id") or "unknown"
            versions = s.get("versions") or []
            # pick first version for name
            if versions:
                v = versions[0]
                title = (v.get("title") or "").strip()
                desc = (v.get("description") or "").strip()
                lines.append(f"• **{title or set_id}** — {desc[:120]}")
            else:
                lines.append(f"• **{set_id}**")

        e = discord.Embed(
            title="Twitch global chat badges",
            description="Latest badge sets detected via official Helix API.",
            color=BADGES_COLOR,
        )
        e.add_field(name="Sets", value="\n".join(lines)[:1024], inline=False)
        e.set_footer(text="Tip: set TWITCH_CLIENT_ID + TWITCH_OAUTH_TOKEN in Railway Variables.")
        await interaction.followup.send(embed=e, ephemeral=False)

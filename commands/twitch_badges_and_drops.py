from __future__ import annotations

import os
import aiohttp
import discord
from discord import app_commands
from datetime import datetime, date

from utils.twitch_oauth import TwitchAppTokenCache
from utils.twitch_helix import get_drops_entitlements
from utils.twitch_registry import load_curated_items

def _parse_iso(d: str | None) -> date | None:
    if not d:
        return None
    try:
        return datetime.strptime(d, "%Y-%m-%d").date()
    except Exception:
        return None

def _status(start_s: str | None, end_s: str | None) -> str:
    today = date.today()
    start = _parse_iso(start_s)
    end = _parse_iso(end_s)
    if start and today < start:
        return "Upcoming"
    if end and today > end:
        return "Ended"
    return "Active"

def register_twitch_badges_and_drops(bot: discord.Client, data_dir: str) -> None:
    """Registers /twitch badges_and_drops (shown in help as: /twitch badges and drops)."""

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
            curated = [
                x for x in curated
                if q in (x.get("game", "").lower()) or q in (x.get("title", "").lower())
            ]

        # Sort curated: Active -> Upcoming -> Ended, then by start desc
        def _sort_key(x: dict):
            s = _status(x.get("start"), x.get("end"))
            pri = {"Active": 0, "Upcoming": 1, "Ended": 2}.get(s, 9)
            start = _parse_iso(x.get("start")) or date(1970, 1, 1)
            return (pri, -start.toordinal())

        curated = sorted(curated, key=_sort_key)

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
                live_summary = f"✅ Retrieved **{len(entitlements)}** entitlement item(s) (authorized scope)."
            except Exception as e:
                live_summary = f"⚠️ Live (API) unavailable: `{e}`"
        else:
            live_summary = "ℹ️ Live (API) disabled: missing `TWITCH_CLIENT_ID` / `TWITCH_CLIENT_SECRET`."

        # --- Build Embed ---
        embed = discord.Embed(
            title="Twitch — Badges & Drops",
            description="A combined view of **LIVE** (official/authorized) and **GLOBAL** (curated catalogue).",
        )
        embed.set_author(name="Bottany Help • Twitch", icon_url="https://static-cdn.jtvnw.net/jtv_user_pictures/0e6a9186-39f1-4b0b-8f08-7fdbf2aab2c4-profile_image-70x70.png")

        embed.add_field(
            name="LIVE (Official / Authorized)",
            value=live_summary[:1024],
            inline=False,
        )

        if curated:
            lines = []
            for item in curated[:10]:
                title = item.get("title", "Untitled")
                game_name = item.get("game", "Unknown game")
                start = item.get("start")
                end = item.get("end")
                st = _status(start, end)

                badge = "🟢" if st == "Active" else ("🟡" if st == "Upcoming" else "⚫")
                src_url = item.get("source_url", "")
                src_label = item.get("source", "Source")
                when = f"{start or '—'} → {end or '—'}"

                # Markdown link if URL present
                src = f"[{src_label}]({src_url})" if src_url else src_label
                lines.append(f"{badge} **{title}** — *{game_name}*\n`{when}` • {src}")

            embed.add_field(
                name="GLOBAL (Curated Catalogue)",
                value="\n\n".join(lines)[:1024],
                inline=False,
            )
        else:
            embed.add_field(
                name="GLOBAL (Curated Catalogue)",
                value="No curated items matched your filter.",
                inline=False,
            )

        embed.set_footer(text="Tip: /twitch badges_and_drops <game> • /help twitch badges and drops • We love Kevy")
        await interaction.followup.send(embed=embed, ephemeral=True)

    bot.tree.add_command(twitch)

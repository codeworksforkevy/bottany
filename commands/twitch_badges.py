"""All-in-one Twitch badges UX upgrade for discord.py 2.x

Includes:
- Summary embed
- One-badge-per-embed display
- Badge-type colors
- Ultra-minimal text density
- Pagination (Prev/Next) for /badges all and /badges new
- Optional combined feed: /twitch feed (badges + optional drops registry)

Env vars:
- TWITCH_CLIENT_ID
- TWITCH_APP_TOKEN (App access token, WITHOUT "Bearer ")
Optional:
- DATA_DIR (default: data)

Notes:
- Uses Twitch Helix: GET /helix/chat/badges/global
- Persists last-seen snapshot at {DATA_DIR}/twitch_badges_seen.json
"""

from __future__ import annotations

import os
import re
import time
import json
from dataclasses import dataclass
from typing import Any, Dict, List

import aiohttp
import discord
from discord import app_commands


@dataclass(frozen=True)
class TwitchBadge:
    title: str
    set_id: str
    version: str
    scope: str
    image_url: str
    description: str = ""


COLOR_TWITCH_PURPLE = 0x9146FF
COLOR_STAFF = 0x7A3DF0
COLOR_ANNIVERSARY = 0x2563EB
COLOR_EVENT = 0xF59E0B
COLOR_PARTNER = 0x10B981
COLOR_SUB = 0xEC4899
COLOR_BITS = 0xF97316
COLOR_DEFAULT = COLOR_TWITCH_PURPLE

FOOTER_SUMMARY = "Twitch • Chat Badges • Helix API"
FOOTER_ITEM = "Twitch • Badge"


def _truncate(s: str, n: int) -> str:
    s = (s or "").strip()
    if len(s) <= n:
        return s
    return s[: n - 1].rstrip() + "…"


def _infer_badge_color(set_id: str, title: str, desc: str) -> int:
    s = f"{set_id} {title} {desc}".lower()

    if "staff" in s:
        return COLOR_STAFF
    if any(k in s for k in ["partner", "verified"]):
        return COLOR_PARTNER
    if any(k in s for k in ["subscriber", "sub", "prime", "founder"]):
        return COLOR_SUB
    if any(k in s for k in ["bits", "cheer", "bit", "cheering"]):
        return COLOR_BITS
    if re.search(r"\b(\d{1,2})\s*years?\b", s) or "anniversary" in s:
        return COLOR_ANNIVERSARY
    if any(k in s for k in ["event", "campaign", "celebrat", "festival", "season", "revolution", "drops", "drop"]):
        return COLOR_EVENT
    return COLOR_DEFAULT


HELIX_GLOBAL_BADGES = "https://api.twitch.tv/helix/chat/badges/global"


class TwitchAPIError(RuntimeError):
    pass


async def fetch_global_badges(client_id: str, app_token: str, session: aiohttp.ClientSession) -> List[TwitchBadge]:
    if not client_id or not app_token:
        raise TwitchAPIError("Missing TWITCH_CLIENT_ID or TWITCH_APP_TOKEN.")

    headers = {"Client-ID": client_id, "Authorization": f"Bearer {app_token}"}
    async with session.get(HELIX_GLOBAL_BADGES, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
        if resp.status != 200:
            txt = await resp.text()
            raise TwitchAPIError(f"Twitch API error {resp.status}: {_truncate(txt, 300)}")
        payload = await resp.json()

    out: List[TwitchBadge] = []
    for set_obj in payload.get("data", []) or []:
        set_id = str(set_obj.get("set_id", "")).strip()
        for v in (set_obj.get("versions", []) or []):
            version = str(v.get("id", "")).strip()
            title = str(v.get("title", "")).strip() or set_id
            desc = str(v.get("description", "")).strip()
            image_url = (
                str(v.get("image_url_1x", "")).strip()
                or str(v.get("image_url_2x", "")).strip()
                or str(v.get("image_url_4x", "")).strip()
            )
            if not (set_id and version and image_url):
                continue
            out.append(TwitchBadge(title=title, set_id=set_id, version=version, scope="Global", image_url=image_url, description=desc))

    out.sort(key=lambda b: (b.set_id.lower(), b.version.lower(), b.title.lower()))
    return out


def _load_json(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _save_json(path: str, obj: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def build_summary_embed(count: int, label: str) -> discord.Embed:
    e = discord.Embed(title=label, description=f"{count} badge(s).", color=COLOR_TWITCH_PURPLE)
    e.set_footer(text=FOOTER_SUMMARY)
    return e


def build_badge_embed(b: TwitchBadge) -> discord.Embed:
    e = discord.Embed(
        title=_truncate(b.title, 256),
        description=_truncate(b.description, 140) if b.description else "",
        color=_infer_badge_color(b.set_id, b.title, b.description),
    )
    e.set_thumbnail(url=b.image_url)
    e.add_field(name="Set", value=_truncate(b.set_id, 1024), inline=True)
    e.add_field(name="v", value=_truncate(b.version, 1024), inline=True)
    e.set_footer(text=FOOTER_ITEM)
    return e


class BadgePager(discord.ui.View):
    def __init__(self, badges: List[TwitchBadge], summary: discord.Embed, timeout: int = 180):
        super().__init__(timeout=timeout)
        self.badges = badges
        self.summary = summary
        self.i = 0

    def _page_embeds(self) -> List[discord.Embed]:
        badge = self.badges[self.i]
        s = discord.Embed.from_dict(self.summary.to_dict())
        s.description = f"{len(self.badges)} badge(s) • {self.i+1}/{len(self.badges)}"
        return [s, build_badge_embed(badge)]

    async def on_timeout(self) -> None:
        # Disable buttons when the view expires so users don't get "Interaction failed".
        for child in self.children:
            try:
                child.disabled = True
            except Exception:
                pass
        if getattr(self, "message", None) is not None:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass

    async def _update(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message(embeds=self._page_embeds(), view=self)

    @discord.ui.button(label="Prev", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.i > 0:
            self.i -= 1
        await self._update(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.i < len(self.badges) - 1:
            self.i += 1
        await self._update(interaction)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)


def _load_drops_registry(data_dir: str) -> List[Dict[str, Any]]:
    path = os.path.join(data_dir, "twitch_drops_registry.json")
    reg = _load_json(path)
    drops = reg.get("drops", []) if isinstance(reg, dict) else []
    if not isinstance(drops, list):
        return []
    return [d for d in drops if isinstance(d, dict)]


def build_drops_embed(active: List[Dict[str, Any]]) -> discord.Embed:
    e = discord.Embed(title="Twitch Drops", color=COLOR_EVENT)
    lines = []
    for d in active[:3]:
        game = str(d.get("game", "")).strip()
        camp = str(d.get("campaign", "")).strip()
        url = str(d.get("url", "")).strip()
        label = " • ".join([x for x in [game, camp] if x]) or "Drop"
        if url:
            lines.append(f"• {label}\n{url}")
        else:
            lines.append(f"• {label}")
    e.description = "\n".join(lines) if lines else f"{len(active)} active item(s)."
    e.set_footer(text="Twitch • Drops (curated)")
    return e


def register_twitch_badges(bot: discord.Client, data_dir: str) -> None:
    os.makedirs(data_dir, exist_ok=True)
    seen_path = os.path.join(data_dir, "twitch_badges_seen.json")

    badges_group = app_commands.Group(name="badges", description="Twitch badges (minimal).")
    twitch_group = app_commands.Group(name="twitch", description="Twitch utilities (minimal).")

    @badges_group.command(name="new", description="New global Twitch badges (minimal + paginated).")
    async def badges_new(interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=False)
        client_id = os.getenv("TWITCH_CLIENT_ID", "").strip()
        app_token = os.getenv("TWITCH_APP_TOKEN", "").strip()

        try:
            async with aiohttp.ClientSession() as session:
                badges = await fetch_global_badges(client_id, app_token, session)
        except Exception as e:
            await interaction.followup.send(f"Unable to fetch Twitch badges. ({type(e).__name__}: {e})")
            return

        last_seen = _load_json(seen_path)
        prev_keys = set(last_seen.get("keys") or [])

        keys = [f"{b.set_id}:{b.version}" for b in badges]
        new_badges = [b for b in badges if f"{b.set_id}:{b.version}" not in prev_keys]

        _save_json(seen_path, {"ts": int(time.time()), "keys": keys})

        summary = build_summary_embed(len(new_badges), "New Twitch Badges Detected")
        if not new_badges:
            await interaction.followup.send(embeds=[summary])
            return

        view = BadgePager(new_badges, summary)
        await interaction.followup.send(embeds=view._page_embeds(), view=view)

    @badges_group.command(name="all", description="All global Twitch badges (minimal + paginated).")
    async def badges_all(interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=False)
        client_id = os.getenv("TWITCH_CLIENT_ID", "").strip()
        app_token = os.getenv("TWITCH_APP_TOKEN", "").strip()

        try:
            async with aiohttp.ClientSession() as session:
                badges = await fetch_global_badges(client_id, app_token, session)
        except Exception as e:
            await interaction.followup.send(f"Unable to fetch Twitch badges. ({type(e).__name__}: {e})")
            return

        summary = build_summary_embed(len(badges), "Global Twitch Badges")
        if not badges:
            await interaction.followup.send(embeds=[summary])
            return

        view = BadgePager(badges, summary)
        await interaction.followup.send(embeds=view._page_embeds(), view=view)

    @twitch_group.command(name="feed", description="Combined Twitch feed (badges + optional drops).")
    async def twitch_feed(interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=False)
        client_id = os.getenv("TWITCH_CLIENT_ID", "").strip()
        app_token = os.getenv("TWITCH_APP_TOKEN", "").strip()

        try:
            async with aiohttp.ClientSession() as session:
                badges = await fetch_global_badges(client_id, app_token, session)
        except Exception as e:
            await interaction.followup.send(f"Unable to fetch Twitch badges. ({type(e).__name__}: {e})")
            return

        last_seen = _load_json(seen_path)
        prev_keys = set(last_seen.get("keys") or [])
        keys = [f"{b.set_id}:{b.version}" for b in badges]
        new_badges = [b for b in badges if f"{b.set_id}:{b.version}" not in prev_keys]
        _save_json(seen_path, {"ts": int(time.time()), "keys": keys})

        feed_summary = build_summary_embed(len(new_badges), "Twitch Feed")
        embeds = [feed_summary]

        drops = _load_drops_registry(data_dir)
        active = [d for d in drops if str(d.get("status", "")).lower().strip() == "active"]
        if active:
            embeds.append(build_drops_embed(active))

        if not new_badges:
            await interaction.followup.send(embeds=embeds)
            return

        view = BadgePager(new_badges, feed_summary)
        # Keep at most 2 "feed embeds" + 1 badge = minimal and under limits.
        head = embeds[:2]
        page = view._page_embeds()
        payload = [page[0]] + head[1:] + [page[1]]
        msg = await interaction.followup.send(embeds=payload, view=view)
        try:
            view.message = msg
        except Exception:
            pass

    bot.tree.add_command(badges_group)
    bot.tree.add_command(twitch_group)
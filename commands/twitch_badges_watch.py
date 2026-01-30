from __future__ import annotations
import os, json, hashlib, logging, asyncio
from typing import Any, Dict, List, Optional
import aiohttp
import discord
from discord import app_commands
from discord.ext import tasks

logger = logging.getLogger("bottany.twitch_badges")

TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
HELIX_BASE = "https://api.twitch.tv/helix"

def _load(path: str, default: Optional[dict]=None) -> dict:
    if not os.path.exists(path):
        return default or {}
    with open(path,"r",encoding="utf-8") as f:
        return json.load(f)

def _save(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,"w",encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def _hash_obj(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

class TwitchAuth:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self._token: Optional[str] = None
        self._exp: float = 0.0

    async def get_token(self) -> Optional[str]:
        import time
        if self._token and time.time() < (self._exp - 30):
            return self._token
        if not self.client_id or not self.client_secret:
            return None
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }
        async with aiohttp.ClientSession() as s:
            async with s.post(TWITCH_TOKEN_URL, data=data, timeout=15) as r:
                if r.status != 200:
                    txt = await r.text()
                    logger.warning("Twitch token error %s: %s", r.status, txt[:200])
                    return None
                js = await r.json()
        self._token = js.get("access_token")
        expires = int(js.get("expires_in", 0) or 0)
        self._exp = time.time() + max(60, expires)
        return self._token

async def helix_get(auth: TwitchAuth, path: str, params: dict | None=None) -> dict:
    token = await auth.get_token()
    if not token:
        raise RuntimeError("Missing Twitch app credentials (TWITCH_CLIENT_ID/TWITCH_CLIENT_SECRET).")
    headers = {
        "Client-ID": auth.client_id,
        "Authorization": f"Bearer {token}",
    }
    url = HELIX_BASE + path
    async with aiohttp.ClientSession(headers=headers) as s:
        async with s.get(url, params=params or {}, timeout=20) as r:
            if r.status != 200:
                txt = await r.text()
                raise RuntimeError(f"Twitch API error {r.status}: {txt[:200]}")
            return await r.json()

def _extract_badges(data: dict) -> list[dict]:
    """
    Returns list of badges as:
    {set_id, version, title, description, image_url_1x, image_url_2x, image_url_4x}
    """
    out = []
    for s in (data.get("data") or []):
        set_id = s.get("set_id")
        for v in (s.get("versions") or []):
            out.append({
                "set_id": set_id,
                "version": v.get("id"),
                "title": v.get("title",""),
                "description": v.get("description",""),
                "image_url_1x": v.get("image_url_1x",""),
                "image_url_2x": v.get("image_url_2x",""),
                "image_url_4x": v.get("image_url_4x",""),
            })
    return out

async def register_badges(bot, data_dir: str) -> None:
    cache_path = os.path.join(data_dir, "twitch_badges_cache.json")
    # channel for posting: stored via /admin setchannel topic=twitch
    # main.py provides that, but module stays decoupled and posts to the stored channel via bot.get_channel.

    client_id = (os.getenv("TWITCH_CLIENT_ID","") or "").strip()
    client_secret = (os.getenv("TWITCH_CLIENT_SECRET","") or "").strip()
    auth = TwitchAuth(client_id, client_secret)

    state = _load(cache_path, default={"hash": "", "badges": [], "updated_utc": ""})

    badges_group = app_commands.Group(name="badges", description="Twitch badges (official API).")

    
    class _BadgesBrowserView(discord.ui.View):
        """
        Interactive browser:
        - Select menu (max 25) to pick a badge on the current page.
        - Prev/Next page buttons.
        This avoids spammy multi-embed dumps and still shows visuals (thumbnail).
        """
        def __init__(self, items: List[dict], *, page: int = 0, page_size: int = 25, timeout: int = 180):
            super().__init__(timeout=timeout)
            self.items = items
            self.page = page
            self.page_size = max(5, min(25, page_size))
            self.selected = 0  # index within page
            self._sync_select_options()

        def _page_slice(self) -> List[dict]:
            start = self.page * self.page_size
            end = min(len(self.items), start + self.page_size)
            return self.items[start:end]

        def _sync_select_options(self) -> None:
            # rebuild select options based on current page
            page_items = self._page_slice()
            options = []
            for i, it in enumerate(page_items):
                title = (it.get("title") or "(untitled)").strip()
                set_id = it.get("set_id") or "?"
                ver = it.get("version") or "?"
                label = title[:90]
                desc = f"set {set_id} v{ver}"[:100]
                options.append(discord.SelectOption(label=label, description=desc, value=str(i)))
            self.badge_select.options = options

        def _build_embed(self, updated_utc: str) -> discord.Embed:
            page_items = self._page_slice()
            total = len(self.items)
            start_i = self.page * self.page_size + 1
            end_i = self.page * self.page_size + len(page_items)
            cur = page_items[self.selected] if page_items else {}

            title = "Twitch badges — browser"
            e = discord.Embed(title=title)
            e.description = (
                f"Updated: {updated_utc or '(unknown)'}\n"
                f"Showing {start_i}-{end_i} of {total}"
            )

            # Primary visual: thumbnail
            thumb = (cur.get("image_url_4x") or cur.get("image_url_2x") or cur.get("image_url_1x") or "").strip()
            if thumb:
                e.set_thumbnail(url=thumb)

            # Badge card
            btitle = (cur.get("title") or "(untitled)").strip()
            bdesc = (cur.get("description") or "").strip()
            set_id = cur.get("set_id") or "?"
            ver = cur.get("version") or "?"
            e.add_field(name="Selected badge", value=f"**{btitle}**\nset `{set_id}` v{ver}" + (f"\n_{bdesc}_" if bdesc else ""), inline=False)

            # Helpful direct links (Discord clients often auto-preview)
            if thumb:
                e.add_field(name="Image", value=thumb, inline=False)

            # Compact list preview for context
            lines = []
            for i, it in enumerate(page_items[:10]):
                prefix = "➤" if i == self.selected else "•"
                lines.append(f"{prefix} {(it.get('title') or '(untitled)')[:70]} — `{it.get('set_id')}` v{it.get('version')}")
            e.add_field(name="This page (preview)", value="\n".join(lines)[:1024] if lines else "—", inline=False)

            e.add_field(name="Source", value="Official Twitch Helix: /chat/badges/global", inline=False)
            return e

        @discord.ui.select(placeholder="Select a badge…", min_values=1, max_values=1, options=[])
        async def badge_select(self, interaction: discord.Interaction, select: discord.ui.Select):
            try:
                self.selected = int(select.values[0])
            except Exception:
                self.selected = 0
            # updated_utc is stored on the message embed description; pass via custom_id is overkill
            # We will re-read from state in handler by storing it on view
            e = self._build_embed(self.updated_utc)
            await interaction.response.edit_message(embed=e, view=self)

        @discord.ui.button(label="Prev", style=discord.ButtonStyle.secondary)
        async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.page > 0:
                self.page -= 1
                self.selected = 0
                self._sync_select_options()
            e = self._build_embed(self.updated_utc)
            await interaction.response.edit_message(embed=e, view=self)

        @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
        async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
            max_page = (len(self.items) - 1) // self.page_size if self.items else 0
            if self.page < max_page:
                self.page += 1
                self.selected = 0
                self._sync_select_options()
            e = self._build_embed(self.updated_utc)
            await interaction.response.edit_message(embed=e, view=self)

    @badges_group.command(name="latest", description="Browse the latest cached global badges snapshot (with images).")
    @app_commands.describe(public="Post publicly in the channel (default is ephemeral).")
    async def badges_latest(interaction: discord.Interaction, public: bool = False):
        items = (state.get("badges", []) or [])
        if not items:
            await interaction.response.send_message("No badge cache yet. Wait for the watcher to run.", ephemeral=True)
            return

        # Sort deterministically: title then set_id then version
        items_sorted = sorted(items, key=lambda x: ((x.get("title") or ""), (x.get("set_id") or ""), str(x.get("version") or "")))

        view = _BadgesBrowserView(items_sorted, page=0, page_size=25)
        view.updated_utc = state.get("updated_utc","")  # attach dynamic value
        e = view._build_embed(view.updated_utc)

        await interaction.response.send_message(embed=e, view=view, ephemeral=(not public))

    bot.tree.add_command(badges_group)

    @tasks.loop(minutes=int(os.getenv("TWITCH_BADGES_POLL_MINUTES","15")))
    async def badges_watcher():
        nonlocal state
        try:
            js = await helix_get(auth, "/chat/badges/global")
            badges = _extract_badges(js)
            new_hash = _hash_obj(badges)

            if new_hash == (state.get("hash") or ""):
                return

            # detect changes (simple set diff on set_id+version)
            old_keys = set(f"{b.get('set_id')}:{b.get('version')}" for b in (state.get("badges",[]) or []))
            new_keys = set(f"{b.get('set_id')}:{b.get('version')}" for b in badges)

            added_keys = list(sorted(new_keys - old_keys))
            removed_keys = list(sorted(old_keys - new_keys))

            state = {
                "hash": new_hash,
                "badges": badges,
                "updated_utc": __import__("datetime").datetime.utcnow().replace(microsecond=0).isoformat()+"Z",
            }
            _save(cache_path, state)

            # Post update into per-guild configured twitch channel, if any.
            # We look for a helper attached by main.py (db_get_channel callable), otherwise skip.
            db_get_channel = getattr(bot, "_db_get_channel", None)
            if not callable(db_get_channel):
                return

            for g in bot.guilds:
                chan_id = db_get_channel(g.id, "twitch")
                if not chan_id:
                    continue
                ch = bot.get_channel(chan_id)
                if not ch:
                    continue

                e = discord.Embed(title=f"New Twitch badges detected ({len(added_keys)})")
                e.description = "Detected via the official Twitch API (Helix Chat Badges)."
                # Show up to 8 added
                shown = 0
                for k in added_keys[:8]:
                    set_id, ver = k.split(":",1)
                    it = next((x for x in badges if x.get("set_id")==set_id and str(x.get("version"))==ver), None)
                    if not it:
                        continue
                    line = f"**{it.get('title','Badge')}** — Global (set `{set_id}`, v `{ver}`)\n{it.get('description','')}".strip()
                    e.add_field(name=it.get("title","Badge"), value=line[:1024], inline=False)
                    if shown == 0 and it.get("image_url_2x"):
                        # IMPORTANT: this is the fix — use embed image/thumbnail, not a "download link"
                        e.set_thumbnail(url=it["image_url_2x"])
                    shown += 1

                if removed_keys:
                    e.add_field(name="Removed (snapshot diff)", value="\n".join(f"• {k}" for k in removed_keys[:8])[:1024], inline=False)

                await ch.send(embed=e)

        except Exception as e:
            logger.warning("badges_watcher error: %s", e)

    @badges_watcher.before_loop
    async def _wait_ready():
        await bot.wait_until_ready()

    if not getattr(bot, "_badges_watcher_started", False):
        bot._badges_watcher_started = True
        badges_watcher.start()

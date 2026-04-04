# consoles.py
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

import discord
from discord import app_commands

log = logging.getLogger(__name__)

REG_FILE = "consoles_full.json"

# Embed color — lemon yellow
_COLOR = 0xFFF44F

# Generation labels
_GEN_LABELS = {
    1: "1st Gen (1972–1977)",
    2: "2nd Gen (1976–1992)",
    3: "3rd Gen (1983–2003)",
    4: "4th Gen (1987–2004)",
    5: "5th Gen (1993–2006)",
    6: "6th Gen (1998–2013)",
    7: "7th Gen (2005–2017)",
    8: "8th Gen (2011–2021)",
    9: "9th Gen (2020–present)",
}


# ── Loader ────────────────────────────────────────────────────────────────────

def _load(data_dir: str) -> List[Dict[str, Any]]:
    path = os.path.join(data_dir, REG_FILE)
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        consoles = obj.get("consoles", [])
        return consoles if isinstance(consoles, list) else []
    except FileNotFoundError:
        log.error("Consoles registry not found at %s", path)
    except json.JSONDecodeError as exc:
        log.error("Consoles registry malformed: %s", exc)
    except OSError as exc:
        log.error("Could not read consoles registry: %s", exc)
    return []


# ── Helpers ───────────────────────────────────────────────────────────────────

def _release_str(c: Dict[str, Any]) -> str:
    rel = c.get("release", {})
    parts = []
    if rel.get("jp"):  parts.append(f"JP {rel['jp']}")
    if rel.get("na"):  parts.append(f"NA {rel['na']}")
    if rel.get("global"): parts.append(rel["global"])
    return "  ·  ".join(parts) if parts else "—"


def _units_str(c: Dict[str, Any]) -> str:
    u = c.get("units_sold_millions")
    if u is None: return "—"
    return f"{u}M units"


def _type_tag(c: Dict[str, Any]) -> str:
    if c.get("hybrid"):   return "Hybrid"
    if c.get("handheld"): return "Handheld"
    return "Home console"


def _thumbnail(c: Dict[str, Any]) -> str:
    """Return best available thumbnail URL — Wikimedia full as fallback.
    Priority: custom avatar CDN → Wikimedia full URL → empty string.
    """
    thumb  = c.get("thumbnail", {})
    avatar = thumb.get("avatar", "")
    full   = thumb.get("full", "")
    # Use avatar only if it's a real URL (not empty, not a placeholder)
    if avatar and "cdn.yourapp.com" not in avatar:
        return avatar
    # Fall back to Wikimedia full URL
    if full:
        return full
    return ""


_DIVIDER  = "\u200b"                        # zero-width — blank line between fields
_PIX_LINE = "░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░"  # pixel-art divider (Seçenek A)


# ── Embed builders ────────────────────────────────────────────────────────────

def _build_info_embed(c: Dict[str, Any]) -> discord.Embed:
    name  = c.get("name", "Unknown")
    brand = c.get("brand", "")
    gen   = c.get("generation")
    units = c.get("units_sold_millions")
    cpu   = c.get("cpu")

    # Description — italic subtitle
    gen_label = _GEN_LABELS.get(gen, f"Gen {gen}") if gen else None
    type_tag  = _type_tag(c)
    desc_parts = [brand]
    if gen_label:  desc_parts.append(gen_label)
    if type_tag != "Home console": desc_parts.append(type_tag)

    embed = discord.Embed(
        title=name,
        description=f"*{'  ·  '.join(desc_parts)}*",
        color=_COLOR,
    )

    # ── Release / Units / CPU fields ──────────────────────────────────────────
    rel = c.get("release", {})
    rel_lines = []
    if rel.get("jp"):     rel_lines.append(f"Japan  {rel['jp']}")
    if rel.get("na"):     rel_lines.append(f"North America  {rel['na']}")
    if rel.get("eu"):     rel_lines.append(f"Europe  {rel['eu']}")
    if rel.get("global"): rel_lines.append(rel["global"])

    if rel_lines:
        embed.add_field(name="Released", value="\n".join(rel_lines), inline=True)
    if units is not None:
        embed.add_field(name="Units sold", value=f"{units}M", inline=True)
    if cpu:
        embed.add_field(name="CPU", value=cpu, inline=True)

    # ── Pixel divider ─────────────────────────────────────────────────────────
    embed.add_field(name=_PIX_LINE, value=_DIVIDER, inline=False)

    # ── CPU note — // section header ──────────────────────────────────────────
    cpu_note = c.get("cpu_note")
    if cpu_note:
        embed.add_field(
            name="// cpu",
            value=f"*{cpu_note}*",
            inline=False,
        )

    # ── Pixel divider ─────────────────────────────────────────────────────────
    embed.add_field(name=_PIX_LINE, value=_DIVIDER, inline=False)

    # ── Innovation & Record — // section headers ───────────────────────────────
    innovation = c.get("innovation")
    record     = c.get("record")

    if innovation:
        embed.add_field(name="// innovation", value=innovation, inline=False)
    if record:
        embed.add_field(name="// record", value=f"*{record}*", inline=False)

    # ── Thumbnail ─────────────────────────────────────────────────────────────
    thumb = _thumbnail(c)
    if thumb:
        embed.set_thumbnail(url=thumb)

    embed.set_footer(text="[ BOTTANY ] ───────────────────────────────")
    return embed


def _build_compare_embed(a: Dict[str, Any], b: Dict[str, Any]) -> discord.Embed:
    embed = discord.Embed(
        title=f"{a['name']}  vs  {b['name']}",
        color=_COLOR,
    )

    def row(label, va, vb):
        embed.add_field(name=f"{label} — {a['name']}", value=str(va) if va else "—", inline=True)
        embed.add_field(name=f"{label} — {b['name']}", value=str(vb) if vb else "—", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)  # spacer

    row("Brand",      a.get("brand"),       b.get("brand"))
    row("Generation", a.get("generation"),  b.get("generation"))
    row("Released",   _release_str(a),      _release_str(b))
    row("Units Sold", _units_str(a),        _units_str(b))
    row("CPU",        a.get("cpu", "—"),    b.get("cpu", "—"))

    # Winner badge
    ua = a.get("units_sold_millions") or 0
    ub = b.get("units_sold_millions") or 0
    if ua and ub:
        winner = a["name"] if ua > ub else b["name"]
        embed.add_field(
            name="Best Seller",
            value=f"{winner}  ({max(ua,ub)}M vs {min(ua,ub)}M)",
            inline=False,
        )

    # Thumbnails — show first console's avatar
    avatar_a, _ = _thumbnail(a)
    if avatar_a:
        embed.set_thumbnail(url=avatar_a)

    embed.set_footer(text="Bottany Console Registry  ·  /console compare")
    return embed


def _build_timeline_embed(
    consoles: List[Dict[str, Any]],
    brand_filter: Optional[str],
) -> discord.Embed:
    title = "Console Timeline"
    if brand_filter:
        title += f" — {brand_filter}"

    embed = discord.Embed(title=title, color=_COLOR)

    # Group by generation
    by_gen: Dict[int, List[Dict]] = {}
    for c in consoles:
        g = c.get("generation", 0)
        by_gen.setdefault(g, []).append(c)

    for gen in sorted(by_gen.keys()):
        label = _GEN_LABELS.get(gen, f"Gen {gen}")
        lines = []
        for c in sorted(by_gen[gen], key=lambda x: (x.get("brand",""), x.get("name",""))):
            units = c.get("units_sold_millions")
            u_str = f" — {units}M" if units else ""
            handheld = " [Handheld]" if c.get("handheld") else ""
            hybrid   = " [Hybrid]"   if c.get("hybrid")   else ""
            lines.append(f"**{c['name']}**{handheld}{hybrid}{u_str}")
        embed.add_field(
            name=label,
            value="\n".join(lines)[:1024],
            inline=False,
        )

    # Thumbnail from the oldest console
    if consoles:
        oldest = sorted(consoles, key=lambda c: c.get("generation", 99))[0]
        avatar, _ = _thumbnail(oldest)
        if avatar:
            embed.set_thumbnail(url=avatar)

    total = len(consoles)
    embed.set_footer(text=f"{total} console(s) shown  ·  Bottany Console Registry")
    return embed


# ── Command group ─────────────────────────────────────────────────────────────

class ConsoleGroup(app_commands.Group):
    def __init__(self, data_dir: str):
        super().__init__(name="console", description="Video game console database")
        self._data_dir = data_dir

    # ── Autocomplete ──────────────────────────────────────────────────────────

    async def _autocomplete_name(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        consoles = _load(self._data_dir)
        needle   = current.lower().strip()
        seen: set[str] = set()
        choices: List[app_commands.Choice[str]] = []
        for c in consoles:
            name = c.get("name", "")
            if needle in name.lower() and name not in seen:
                seen.add(name)
                choices.append(app_commands.Choice(name=name, value=c["id"]))
            if len(choices) == 25:
                break
        return choices

    # /console info ────────────────────────────────────────────────────────────

    @app_commands.command(name="info", description="Full details for a specific console")
    @app_commands.describe(name="Console name (type to search)")
    @app_commands.autocomplete(name=_autocomplete_name)
    async def info(self, interaction: discord.Interaction, name: str) -> None:
        await interaction.response.defer()

        consoles = _load(self._data_dir)
        if not consoles:
            await interaction.followup.send("Console registry could not be loaded.", ephemeral=True)
            return

        # name param is actually the console id (from autocomplete value)
        match = next((c for c in consoles if c.get("id") == name), None)
        # Fallback: partial name match
        if not match:
            needle = name.lower()
            match  = next((c for c in consoles if needle in c.get("name","").lower()), None)

        if not match:
            await interaction.followup.send(
                f"No console found matching **\"{name}\"**.", ephemeral=True
            )
            return

        await interaction.followup.send(embed=_build_info_embed(match))

    # /console compare ─────────────────────────────────────────────────────────

    @app_commands.command(name="compare", description="Compare two consoles side by side")
    @app_commands.describe(
        first="First console",
        second="Second console",
    )
    @app_commands.autocomplete(first=_autocomplete_name, second=_autocomplete_name)
    async def compare(
        self,
        interaction: discord.Interaction,
        first: str,
        second: str,
    ) -> None:
        await interaction.response.defer()

        consoles = _load(self._data_dir)
        if not consoles:
            await interaction.followup.send("Console registry could not be loaded.", ephemeral=True)
            return

        def find(query: str) -> Optional[Dict]:
            c = next((c for c in consoles if c.get("id") == query), None)
            if not c:
                needle = query.lower()
                c = next((c for c in consoles if needle in c.get("name","").lower()), None)
            return c

        a = find(first)
        b = find(second)

        if not a or not b:
            missing = first if not a else second
            await interaction.followup.send(
                f"Could not find console: **\"{missing}\"**.", ephemeral=True
            )
            return

        if a["id"] == b["id"]:
            await interaction.followup.send(
                "Please select two different consoles.", ephemeral=True
            )
            return

        await interaction.followup.send(embed=_build_compare_embed(a, b))

    # /console timeline ────────────────────────────────────────────────────────

    @app_commands.command(
        name="timeline",
        description="Show consoles by generation, optionally filtered by brand",
    )
    @app_commands.describe(brand="Filter by brand (Nintendo, Sony, Sega, Microsoft…)")
    @app_commands.choices(brand=[
        app_commands.Choice(name="Nintendo",  value="Nintendo"),
        app_commands.Choice(name="Sony",      value="Sony"),
        app_commands.Choice(name="Microsoft", value="Microsoft"),
        app_commands.Choice(name="Sega",      value="Sega"),
        app_commands.Choice(name="Atari",     value="Atari"),
        app_commands.Choice(name="Valve",     value="Valve"),
        app_commands.Choice(name="SNK",       value="SNK"),
        app_commands.Choice(name="All",       value="All"),
    ])
    async def timeline(
        self,
        interaction: discord.Interaction,
        brand: Optional[str] = None,
    ) -> None:
        await interaction.response.defer()

        consoles = _load(self._data_dir)
        if not consoles:
            await interaction.followup.send("Console registry could not be loaded.", ephemeral=True)
            return

        if brand and brand != "All":
            filtered = [c for c in consoles if c.get("brand","").lower() == brand.lower()]
        else:
            filtered = consoles
            brand    = None

        if not filtered:
            await interaction.followup.send(
                f"No consoles found for brand **\"{brand}\"**.", ephemeral=True
            )
            return

        await interaction.followup.send(
            embed=_build_timeline_embed(filtered, brand_filter=brand)
        )


# ── Registration ──────────────────────────────────────────────────────────────

async def register(bot: discord.Client, data_dir: str) -> None:
    """Register /console commands. Called by main.py loader."""
    if bot.tree.get_command("console"):
        return
    bot.tree.add_command(ConsoleGroup(data_dir))

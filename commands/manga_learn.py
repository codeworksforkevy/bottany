# manga_learn.py
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import discord
from discord import app_commands

log = logging.getLogger(__name__)

REGISTRY_FILENAME = "manga_drawing_sources_registry.json"
PRESETS_FILENAME  = "manga_learn_presets.json"
AWARDS_FILENAME   = "manga_awards_registry.json"
ORIGINS_FILENAME  = "manga_origins_registry.json"

# ─────────────────────────────────────────────────────────────────────────────
# Allowed values & aliases
# ─────────────────────────────────────────────────────────────────────────────

_TOPIC_ALIASES = {
    "bg": "backgrounds", "background": "backgrounds", "bgs": "backgrounds",
    "env": "environments", "environment": "environments",
    "persp": "perspective",
    "value": "values", "tonal": "values",
    "atmosphere": "atmospheric_perspective", "depth": "atmospheric_perspective",
    "atm": "atmospheric_perspective",
}

_TOOL_ALIASES = {
    "csp": "clip-studio", "clip": "clip-studio", "clipstudio": "clip-studio",
    "clip_studio": "clip-studio", "medibang": "medibang", "wacom": "wacom",
    "too": "too", "procreate": "procreate", "kodansha": "kodansha",
}

_ALLOWED_TOPICS = {
    "lineart", "paneling", "screentone", "lettering", "workflow", "tools",
    "anatomy", "composition", "perspective", "backgrounds", "environments",
    "lighting", "values", "atmospheric_perspective", "materials", "props",
    "architecture",
}
_ALLOWED_LEVELS = {"Beginner", "Intermediate", "Advanced"}
_ALLOWED_MODES  = {"Digital", "Traditional", "Hybrid"}

_SHOW_EMOJIS = {
    "shogakukan":       "📘",
    "kodansha":         "📗",
    "jmaf":             "🏛️",
    "jima":             "🌐",
    "kadokawa_contest": "🌏",
}
_MEDIUM_EMOJIS = {"manga": "📖", "anime": "🎬"}
_SCOPE_EMOJIS  = {"japan": "🇯🇵", "global": "🌍"}

# ─────────────────────────────────────────────────────────────────────────────
# Normalisation helpers
# ─────────────────────────────────────────────────────────────────────────────

def _utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _norm_topic(v: Optional[str]) -> Optional[str]:
    if not v: return None
    s = v.strip().lower().replace(" ", "_")
    s = _TOPIC_ALIASES.get(s, s)
    return s if s in _ALLOWED_TOPICS else None


def _norm_level(v: Optional[str]) -> Optional[str]:
    if not v: return None
    s = v.strip().title()
    return s if s in _ALLOWED_LEVELS else None


def _norm_mode(v: Optional[str]) -> Optional[str]:
    if not v: return None
    s = v.strip().title()
    return s if s in _ALLOWED_MODES else None


def _norm_tool(v: Optional[str]) -> Optional[str]:
    if not v: return None
    s = v.strip().lower().replace(" ", "-").replace("_", "-")
    return _TOOL_ALIASES.get(s, s)


def _preset_code(topic, level, mode, tool) -> str:
    return ";".join(f"{k}={v}" for k, v in
                    [("topic", topic), ("level", level), ("mode", mode), ("tool", tool)] if v)


def _parse_preset_code(code: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for chunk in (code or "").split(";"):
        if "=" in chunk:
            k, v = chunk.split("=", 1)
            k, v = k.strip().lower(), v.strip()
            if k and v:
                out[k] = v
    return out

# ─────────────────────────────────────────────────────────────────────────────
# JSON I/O
# ─────────────────────────────────────────────────────────────────────────────

def _load_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

# ─────────────────────────────────────────────────────────────────────────────
# Loaders
# ─────────────────────────────────────────────────────────────────────────────

def _load_registry(data_dir: str) -> List[Dict[str, Any]]:
    path = os.path.join(data_dir, REGISTRY_FILENAME)
    obj  = _load_json(path, {"sources": []})
    raw  = obj.get("sources") if isinstance(obj, dict) else []
    return [s for s in (raw or []) if isinstance(s, dict) and s.get("id") and s.get("url")]


def _load_presets(data_dir: str) -> Dict[str, Any]:
    path = os.path.join(data_dir, PRESETS_FILENAME)
    obj  = _load_json(path, {})
    if not isinstance(obj, dict):
        obj = {}
    obj.setdefault("version", 1)
    obj.setdefault("updated_utc", _utc_now())
    obj.setdefault("presets", [])
    if not isinstance(obj["presets"], list):
        obj["presets"] = []
    return obj


def _save_presets(data_dir: str, obj: Dict[str, Any]) -> None:
    obj["updated_utc"] = _utc_now()
    _save_json(os.path.join(data_dir, PRESETS_FILENAME), obj)


def _load_awards(data_dir: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Returns (award_shows, winners). Compatible with old awards-only schema."""
    path = os.path.join(data_dir, AWARDS_FILENAME)
    obj  = _load_json(path, {})
    if not isinstance(obj, dict):
        return [], []
    # New unified schema uses "award_shows"; old stub used "awards"
    shows   = obj.get("award_shows") or obj.get("awards") or []
    winners = obj.get("winners") or []
    shows   = [s for s in shows   if isinstance(s, dict) and s.get("id")]
    winners = [w for w in winners if isinstance(w, dict) and w.get("title")]
    return shows, winners


def _load_origins(data_dir: str) -> List[Dict[str, Any]]:
    path = os.path.join(data_dir, ORIGINS_FILENAME)
    obj  = _load_json(path, {"entries": []})
    raw  = obj.get("entries") if isinstance(obj, dict) else []
    return [e for e in (raw or []) if isinstance(e, dict) and e.get("id") and e.get("title")]

# ─────────────────────────────────────────────────────────────────────────────
# Scoring & selection
# ─────────────────────────────────────────────────────────────────────────────

def _score_source(src: Dict[str, Any], topic, level, mode, tool) -> float:
    score = 0.0
    st = (src.get("source_type") or "").lower()
    if st in {"official", "official_platform", "official_docs"}:
        score += 4.0
    elif st in {"trusted", "trusted_platform", "curated"}:
        score += 2.0

    topics = [str(t).lower() for t in (src.get("topics") or [])]
    levels = [str(t)         for t in (src.get("levels") or [])]
    modes  = [str(t)         for t in (src.get("modes")  or [])]
    tool_s = str(src.get("tool") or "").lower()

    if topic: score += 6.0 if topic in topics else -1.0
    if level: score += 3.0 if level in levels else -0.5
    if mode:  score += 2.0 if mode  in modes  else -0.5
    if tool:  score += 3.0 if tool == tool_s  else -0.25
    if src.get("summary"): score += 0.25
    return score


def _select_sources(sources, topic, level, mode, tool, limit=8) -> List[Dict[str, Any]]:
    scored = [(_score_source(s, topic, level, mode, tool), s) for s in sources]
    scored.sort(key=lambda x: x[0], reverse=True)

    picked: List[Dict[str, Any]] = []
    pcounts: Dict[str, int] = {}

    for _ in range(limit):
        best_adj, best, best_idx = -1e9, None, -1
        for idx, (base, s) in enumerate(scored):
            if s is None: continue
            p   = str(s.get("provider") or "unknown").lower()
            adj = base - 1.25 * pcounts.get(p, 0)
            if adj > best_adj:
                best_adj, best, best_idx = adj, s, idx
        if best is None: break
        picked.append(best)
        p = str(best.get("provider") or "unknown").lower()
        pcounts[p] = pcounts.get(p, 0) + 1
        scored[best_idx] = (-1e9, None)  # type: ignore
    return picked

# ─────────────────────────────────────────────────────────────────────────────
# Learning paths
# ─────────────────────────────────────────────────────────────────────────────

_PATHS: Dict[str, List[str]] = {
    "backgrounds": [
        "workflow", "composition", "perspective", "values",
        "atmospheric_perspective", "materials", "props",
        "architecture", "environments", "backgrounds", "lighting",
    ],
    "characters": [
        "anatomy", "composition", "perspective", "lineart",
        "values", "lighting", "screentone",
    ],
    "general": [
        "workflow", "composition", "perspective", "values",
        "backgrounds", "paneling", "anatomy", "lineart",
        "screentone", "lettering",
    ],
}


def _path_for(track: Optional[str]) -> Tuple[str, List[str]]:
    t = (track or "").strip().lower()
    if t in {"bg", "background", "bgs", "backgrounds"}:
        return "backgrounds", _PATHS["backgrounds"]
    if t in {"character", "characters", "chars", "char"}:
        return "characters", _PATHS["characters"]
    return "general", _PATHS["general"]

# ─────────────────────────────────────────────────────────────────────────────
# Discord choices (static — no 25-item limit problem here)
# ─────────────────────────────────────────────────────────────────────────────

_TOPIC_CHOICES = [
    app_commands.Choice(name="Anatomy",                 value="anatomy"),
    app_commands.Choice(name="Architecture",            value="architecture"),
    app_commands.Choice(name="Atmospheric Perspective", value="atmospheric_perspective"),
    app_commands.Choice(name="Backgrounds",             value="backgrounds"),
    app_commands.Choice(name="Composition",             value="composition"),
    app_commands.Choice(name="Environments",            value="environments"),
    app_commands.Choice(name="Lettering",               value="lettering"),
    app_commands.Choice(name="Lighting",                value="lighting"),
    app_commands.Choice(name="Lineart",                 value="lineart"),
    app_commands.Choice(name="Materials",               value="materials"),
    app_commands.Choice(name="Paneling",                value="paneling"),
    app_commands.Choice(name="Perspective",             value="perspective"),
    app_commands.Choice(name="Props",                   value="props"),
    app_commands.Choice(name="Screentone",              value="screentone"),
    app_commands.Choice(name="Tools",                   value="tools"),
    app_commands.Choice(name="Values",                  value="values"),
    app_commands.Choice(name="Workflow",                value="workflow"),
]

_LEVEL_CHOICES = [
    app_commands.Choice(name="Beginner",     value="Beginner"),
    app_commands.Choice(name="Intermediate", value="Intermediate"),
    app_commands.Choice(name="Advanced",     value="Advanced"),
]

_MODE_CHOICES = [
    app_commands.Choice(name="Digital",     value="Digital"),
    app_commands.Choice(name="Traditional", value="Traditional"),
    app_commands.Choice(name="Hybrid",      value="Hybrid"),
]

_TOOL_CHOICES = [
    app_commands.Choice(name="CLIP STUDIO PAINT", value="clip-studio"),
    app_commands.Choice(name="MediBang Paint",    value="medibang"),
    app_commands.Choice(name="Procreate",         value="procreate"),
    app_commands.Choice(name="TOO",               value="too"),
    app_commands.Choice(name="Wacom",             value="wacom"),
    app_commands.Choice(name="Kodansha Academy",  value="kodansha"),
]

_TRACK_CHOICES = [
    app_commands.Choice(name="General manga creation", value="general"),
    app_commands.Choice(name="Backgrounds & scenes",   value="backgrounds"),
    app_commands.Choice(name="Characters & anatomy",   value="characters"),
]

_AWARD_REGION_CHOICES = [
    app_commands.Choice(name="Japan",         value="japan"),
    app_commands.Choice(name="International", value="international"),
]

_AWARD_KIND_CHOICES = [
    app_commands.Choice(name="Industry",   value="industry"),
    app_commands.Choice(name="Festival",   value="festival"),
    app_commands.Choice(name="Government", value="government"),
]

_MEDIUM_CHOICES = [
    app_commands.Choice(name="Manga", value="manga"),
    app_commands.Choice(name="Anime", value="anime"),
]

_SCOPE_CHOICES = [
    app_commands.Choice(name="Japan",  value="japan"),
    app_commands.Choice(name="Global", value="global"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Command group
# ─────────────────────────────────────────────────────────────────────────────

class MangaGroup(app_commands.Group):
    def __init__(self, data_dir: str):
        super().__init__(name="manga", description="Manga learning resources, awards, and history")
        self._data_dir = data_dir

    # /manga learn ────────────────────────────────────────────────────────────

    @app_commands.command(name="learn", description="Find official learning resources for manga drawing")
    @app_commands.describe(
        topic="What to study", level="Your current skill level",
        mode="Drawing medium",  tool="Software or tool",
    )
    @app_commands.choices(topic=_TOPIC_CHOICES, level=_LEVEL_CHOICES,
                          mode=_MODE_CHOICES,   tool=_TOOL_CHOICES)
    async def learn(
        self, interaction: discord.Interaction,
        topic: Optional[str] = None, level: Optional[str] = None,
        mode:  Optional[str] = None, tool:  Optional[str] = None,
    ) -> None:
        await interaction.response.defer()

        topic_n = _norm_topic(topic)
        level_n = _norm_level(level)
        mode_n  = _norm_mode(mode)
        tool_n  = _norm_tool(tool)

        sources = _load_registry(self._data_dir)
        picks   = _select_sources(sources, topic_n, level_n, mode_n, tool_n, limit=8)

        filters = [f for f in [topic_n, level_n, mode_n, tool_n] if f]
        title   = "📚 Manga Learning Resources"
        if filters:
            title += f" — {chr(44).join(filters)}"

        embed = discord.Embed(title=title, color=0x5865F2)

        if not picks:
            embed.description = (
                "No sources matched your filters.\n"
                "Try removing a filter, or use `/manga filters` to see what is available."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        for s in picks:
            name    = s.get("title") or s.get("id", "Unknown")
            url     = s.get("url", "")
            summary = (s.get("summary") or "").strip()
            meta    = " · ".join(p for p in [s.get("provider",""), s.get("tool",""), s.get("source_type","")] if p)

            fval = ""
            if summary:
                fval += summary + "\n"
            fval += f"[↗ Visit]({url})"
            if meta:
                fval += f"\n*{meta}*"

            embed.add_field(name=f"**{name}**", value=fval[:1024], inline=False)

        scene_topics = {"backgrounds","environments","composition","perspective",
                        "lighting","values","atmospheric_perspective","materials","props","architecture"}
        if topic_n in scene_topics:
            embed.add_field(
                name="💡 Suggested study order",
                value="composition → perspective → values → atmospheric_perspective → backgrounds → lighting",
                inline=False,
            )

        preset_code = _preset_code(topic_n, level_n, mode_n, tool_n)
        if preset_code:
            embed.add_field(
                name="🔖 Save as preset",
                value=f"`/manga preset_save name:MyPreset code:{preset_code}`",
                inline=False,
            )

        embed.set_footer(text=f"{len(picks)} source(s) · Official and trusted links only")
        await interaction.followup.send(embed=embed)

    # /manga path ─────────────────────────────────────────────────────────────

    @app_commands.command(name="path", description="Step-by-step learning path with curated links")
    @app_commands.describe(
        track="Learning track", level="Skill level filter",
        mode="Drawing medium",  tool="Tool filter",
    )
    @app_commands.choices(track=_TRACK_CHOICES, level=_LEVEL_CHOICES,
                          mode=_MODE_CHOICES,   tool=_TOOL_CHOICES)
    async def path(
        self, interaction: discord.Interaction,
        track: Optional[str] = None, level: Optional[str] = None,
        mode:  Optional[str] = None, tool:  Optional[str] = None,
    ) -> None:
        await interaction.response.defer()

        track_label, steps = _path_for(track)
        level_n = _norm_level(level)
        mode_n  = _norm_mode(mode)
        tool_n  = _norm_tool(tool)
        sources = _load_registry(self._data_dir)

        embed = discord.Embed(
            title=f"🗺️ Manga Learning Path — {track_label.title()}",
            color=0x5865F2,
        )

        for i, step_topic in enumerate(steps, start=1):
            picks = _select_sources(sources, step_topic, level_n, mode_n, tool_n, limit=2)
            if picks:
                links = "\n".join(
                    f"[↗ {p.get('title') or p.get('id')}]({p.get('url')})"
                    for p in picks
                )
            else:
                links = f"*No source found — try `/manga learn topic:{step_topic}`*"
            embed.add_field(name=f"**{i}.** {step_topic}", value=links, inline=False)

        embed.set_footer(text="Official and trusted links only")
        await interaction.followup.send(embed=embed)

    # /manga filters ──────────────────────────────────────────────────────────

    @app_commands.command(name="filters", description="Show all available filters for /manga learn")
    async def filters(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(title="🎛️ Available Filters for /manga learn", color=0x5865F2)
        embed.add_field(
            name="Topics",
            value=", ".join(f"`{t}`" for t in sorted(_ALLOWED_TOPICS)),
            inline=False,
        )
        embed.add_field(
            name="Levels",
            value=" · ".join(f"`{l}`" for l in sorted(_ALLOWED_LEVELS)),
            inline=False,
        )
        embed.add_field(
            name="Modes",
            value=" · ".join(f"`{m}`" for m in sorted(_ALLOWED_MODES)),
            inline=False,
        )
        embed.add_field(
            name="Tools",
            value=", ".join(f"`{t}`" for t in sorted(set(_TOOL_ALIASES.values()))),
            inline=False,
        )
        embed.set_footer(text="Tip: aliases work — bg=backgrounds, csp=clip-studio")
        await interaction.followup.send(embed=embed, ephemeral=True)

    # /manga source ────────────────────────────────────────────────────────────

    @app_commands.command(name="source", description="Look up a single learning source by its ID")
    @app_commands.describe(id="Source ID (shown in /manga learn results)")
    async def source(self, interaction: discord.Interaction, id: str) -> None:
        await interaction.response.defer()

        sid  = (id or "").strip()
        srcs = _load_registry(self._data_dir)
        s    = next((x for x in srcs if str(x.get("id")) == sid), None)

        if not s:
            await interaction.followup.send(
                f"Source `{sid}` not found. Use `/manga learn` to browse sources.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(title=s.get("title") or sid, url=s.get("url"), color=0x5865F2)
        if s.get("summary"):
            embed.description = str(s["summary"])

        for k, label in [("provider","Provider"), ("tool","Tool"), ("source_type","Type")]:
            if s.get(k):
                embed.add_field(name=label, value=str(s[k]), inline=True)

        if s.get("topics"):
            embed.add_field(name="Topics", value=", ".join(s["topics"]), inline=False)
        if s.get("levels"):
            embed.add_field(name="Levels", value=" · ".join(s["levels"]), inline=True)
        if s.get("modes"):
            embed.add_field(name="Modes",  value=" · ".join(s["modes"]),  inline=True)

        await interaction.followup.send(embed=embed)

    # /manga awards ────────────────────────────────────────────────────────────

    @app_commands.command(name="awards", description="Browse prestigious manga awards and their winners")
    @app_commands.describe(
        region="Filter by region", kind="Filter by award type",
        winner="Search for a winning title",
    )
    @app_commands.choices(region=_AWARD_REGION_CHOICES, kind=_AWARD_KIND_CHOICES)
    async def awards(
        self, interaction: discord.Interaction,
        region: Optional[str] = None, kind:   Optional[str] = None,
        winner: Optional[str] = None,
    ) -> None:
        await interaction.response.defer()

        shows, all_winners = _load_awards(self._data_dir)
        show_index = {s["id"]: s for s in shows}

        filtered_shows = shows
        if region:
            filtered_shows = [s for s in filtered_shows if s.get("region","").lower() == region.lower()]
        if kind:
            filtered_shows = [s for s in filtered_shows if s.get("kind","").lower() == kind.lower()]

        valid_show_ids = {s["id"] for s in filtered_shows}
        filtered_winners = [w for w in all_winners if w.get("award_show_id") in valid_show_ids]

        if winner:
            needle = winner.lower().strip()
            filtered_winners = [w for w in filtered_winners if needle in w.get("title","").lower()]

            embed = discord.Embed(title=f"🏆 Manga Winners — \"{winner}\"", color=0xE74C3C)
            if not filtered_winners:
                embed.description = f"No winners found matching **\"{winner}\"**."
            else:
                for w in sorted(filtered_winners, key=lambda w: -w.get("year",0))[:20]:
                    emoji  = _SHOW_EMOJIS.get(w.get("award_show_id",""), "🏆")
                    source = w.get("official_source","")
                    author = w.get("author","")
                    cat    = w.get("category","")
                    fval   = f"{emoji} {w.get('award','—')}"
                    if author: fval += f"\n*by {author}*"
                    if cat:    fval += f" · *{cat}*"
                    if source: fval += f"\n[↗ Source]({source})"
                    embed.add_field(
                        name=f"**{w['title']}** ({w.get('year','—')})",
                        value=fval[:1024], inline=False,
                    )
            embed.set_footer(text="Official sources only")
            await interaction.followup.send(embed=embed)
            return

        # Default view: show award organisations + most recent winner per show
        title = "🏆 Manga Awards"
        fil   = [f"region:{region}" if region else None, f"kind:{kind}" if kind else None]
        fil   = [f for f in fil if f]
        if fil: title += f" — {', '.join(fil)}"

        embed = discord.Embed(title=title, color=0xE74C3C)
        if not filtered_shows:
            embed.description = "No award shows matched your filters."
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        for show in sorted(filtered_shows, key=lambda s: s.get("since",9999)):
            emoji  = _SHOW_EMOJIS.get(show["id"], "🏆")
            active = "" if show.get("active", True) else " *(ended)*"
            since  = show.get("since","")
            org    = show.get("organizer","")
            url    = show.get("url","")
            note   = (show.get("note") or "").strip()

            show_wins = sorted(
                [w for w in all_winners if w.get("award_show_id") == show["id"]],
                key=lambda w: -w.get("year",0),
            )

            meta = " · ".join(p for p in [f"since {since}" if since else None, org] if p)
            fval = f"*{meta}*{active}"
            if note: fval += f"\n{note}"
            if show_wins:
                w = show_wins[0]
                fval += f"\n**Latest:** {w['title']} ({w.get('year','—')})"
                if w.get("author"): fval += f" · *{w['author']}*"
            if url: fval += f"\n[↗ Official site]({url})"

            embed.add_field(name=f"{emoji} {show['name']}", value=fval[:1024], inline=False)

        embed.set_footer(text=f"{len(all_winners)} verified winners · Official sources only")
        await interaction.followup.send(embed=embed)

    # /manga origins ───────────────────────────────────────────────────────────

    @app_commands.command(name="origins", description="Key milestones in manga and anime history")
    @app_commands.describe(medium="Filter by medium", scope="Filter by scope")
    @app_commands.choices(medium=_MEDIUM_CHOICES, scope=_SCOPE_CHOICES)
    async def origins(
        self, interaction: discord.Interaction,
        medium: Optional[str] = None, scope: Optional[str] = None,
    ) -> None:
        await interaction.response.defer()

        entries = _load_origins(self._data_dir)
        if medium:
            entries = [e for e in entries if e.get("medium","").lower() == medium.lower()]
        if scope:
            entries = [e for e in entries if e.get("scope","").lower() == scope.lower()]

        # Sort by integer year field (new schema); fall back to 9999 for undated entries
        entries.sort(key=lambda e: (e.get("year") or 9999, (e.get("title") or "").lower()))

        filters = []
        if medium: filters.append((_MEDIUM_EMOJIS.get(medium.lower(),"") + " " + medium).strip())
        if scope:  filters.append((_SCOPE_EMOJIS.get(scope.lower(),"")  + " " + scope).strip())

        title = "📜 Manga & Anime History"
        if filters: title += f" — {', '.join(filters)}"

        embed = discord.Embed(title=title, color=0xE67E22)

        if not entries:
            embed.description = "No milestones matched your filters."
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        for e in entries[:20]:
            date    = e.get("date") or str(e.get("year","—"))
            med     = e.get("medium","")
            scp     = e.get("scope","")
            note    = (e.get("note") or "").strip()
            url     = e.get("url","")

            m_em = _MEDIUM_EMOJIS.get(med.lower(),"")
            s_em = _SCOPE_EMOJIS.get(scp.lower(),"")

            fval = f"{m_em} {med} · {s_em} {scp}".strip(" ·")
            if note: fval += f"\n{note}"
            if url:  fval += f"\n[↗ Source]({url})"

            embed.add_field(
                name=f"**{e['title']}** · *{date}*",
                value=fval[:1024], inline=False,
            )

        embed.set_footer(text="'First' claims vary by definition — widely cited milestones only")
        await interaction.followup.send(embed=embed)

    # /manga preset_save ──────────────────────────────────────────────────────

    @app_commands.command(name="preset_save", description="Save your current filter combination as a named preset")
    @app_commands.describe(name="Preset name", code="Code from /manga learn (e.g. topic=lineart;level=Beginner)")
    async def preset_save(self, interaction: discord.Interaction, name: str, code: str) -> None:
        name = (name or "").strip()
        if not name:
            await interaction.response.send_message("Preset name cannot be empty.", ephemeral=True)
            return

        parsed  = _parse_preset_code(code)
        topic_n = _norm_topic(parsed.get("topic"))
        level_n = _norm_level(parsed.get("level"))
        mode_n  = _norm_mode(parsed.get("mode"))
        tool_n  = _norm_tool(parsed.get("tool"))

        obj     = _load_presets(self._data_dir)
        uid     = interaction.user.id
        presets = [p for p in obj["presets"]
                   if not (p.get("owner_id") == uid and (p.get("name") or "").lower() == name.lower())]
        presets.append({
            "owner_id":    uid,
            "name":        name,
            "filters":     {"topic": topic_n, "level": level_n, "mode": mode_n, "tool": tool_n},
            "created_utc": _utc_now(),
        })
        obj["presets"] = presets
        _save_presets(self._data_dir, obj)
        await interaction.response.send_message(f"✅ Saved preset **{name}**.", ephemeral=True)

    # /manga preset_list ──────────────────────────────────────────────────────

    @app_commands.command(name="preset_list", description="List your saved filter presets")
    async def preset_list(self, interaction: discord.Interaction) -> None:
        obj  = _load_presets(self._data_dir)
        uid  = interaction.user.id
        mine = [p for p in obj["presets"] if p.get("owner_id") == uid]

        if not mine:
            await interaction.response.send_message(
                "No presets yet. Use `/manga learn`, then `/manga preset_save`.", ephemeral=True,
            )
            return

        embed = discord.Embed(title="🔖 Your Manga Learn Presets", color=0x5865F2)
        for p in sorted(mine, key=lambda x: (x.get("name") or "").lower()):
            f    = p.get("filters") or {}
            code = _preset_code(f.get("topic"), f.get("level"), f.get("mode"), f.get("tool"))
            embed.add_field(
                name=f"**{p['name']}**",
                value=f"`{code}`\nRun: `/manga preset_run name:{p['name']}`",
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # /manga preset_run ───────────────────────────────────────────────────────

    @app_commands.command(name="preset_run", description="Run a saved preset by name")
    @app_commands.describe(name="Preset name")
    async def preset_run(self, interaction: discord.Interaction, name: str) -> None:
        obj    = _load_presets(self._data_dir)
        uid    = interaction.user.id
        name_l = (name or "").strip().lower()
        target = next(
            (p for p in obj["presets"]
             if p.get("owner_id") == uid and (p.get("name") or "").strip().lower() == name_l),
            None,
        )
        if not target:
            await interaction.response.send_message(
                "Preset not found. Use `/manga preset_list`.", ephemeral=True,
            )
            return

        f = target.get("filters") or {}
        await self.learn(
            interaction, topic=f.get("topic"), level=f.get("level"),
            mode=f.get("mode"), tool=f.get("tool"),
        )

    # /manga preset_delete ─────────────────────────────────────────────────────

    @app_commands.command(name="preset_delete", description="Delete a saved preset by name")
    @app_commands.describe(name="Preset name")
    async def preset_delete(self, interaction: discord.Interaction, name: str) -> None:
        obj    = _load_presets(self._data_dir)
        uid    = interaction.user.id
        name_l = (name or "").strip().lower()
        before = len(obj["presets"])
        obj["presets"] = [
            p for p in obj["presets"]
            if not (p.get("owner_id") == uid and (p.get("name") or "").strip().lower() == name_l)
        ]
        _save_presets(self._data_dir, obj)
        if len(obj["presets"]) == before:
            await interaction.response.send_message("Preset not found.", ephemeral=True)
        else:
            await interaction.response.send_message(f"🗑️ Deleted preset **{name}**.", ephemeral=True)


# ─────────────────────────────────────────────────────────────────────────────
# Registration
# ─────────────────────────────────────────────────────────────────────────────

async def register(bot: discord.Client, data_dir: str) -> None:
    """Register /manga command group. Called by main.py loader."""
    if bot.tree.get_command("manga"):
        return
    bot.tree.add_command(MangaGroup(data_dir=data_dir))

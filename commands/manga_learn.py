import os
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import discord
from discord import app_commands

REGISTRY_FILENAME = "manga_drawing_sources_registry.json"
PRESETS_FILENAME = "manga_learn_presets.json"
MANGA_AWARDS_FILENAME = "manga_awards_registry.json"
MANGA_ORIGINS_FILENAME = "manga_origins_registry.json"

# -------------------------
# Normalization / aliases
# -------------------------
_TOPIC_ALIASES = {
    "bg": "backgrounds",
    "background": "backgrounds",
    "bgs": "backgrounds",
    "env": "environments",
    "environment": "environments",
    "environ": "environments",
    "persp": "perspective",
    "value": "values",
    "tonal": "values",
    "atmosphere": "atmospheric_perspective",
    "depth": "atmospheric_perspective",
}

_TOOL_ALIASES = {
    "csp": "clip-studio",
    "clip": "clip-studio",
    "clipstudio": "clip-studio",
    "clip_studio": "clip-studio",
    "medibang": "medibang",
    "wacom": "wacom",
    "too": "too",
    "procreate": "procreate",
    "kodansha": "kodansha",
}

_ALLOWED_TOPICS = {
    "lineart",
    "paneling",
    "screentone",
    "lettering",
    "workflow",
    "tools",
    "anatomy",
    "composition",
    "perspective",
    "backgrounds",
    "environments",
    "lighting",
    "values",
    "atmospheric_perspective",
    "materials",
    "props",
    "architecture",
}

_ALLOWED_LEVELS = {"Beginner", "Intermediate", "Advanced"}
_ALLOWED_MODES = {"Digital", "Traditional", "Hybrid"}


def _utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _registry_path(data_dir: str) -> str:
    return os.path.join(data_dir, REGISTRY_FILENAME)


def _preset_path(data_dir: str) -> str:
    return os.path.join(data_dir, PRESETS_FILENAME)


def _awards_path(data_dir: str) -> str:
    return os.path.join(data_dir, MANGA_AWARDS_FILENAME)


def _origins_path(data_dir: str) -> str:
    return os.path.join(data_dir, MANGA_ORIGINS_FILENAME)


def _load_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _norm_topic(v: Optional[str]) -> Optional[str]:
    if not v:
        return None
    s = v.strip().lower().replace(" ", "_")
    s = _TOPIC_ALIASES.get(s, s)
    return s if s in _ALLOWED_TOPICS else None


def _norm_level(v: Optional[str]) -> Optional[str]:
    if not v:
        return None
    s = v.strip().title()
    return s if s in _ALLOWED_LEVELS else None


def _norm_mode(v: Optional[str]) -> Optional[str]:
    if not v:
        return None
    s = v.strip().title()
    return s if s in _ALLOWED_MODES else None


def _norm_tool(v: Optional[str]) -> Optional[str]:
    if not v:
        return None
    s = v.strip().lower().replace(" ", "-").replace("_", "-")
    s = _TOOL_ALIASES.get(s, s)
    return s


def _preset_code(topic: Optional[str], level: Optional[str], mode: Optional[str], tool: Optional[str]) -> str:
    parts = []
    if topic:
        parts.append(f"topic={topic}")
    if level:
        parts.append(f"level={level}")
    if mode:
        parts.append(f"mode={mode}")
    if tool:
        parts.append(f"tool={tool}")
    return ";".join(parts)


def _parse_preset_code(code: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not code:
        return out
    for chunk in code.split(";"):
        if "=" not in chunk:
            continue
        k, v = chunk.split("=", 1)
        k = (k or "").strip().lower()
        v = (v or "").strip()
        if k and v:
            out[k] = v
    return out


def _load_registry(data_dir: str) -> List[Dict[str, Any]]:
    obj = _load_json(_registry_path(data_dir), {"version": 1, "sources": []})
    sources = obj.get("sources") if isinstance(obj, dict) else []
    if not isinstance(sources, list):
        return []
    out = []
    for s in sources:
        if isinstance(s, dict) and s.get("id") and s.get("url"):
            out.append(s)
    return out


def _load_presets(data_dir: str) -> Dict[str, Any]:
    obj = _load_json(_preset_path(data_dir), {"version": 1, "updated_utc": _utc_now(), "presets": []})
    if not isinstance(obj, dict):
        obj = {"version": 1, "updated_utc": _utc_now(), "presets": []}
    obj.setdefault("version", 1)
    obj.setdefault("updated_utc", _utc_now())
    obj.setdefault("presets", [])
    if not isinstance(obj["presets"], list):
        obj["presets"] = []
    return obj


def _save_presets(data_dir: str, obj: Dict[str, Any]) -> None:
    obj["updated_utc"] = _utc_now()
    _save_json(_preset_path(data_dir), obj)


def _load_awards(data_dir: str) -> List[Dict[str, Any]]:
    obj = _load_json(_awards_path(data_dir), {"version": 1, "awards": []})
    awards = obj.get("awards") if isinstance(obj, dict) else []
    if not isinstance(awards, list):
        return []
    out: List[Dict[str, Any]] = []
    for a in awards:
        if isinstance(a, dict) and a.get("id") and a.get("name") and a.get("url"):
            out.append(a)
    return out


def _load_origins(data_dir: str) -> List[Dict[str, Any]]:
    obj = _load_json(_origins_path(data_dir), {"version": 1, "entries": []})
    entries = obj.get("entries") if isinstance(obj, dict) else []
    if not isinstance(entries, list):
        return []
    out: List[Dict[str, Any]] = []
    for e in entries:
        if isinstance(e, dict) and e.get("id") and e.get("title") and e.get("url"):
            out.append(e)
    return out


def _score_source(src: Dict[str, Any], topic: Optional[str], level: Optional[str], mode: Optional[str], tool: Optional[str]) -> float:
    """Compute a relevance score for a source given optional filters."""
    score = 0.0

    # source_type preference
    st = (src.get("source_type") or "").lower()
    if st in {"official", "official_platform", "official_docs"}:
        score += 4.0
    elif st in {"trusted", "trusted_platform", "curated"}:
        score += 2.0

    # Exact / partial matches
    topics = [str(t).lower() for t in (src.get("topics") or []) if isinstance(t, str)]
    levels = [str(t) for t in (src.get("levels") or []) if isinstance(t, str)]
    modes = [str(t) for t in (src.get("modes") or []) if isinstance(t, str)]
    src_tool = str(src.get("tool") or "").lower()

    if topic:
        if topic in topics:
            score += 6.0
        else:
            score -= 1.0
    if level:
        if level in levels:
            score += 3.0
        else:
            score -= 0.5
    if mode:
        if mode in modes:
            score += 2.0
        else:
            score -= 0.5
    if tool:
        if tool == src_tool:
            score += 3.0
        else:
            score -= 0.25

    # Small boost for concise summaries
    if src.get("summary"):
        score += 0.25

    return score


def _select_sources(
    sources: List[Dict[str, Any]],
    topic: Optional[str],
    level: Optional[str],
    mode: Optional[str],
    tool: Optional[str],
    limit: int = 8,
) -> List[Dict[str, Any]]:
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for s in sources:
        scored.append((_score_source(s, topic, level, mode, tool), s))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Greedy diversity selection: penalize repeating the same provider.
    picked: List[Dict[str, Any]] = []
    provider_counts: Dict[str, int] = {}

    for _ in range(limit):
        best = None
        best_score = -10**9
        best_idx = -1
        for idx, (base_score, s) in enumerate(scored):
            if s is None:
                continue
            provider = str(s.get("provider") or "unknown").lower()
            penalty = 1.25 * provider_counts.get(provider, 0)
            adj = base_score - penalty
            if adj > best_score:
                best_score = adj
                best = s
                best_idx = idx
        if best is None:
            break
        picked.append(best)
        provider = str(best.get("provider") or "unknown").lower()
        provider_counts[provider] = provider_counts.get(provider, 0) + 1
        scored[best_idx] = (-10**9, None)  # type: ignore

    return picked


def _mini_paths() -> Tuple[List[str], List[str]]:
    beginner = [
        "composition",
        "perspective",
        "values",
        "backgrounds",
        "lighting",
    ]
    intermediate = [
        "perspective",
        "atmospheric_perspective",
        "materials",
        "props",
        "architecture",
        "environments",
        "lighting",
    ]
    return beginner, intermediate


def _path_for(track: Optional[str]) -> List[str]:
    if track and track.strip().lower() == "backgrounds":
        # default to the full intermediate-ish backgrounds track
        return [
            "workflow",
            "composition",
            "perspective",
            "values",
            "atmospheric_perspective",
            "materials",
            "props",
            "architecture",
            "environments",
            "backgrounds",
            "lighting",
        ]

    # General manga creation path
    return [
        "workflow",
        "composition",
        "perspective",
        "values",
        "backgrounds",
        "paneling",
        "anatomy",
        "lineart",
        "screentone",
        "lettering",
    ]


class MangaGroup(app_commands.Group):
    def __init__(self, data_dir: str):
        super().__init__(name="manga", description="Manga learning resources (official/trusted) and study paths")
        self._data_dir = data_dir

    @app_commands.command(name="filters", description="Show available filters for /manga learn")
    async def filters(self, interaction: discord.Interaction):
        topic_list = ", ".join(sorted(_ALLOWED_TOPICS))
        level_list = ", ".join(sorted(_ALLOWED_LEVELS))
        mode_list = ", ".join(sorted(_ALLOWED_MODES))
        tool_list = ", ".join(sorted(set(_TOOL_ALIASES.values())))
        embed = discord.Embed(title="/manga filters", color=0x2F3136)
        embed.add_field(name="Topics", value=topic_list[:1024], inline=False)
        embed.add_field(name="Levels", value=level_list, inline=False)
        embed.add_field(name="Modes", value=mode_list, inline=False)
        embed.add_field(name="Tools", value=tool_list[:1024], inline=False)
        embed.set_footer(text="Tip: aliases work (e.g., topic:bg, tool:csp)")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="topics", description="Alias for /manga filters")
    async def topics(self, interaction: discord.Interaction):
        await self.filters(interaction)

    @app_commands.command(name="learn", description="List official/trusted resources to learn manga drawing")
    @app_commands.describe(topic="Topic (e.g., lineart, backgrounds, perspective)", level="Beginner/Intermediate/Advanced", mode="Digital/Traditional/Hybrid", tool="clip-studio/medibang/wacom/etc")
    async def learn(
        self,
        interaction: discord.Interaction,
        topic: Optional[str] = None,
        level: Optional[str] = None,
        mode: Optional[str] = None,
        tool: Optional[str] = None,
    ):
        topic_n = _norm_topic(topic)
        level_n = _norm_level(level)
        mode_n = _norm_mode(mode)
        tool_n = _norm_tool(tool)

        sources = _load_registry(self._data_dir)
        picks = _select_sources(sources, topic_n, level_n, mode_n, tool_n, limit=8)

        title_parts = ["/manga learn"]
        fparts = []
        if topic_n:
            fparts.append(f"topic:{topic_n}")
        if level_n:
            fparts.append(f"level:{level_n}")
        if mode_n:
            fparts.append(f"mode:{mode_n}")
        if tool_n:
            fparts.append(f"tool:{tool_n}")
        if fparts:
            title_parts.append("(" + ", ".join(fparts) + ")")

        embed = discord.Embed(title=" ".join(title_parts), color=0x2F3136)
        if not picks:
            embed.description = "No sources matched your filters. Try removing one filter or use /manga filters."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        lines = []
        for s in picks:
            sid = s.get("id")
            name = s.get("title") or s.get("name") or sid
            url = s.get("url")
            summary = (s.get("summary") or "").strip()
            provider = s.get("provider")
            meta = []
            if provider:
                meta.append(str(provider))
            if s.get("tool"):
                meta.append(str(s.get("tool")))
            if s.get("source_type"):
                meta.append(str(s.get("source_type")))
            meta_txt = " — ".join(meta)
            if summary:
                lines.append(f"• **{name}**\n  {summary}\n  {url}\n  _{meta_txt}_")
            else:
                lines.append(f"• **{name}**\n  {url}\n  _{meta_txt}_")

        embed.description = "\n\n".join(lines)[:4096]

        # Mini-path for backgrounds / scene work
        scene_topics = {"backgrounds", "environments", "composition", "perspective", "lighting", "values", "atmospheric_perspective", "materials", "props", "architecture"}
        if topic_n in scene_topics or (topic_n is None and (tool_n in {"clip-studio", "medibang", "procreate"})):
            beg, inter = _mini_paths()
            embed.add_field(
                name="Scene & Background Mini-Path — Beginner",
                value=" → ".join(beg),
                inline=False,
            )
            embed.add_field(
                name="Scene & Background Mini-Path — Intermediate",
                value=" → ".join(inter),
                inline=False,
            )

        preset_code = _preset_code(topic_n, level_n, mode_n, tool_n)
        if preset_code:
            embed.add_field(
                name="Saveable preset",
                value=(
                    f"`{preset_code}`\n"
                    f"Save: `/manga preset_save name:MyPreset code:{preset_code}`\n"
                    f"Run: `/manga preset_run name:MyPreset`"
                )[:1024],
                inline=False,
            )

        embed.set_footer(text="Short summaries + official links only (no scraped content).")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="path", description="Show a step-by-step learning path with curated links")
    @app_commands.describe(track="Optional track: backgrounds", level="Beginner/Intermediate/Advanced", mode="Digital/Traditional/Hybrid", tool="clip-studio/medibang/wacom/etc")
    async def path(
        self,
        interaction: discord.Interaction,
        track: Optional[str] = None,
        level: Optional[str] = None,
        mode: Optional[str] = None,
        tool: Optional[str] = None,
    ):
        track_n = (track or "").strip().lower() or None
        if track_n in {"bg", "background", "bgs"}:
            track_n = "backgrounds"

        level_n = _norm_level(level)
        mode_n = _norm_mode(mode)
        tool_n = _norm_tool(tool)

        steps = _path_for(track_n)
        sources = _load_registry(self._data_dir)

        title = "/manga path" + (f" track:{track_n}" if track_n else "")
        embed = discord.Embed(title=title, color=0x2F3136)

        blocks = []
        for i, step_topic in enumerate(steps, start=1):
            picks = _select_sources(sources, step_topic, level_n, mode_n, tool_n, limit=2)
            if picks:
                links = "\n".join(f"- {p.get('title') or p.get('id')}: {p.get('url')}" for p in picks)
            else:
                links = "- (no matching source; try /manga learn topic:{step_topic})"
            blocks.append(f"**{i}. {step_topic}**\n{links}")

        embed.description = "\n\n".join(blocks)[:4096]
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="source", description="Show a single source by id")
    @app_commands.describe(id="Source id")
    async def source(self, interaction: discord.Interaction, id: str):
        sid = (id or "").strip()
        if not sid:
            await interaction.response.send_message("Please provide a source id.", ephemeral=True)
            return
        sources = _load_registry(self._data_dir)
        s = next((x for x in sources if str(x.get("id")) == sid), None)
        if not s:
            await interaction.response.send_message("Source not found. Use /manga learn or /manga filters.", ephemeral=True)
            return

        title = s.get("title") or sid
        embed = discord.Embed(title=title, color=0x2F3136)
        if s.get("summary"):
            embed.description = str(s.get("summary"))
        embed.add_field(name="URL", value=str(s.get("url")), inline=False)
        meta = []
        for k in ("provider", "tool", "source_type"):
            if s.get(k):
                meta.append(f"{k}: {s.get(k)}")
        if meta:
            embed.add_field(name="Meta", value="\n".join(meta)[:1024], inline=False)
        if s.get("topics"):
            embed.add_field(name="Topics", value=", ".join(s.get("topics"))[:1024], inline=False)
        await interaction.response.send_message(embed=embed)

    # -------------------------

    # -------------------------
    # Awards and origins
    # -------------------------
    @app_commands.command(name="awards", description="List prestigious manga awards (official/trusted links)")
    @app_commands.describe(region="Optional region filter (japan/international)", kind="Optional kind filter (industry/government/festival)")
    async def awards(
        self,
        interaction: discord.Interaction,
        region: Optional[str] = None,
        kind: Optional[str] = None,
    ):
        region_n = (region or "").strip().lower() or None
        kind_n = (kind or "").strip().lower() or None

        awards = _load_awards(self._data_dir)

        def ok(a: Dict[str, Any]) -> bool:
            if region_n and str(a.get("region") or "").lower() != region_n:
                return False
            if kind_n and str(a.get("kind") or "").lower() != kind_n:
                return False
            return True

        picks = [a for a in awards if ok(a)]
        picks.sort(key=lambda x: (int(x.get("since") or 9999), str(x.get("name") or "")))

        title = "/manga awards"
        f = []
        if region_n:
            f.append(f"region:{region_n}")
        if kind_n:
            f.append(f"kind:{kind_n}")
        if f:
            title += " (" + ", ".join(f) + ")"

        embed = discord.Embed(title=title, color=0x2F3136)
        if not picks:
            embed.description = "No awards matched your filters. Try removing region/kind."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        lines: List[str] = []
        for a in picks[:12]:
            name = a.get("name")
            url = a.get("url")
            since = a.get("since")
            organizer = a.get("organizer")
            note = (a.get("note") or "").strip()
            meta = []
            if since:
                meta.append(f"since {since}")
            if organizer:
                meta.append(str(organizer))
            if a.get("region"):
                meta.append(str(a.get("region")))
            if a.get("kind"):
                meta.append(str(a.get("kind")))
            meta_txt = " — ".join(meta)
            if note:
                lines.append(f"• **{name}**\n  {note}\n  {url}\n  _{meta_txt}_")
            else:
                lines.append(f"• **{name}**\n  {url}\n  _{meta_txt}_")

        embed.description = "\n\n".join(lines)[:4096]
        embed.set_footer(text="Official/trusted links only.")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="origins", description="Key milestones for early manga and early animation")
    @app_commands.describe(medium="Optional: manga or anime", scope="Optional: japan or global")
    async def origins(
        self,
        interaction: discord.Interaction,
        medium: Optional[str] = None,
        scope: Optional[str] = None,
    ):
        medium_n = (medium or "").strip().lower() or None
        scope_n = (scope or "").strip().lower() or None
        if medium_n in {"animation", "anime"}:
            medium_n = "anime"

        entries = _load_origins(self._data_dir)

        def ok(e: Dict[str, Any]) -> bool:
            if medium_n and str(e.get("medium") or "").lower() != medium_n:
                return False
            if scope_n and str(e.get("scope") or "").lower() != scope_n:
                return False
            return True

        picks = [e for e in entries if ok(e)]
        # Sort by year-ish key (string tolerant)
        def year_key(v: Any) -> int:
            s = str(v or "")
            for token in s.replace("?", "").replace("c.", "").split():
                if token.isdigit() and len(token) == 4:
                    return int(token)
            return 9999

        picks.sort(key=lambda x: (year_key(x.get("date")), str(x.get("title") or "")))

        title = "/manga origins"
        f = []
        if medium_n:
            f.append(f"medium:{medium_n}")
        if scope_n:
            f.append(f"scope:{scope_n}")
        if f:
            title += " (" + ", ".join(f) + ")"

        embed = discord.Embed(title=title, color=0x2F3136)
        if not picks:
            embed.description = "No entries matched your filters. Try medium:manga|anime or scope:japan|global."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        blocks: List[str] = []
        for e in picks[:15]:
            dt = e.get("date")
            ttl = e.get("title")
            url = e.get("url")
            note = (e.get("note") or "").strip()
            blocks.append(f"• **{dt} — {ttl}**\n  {note}\n  {url}")

        embed.description = "\n\n".join(blocks)[:4096]
        embed.set_footer(text="Note: 'first' depends on definitions; this is a curated milestones list.")
        await interaction.response.send_message(embed=embed)

    # -------------------------
    # Awards and origins
    # -------------------------
    @app_commands.command(name="awards", description="List prestigious manga awards (official/trusted links)")
    @app_commands.describe(region="Optional region filter (japan/international)", kind="Optional kind filter (industry/government/festival)")
    async def awards(self, interaction: discord.Interaction, region: Optional[str] = None, kind: Optional[str] = None):
        region_n = (region or "").strip().lower() or None
        kind_n = (kind or "").strip().lower() or None

        awards = _load_awards(self._data_dir)
        if region_n:
            awards = [a for a in awards if (str(a.get("region") or "").lower() == region_n)]
        if kind_n:
            awards = [a for a in awards if (str(a.get("kind") or "").lower() == kind_n)]

        embed = discord.Embed(title="/manga awards", color=0x2F3136)
        if not awards:
            embed.description = "No awards matched your filters. Try removing a filter."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        lines: List[str] = []
        for a in awards[:12]:
            name = a.get("name")
            since = a.get("since")
            org = a.get("organizer")
            url = a.get("url")
            note = (a.get("note") or "").strip()
            meta_bits = [b for b in [f"since {since}" if since else None, org, a.get("region"), a.get("kind")] if b]
            meta = " — ".join(str(x) for x in meta_bits)
            block = f"• **{name}**\n  {meta}\n  {url}"
            if note:
                block += f"\n  _{note}_"
            lines.append(block)

        embed.description = "\n\n".join(lines)[:4096]
        embed.set_footer(text="Official/trusted reference links only.")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="origins", description="Key milestones for early manga/anime (with references)")
    @app_commands.describe(medium="Optional filter: manga or anime")
    async def origins(self, interaction: discord.Interaction, medium: Optional[str] = None):
        medium_n = (medium or "").strip().lower() or None
        if medium_n in {"animation", "anime"}:
            medium_n = "anime"
        if medium_n not in {None, "manga", "anime"}:
            await interaction.response.send_message("medium must be 'manga' or 'anime'.", ephemeral=True)
            return

        entries = _load_origins(self._data_dir)
        if medium_n:
            entries = [e for e in entries if (str(e.get("medium") or "").lower() == medium_n)]

        # Sort by year (best-effort)
        def _year_key(e: Dict[str, Any]) -> int:
            y = e.get("year")
            try:
                return int(y)
            except Exception:
                return 9999

        entries.sort(key=_year_key)

        title = "/manga origins" + (f" ({medium_n})" if medium_n else "")
        embed = discord.Embed(title=title, color=0x2F3136)
        if not entries:
            embed.description = "No entries found."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        lines: List[str] = []
        for e in entries[:12]:
            y = e.get("year")
            t = e.get("title")
            url = e.get("url")
            note = (e.get("note") or "").strip()
            tag = e.get("label") or e.get("medium")
            block = f"• **{y} — {t}**"
            if tag:
                block += f" _(tag: {tag})_"
            if note:
                block += f"\n  {note}"
            block += f"\n  {url}"
            lines.append(block)

        embed.description = "\n\n".join(lines)[:4096]
        embed.set_footer(text="Early-history 'first' claims can vary by definition; this lists widely-cited milestones.")
        await interaction.response.send_message(embed=embed)
    # Presets
    # -------------------------
    @app_commands.command(name="preset_save", description="Save a preset (filters) for quick reuse")
    @app_commands.describe(name="Preset name", code="Preset code shown by /manga learn")
    async def preset_save(self, interaction: discord.Interaction, name: str, code: str):
        name = (name or "").strip()
        if not name:
            await interaction.response.send_message("Preset name cannot be empty.", ephemeral=True)
            return

        parsed = _parse_preset_code(code)
        topic_n = _norm_topic(parsed.get("topic"))
        level_n = _norm_level(parsed.get("level"))
        mode_n = _norm_mode(parsed.get("mode"))
        tool_n = _norm_tool(parsed.get("tool"))

        obj = _load_presets(self._data_dir)
        presets = obj.get("presets", [])

        uid = interaction.user.id
        presets = [p for p in presets if not (p.get("owner_id") == uid and (p.get("name") or "").lower() == name.lower())]

        presets.append({
            "owner_id": uid,
            "name": name,
            "filters": {"topic": topic_n, "level": level_n, "mode": mode_n, "tool": tool_n},
            "created_utc": _utc_now(),
        })
        obj["presets"] = presets
        _save_presets(self._data_dir, obj)
        await interaction.response.send_message(f"Saved preset **{name}**.", ephemeral=True)

    @app_commands.command(name="preset_list", description="List your saved presets")
    async def preset_list(self, interaction: discord.Interaction):
        obj = _load_presets(self._data_dir)
        uid = interaction.user.id
        mine = [p for p in obj.get("presets", []) if p.get("owner_id") == uid]
        if not mine:
            await interaction.response.send_message("You have no presets yet. Use /manga learn then /manga preset_save.", ephemeral=True)
            return

        lines = []
        for p in sorted(mine, key=lambda x: (x.get("name") or "").lower()):
            f = p.get("filters") or {}
            lines.append(f"• **{p.get('name')}** — `{_preset_code(f.get('topic'), f.get('level'), f.get('mode'), f.get('tool'))}`")

        embed = discord.Embed(title="/manga preset_list", description="\n".join(lines)[:4096], color=0x2F3136)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="preset_run", description="Run a saved preset by name")
    @app_commands.describe(name="Preset name")
    async def preset_run(self, interaction: discord.Interaction, name: str):
        obj = _load_presets(self._data_dir)
        uid = interaction.user.id
        name_l = (name or "").strip().lower()
        target = None
        for p in obj.get("presets", []):
            if p.get("owner_id") == uid and (p.get("name") or "").strip().lower() == name_l:
                target = p
                break
        if not target:
            await interaction.response.send_message("Preset not found. Use /manga preset_list.", ephemeral=True)
            return

        f = target.get("filters") or {}
        await self.learn(
            interaction,
            topic=f.get("topic"),
            level=f.get("level"),
            mode=f.get("mode"),
            tool=f.get("tool"),
        )

    @app_commands.command(name="preset_delete", description="Delete a saved preset by name")
    @app_commands.describe(name="Preset name")
    async def preset_delete(self, interaction: discord.Interaction, name: str):
        obj = _load_presets(self._data_dir)
        uid = interaction.user.id
        name_l = (name or "").strip().lower()
        before = len(obj.get("presets", []))
        obj["presets"] = [p for p in obj.get("presets", []) if not (p.get("owner_id") == uid and (p.get("name") or "").strip().lower() == name_l)]
        after = len(obj.get("presets", []))
        _save_presets(self._data_dir, obj)
        if after == before:
            await interaction.response.send_message("Preset not found.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Deleted preset **{name}**.", ephemeral=True)


async def register_manga(bot: discord.Client, data_dir: str) -> None:
    """Register the /manga command group."""
    group = MangaGroup(data_dir=data_dir)

    # Prevent double-register
    for cmd in bot.tree.get_commands():
        if isinstance(cmd, app_commands.Group) and cmd.name == group.name:
            raise RuntimeError("Already registered")

    bot.tree.add_command(group)

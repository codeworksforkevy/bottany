"""
scripts/json_to_sql.py
======================
JSON → PostgreSQL INSERT generator for Bottany bot.

Reads anime_awards data from the project's data/ directory and writes
a ready-to-run SQL file into database/.

Usage (from project root):
    python scripts/json_to_sql.py
    python scripts/json_to_sql.py --source flat
    python scripts/json_to_sql.py --out database/seed.sql
    python scripts/json_to_sql.py --dry-run

Arguments:
    --source nested   Read data/all_raw.json          (full nested schema, default)
    --source flat     Read data/anime_awards_registry.json  (flat schema)
    --out PATH        Write SQL to PATH (default: database/seed.sql)
    --dry-run         Print to stdout instead of writing a file
    --no-transaction  Omit BEGIN/COMMIT wrapper
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Project paths ──────────────────────────────────────────────────────────────
# Always resolve relative to this script's location so it works regardless of
# which directory you run it from.

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR     = PROJECT_ROOT / "data"
DB_DIR       = PROJECT_ROOT / "database"

NESTED_FILE  = DATA_DIR / "all_raw.json"
FLAT_FILE    = DATA_DIR / "anime_awards_registry.json"
DEFAULT_OUT  = DB_DIR / "seed.sql"


# ── PostgreSQL escaping ────────────────────────────────────────────────────────

def esc(v: Any) -> str:
    """
    Safely escape a scalar value for PostgreSQL.
    - None        → NULL
    - int / float → bare number (no quotes)
    - str         → 'quoted', or $str$dollar-quoted$str$ when apostrophe present
    """
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if "'" in s:
        # Dollar-quoting avoids ALL apostrophe issues without needing to
        # double every quote character.  Tag is unique enough to not collide.
        return f"$str${s}$str$"
    return f"'{s}'"


def pg_array(lst: list) -> str:
    """Convert a Python list to a PostgreSQL TEXT[] literal."""
    if not lst:
        return "ARRAY[]::TEXT[]"
    items = ", ".join(esc(x) for x in lst)
    return f"ARRAY[{items}]"


# ── Loaders ────────────────────────────────────────────────────────────────────

def load_nested(path: Path) -> list[dict]:
    """
    Load the rich nested schema (title.en / award.show_id / credits.director …)
    and normalise every entry to the flat dict that build_row() expects.
    """
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    # Top-level may be a bare list or {"winners": [...], ...}
    if isinstance(raw, dict):
        raw = raw.get("winners", [])

    rows = []
    for a in raw:
        t      = a.get("title",    {})
        award  = a.get("award",    {})
        creds  = a.get("credits",  {})
        tech   = a.get("technical",{})
        media  = a.get("media",    {})
        links  = a.get("links",    {})

        rows.append({
            "title_en":            t.get("en", ""),
            "title_jp":            t.get("jp", ""),
            "title_display":       t.get("display",
                                        f"{t.get('en','')} | {t.get('jp','')}"),
            "year":                a.get("year"),
            "era":                 a.get("era"),
            "award_show_id":       award.get("show_id", ""),
            "award_name":          award.get("name", ""),
            "category":            award.get("category"),
            "award_type":          award.get("award_type"),
            "jp_label":            award.get("jp_label"),
            "directors":           creds.get("director",    []),
            "studios":             creds.get("studio",      []),
            "productions":         creds.get("production",  []),
            "animation_technique": tech.get("animation_technique"),
            "format":              tech.get("format"),
            "thumbnail":           media.get("thumbnail"),
            "official_link":       links.get("official"),
            "imdb_link":           links.get("imdb"),
            "mal_link":            links.get("mal"),
            "sources":             a.get("sources", []),
            "confidence":          a.get("confidence", "medium"),
        })
    return rows


def load_flat(path: Path) -> list[dict]:
    """
    Load the flat schema (anime_awards_registry.json).
    Fields not present in the flat schema are set to None / empty list.
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    winners = data.get("winners", []) if isinstance(data, dict) else data

    rows = []
    for w in winners:
        title = w.get("title", "")
        rows.append({
            "title_en":            title,
            "title_jp":            "",
            "title_display":       title,
            "year":                w.get("year"),
            "era":                 w.get("era"),
            "award_show_id":       w.get("award_show_id", ""),
            "award_name":          w.get("award", ""),
            "category":            None,
            "award_type":          None,
            "jp_label":            None,
            "directors":           w.get("director",  []),
            "studios":             w.get("studio",    []),
            "productions":         [],
            "animation_technique": None,
            "format":              None,
            "thumbnail":           None,
            "official_link":       w.get("official_source"),
            "imdb_link":           None,
            "mal_link":            None,
            "sources":             [],
            "confidence":          w.get("confidence", "medium"),
        })
    return rows


# ── Validation ─────────────────────────────────────────────────────────────────

_VALID_AWARD_TYPES = {"feature", "grand_prize", "jury", "special", "screening", None}
_VALID_ERAS        = {"classic", "modern", None}
_VALID_CONFIDENCE  = {"high", "medium", "low", None}


def validate(rows: list[dict]) -> list[str]:
    """Return a list of warning strings for any rows with suspicious values."""
    warnings = []
    for i, r in enumerate(rows):
        label = r.get("title_en") or f"row[{i}]"
        if not r.get("title_en"):
            warnings.append(f"  [{label}] title_en is empty")
        if not r.get("year"):
            warnings.append(f"  [{label}] year is missing")
        if not r.get("award_show_id"):
            warnings.append(f"  [{label}] award_show_id is empty")
        if r.get("award_type") not in _VALID_AWARD_TYPES:
            warnings.append(f"  [{label}] unknown award_type: {r['award_type']!r}")
        if r.get("era") not in _VALID_ERAS:
            warnings.append(f"  [{label}] unknown era: {r['era']!r}")
        if r.get("confidence") not in _VALID_CONFIDENCE:
            warnings.append(f"  [{label}] unknown confidence: {r['confidence']!r}")
    return warnings


# ── SQL builder ────────────────────────────────────────────────────────────────

_COLUMNS = """\
  title_en, title_jp, title_display,
  year, era,
  award_show_id, award_name, category, award_type, jp_label,
  directors, studios, productions,
  animation_technique, format,
  thumbnail,
  official_link, imdb_link, mal_link,
  sources, confidence"""


def build_row(r: dict) -> str:
    return (
        "(\n"
        f"  {esc(r['title_en'])},{esc(r['title_jp'])},{esc(r['title_display'])},\n"
        f"  {esc(r['year'])},{esc(r['era'])},\n"
        f"  {esc(r['award_show_id'])},{esc(r['award_name'])},"
        f"{esc(r['category'])},{esc(r['award_type'])},{esc(r['jp_label'])},\n"
        f"  {pg_array(r['directors'])},{pg_array(r['studios'])},{pg_array(r['productions'])},\n"
        f"  {esc(r['animation_technique'])},{esc(r['format'])},\n"
        f"  {esc(r['thumbnail'])},\n"
        f"  {esc(r['official_link'])},{esc(r['imdb_link'])},{esc(r['mal_link'])},\n"
        f"  {pg_array(r['sources'])},{esc(r['confidence'])}\n"
        ")"
    )


def build_sql(rows: list[dict], source_file: str, transaction: bool) -> str:
    now     = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    sql_rows = [build_row(r) for r in rows]

    header = (
        "-- =============================================================================\n"
        "-- seed.sql\n"
        f"-- Generated by scripts/json_to_sql.py on {now}\n"
        f"-- Source: {source_file}\n"
        f"-- Entries: {len(rows)}\n"
        "-- Safe to re-run: ON CONFLICT DO NOTHING\n"
        "-- =============================================================================\n"
    )

    insert = (
        f"\n-- anime_awards ({len(rows)} entries)\n"
        f"INSERT INTO anime_awards (\n{_COLUMNS}\n) VALUES\n"
        + ",\n".join(sql_rows)
        + "\nON CONFLICT DO NOTHING;\n"
    )

    kitten_note = (
        "\n"
        "-- -----------------------------------------------------------------------------\n"
        "-- kitten_pets / kitten_adoptions / kitten_global_events\n"
        "-- No seed data — populated at runtime by bot commands.\n"
        "-- -----------------------------------------------------------------------------\n"
    )

    body = insert + kitten_note

    if transaction:
        return header + "\nBEGIN;\n" + body + "\nCOMMIT;\n"
    return header + body


# ── CLI ────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Convert anime_awards JSON → PostgreSQL seed.sql"
    )
    p.add_argument(
        "--source",
        choices=["nested", "flat"],
        default="nested",
        help="nested = data/all_raw.json (default), flat = data/anime_awards_registry.json",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output file path (default: {DEFAULT_OUT})",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print SQL to stdout instead of writing a file",
    )
    p.add_argument(
        "--no-transaction",
        action="store_true",
        help="Omit BEGIN/COMMIT wrapper",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # ── Load ──────────────────────────────────────────────────────────────────
    if args.source == "flat":
        path = FLAT_FILE
        if not path.exists():
            print(f"ERROR: {path} not found.", file=sys.stderr)
            sys.exit(1)
        rows = load_flat(path)
    else:
        path = NESTED_FILE
        if not path.exists():
            print(f"ERROR: {path} not found.", file=sys.stderr)
            print(f"Hint:  try --source flat to use {FLAT_FILE}", file=sys.stderr)
            sys.exit(1)
        rows = load_nested(path)

    if not rows:
        print(f"ERROR: No entries found in {path}", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(rows)} entries from {path.name}", file=sys.stderr)

    # ── Validate ──────────────────────────────────────────────────────────────
    warnings = validate(rows)
    if warnings:
        print(f"Warnings ({len(warnings)}):", file=sys.stderr)
        for w in warnings:
            print(w, file=sys.stderr)

    # ── Build SQL ─────────────────────────────────────────────────────────────
    sql = build_sql(
        rows,
        source_file=str(path.relative_to(PROJECT_ROOT)),
        transaction=not args.no_transaction,
    )

    # ── Output ────────────────────────────────────────────────────────────────
    if args.dry_run:
        print(sql)
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(sql, encoding="utf-8")
        print(f"Written → {args.out}  ({len(sql):,} bytes, {len(rows)} rows)",
              file=sys.stderr)


if __name__ == "__main__":
    main()

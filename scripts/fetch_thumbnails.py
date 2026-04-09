"""
scripts/fetch_thumbnails.py
===========================
Fetches poster image URLs from Jikan v4 (unofficial MAL API) and writes them
into data/anime_awards_registry.json as the `thumbnail` field.

Run once from project root:
    python scripts/fetch_thumbnails.py

Requirements:
    pip install requests

Jikan v4 is free, no API key needed. Rate limit: ~3 req/sec.
Script sleeps 1.0s between requests to stay well under the limit.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

try:
    import requests
except ImportError:
    raise SystemExit("Install requests first:  pip install requests")

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
REGISTRY     = PROJECT_ROOT / "data" / "anime_awards_registry.json"

JIKAN_BASE   = "https://api.jikan.moe/v4/anime"
SLEEP        = 1.0   # Jikan limitlerine takılmamak için 0.4'ten 1.0'a çıkarıldı

HEADERS = {
    "User-Agent": "Bottany-Bot/1.0 (https://github.com/codeworksforkevy/bottany)"
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def mal_id_from_url(url: str) -> str | None:
    """Extract MAL anime ID from a MAL URL like https://myanimelist.net/anime/199"""
    if not url:
        return None
    parts = url.rstrip("/").split("/")
    # Last numeric segment is the ID
    for part in reversed(parts):
        if part.isdigit():
            return part
    return None


def fetch_thumbnail(mal_id: str) -> str | None:
    """Call Jikan v4 and return the medium poster image URL, or None on failure."""
    url = f"{JIKAN_BASE}/{mal_id}"
    try:
        # İstek atarken HEADERS bilgisi eklendi
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            images = data.get("images", {})
            jpg = images.get("jpg", {})
            # Prefer large, fall back to image_url (medium)
            return jpg.get("large_image_url") or jpg.get("image_url")
        elif resp.status_code == 429:
            print(f"  Rate limited — sleeping 3s then retrying {mal_id}")
            time.sleep(3)
            return fetch_thumbnail(mal_id)   # one retry
        else:
            print(f"  HTTP {resp.status_code} for MAL ID {mal_id}")
            return None
    except requests.RequestException as e:
        print(f"  Request error for MAL ID {mal_id}: {e}")
        return None


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    if not REGISTRY.exists():
        raise SystemExit(f"Registry not found: {REGISTRY}")

    with open(REGISTRY, encoding="utf-8") as f:
        registry = json.load(f)

    winners = registry.get("winners", [])
    updated = 0
    skipped = 0
    failed  = 0

    print(f"Processing {len(winners)} entries...\n")

    for w in winners:
        title  = w.get("title", "?")
        mal_url = w.get("mal_link", "")
        mal_id  = mal_id_from_url(mal_url)

        # Skip if thumbnail already set and not a bottany CDN placeholder
        existing = w.get("thumbnail", "")
        if existing and "cdn.bottany.app" not in existing:
            print(f"  SKIP  {title} (already has thumbnail)")
            skipped += 1
            continue

        if not mal_id:
            print(f"  SKIP  {title} (no MAL link)")
            skipped += 1
            continue

        print(f"  FETCH {title} (MAL {mal_id}) ... ", end="", flush=True)
        thumb = fetch_thumbnail(mal_id)
        time.sleep(SLEEP)

        if thumb:
            w["thumbnail"] = thumb
            # Also store a fallback field pointing to bottany CDN
            # so Seçenek A works automatically once CDN is set up
            if "cdn.bottany.app" in existing:
                w["thumbnail_cdn_fallback"] = existing
            print(f"OK → {thumb[:60]}...")
            updated += 1
        else:
            print("FAILED")
            failed += 1

    # Save updated registry
    with open(REGISTRY, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)

    print(f"\nDone. Updated: {updated}  Skipped: {skipped}  Failed: {failed}")
    print(f"Saved → {REGISTRY}")


if __name__ == "__main__":
    main()

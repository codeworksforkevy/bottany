"""
scripts/localpath_to_github_url.py
=====================================
generate_console_avatars.py ve generate_chocolate_avatars.py çalıştırıp
git push yaptıktan sonra bu scripti çalıştır.

JSON dosyalarındaki local asset path'lerini
GitHub raw URL'lerine çevirir — Discord embed'de çalışır.

Çalıştır (proje kökünden):
    python scripts/localpath_to_github_url.py

Örnek dönüşüm:
    "assets/consoles/avatars/nintendo_nes.png"
    → "https://raw.githubusercontent.com/codeworksforkevy/bottany/main/assets/consoles/avatars/nintendo_nes.png"
"""

from __future__ import annotations

import json
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
GITHUB_USER   = "codeworksforkevy"
GITHUB_REPO   = "bottany"
GITHUB_BRANCH = "main"

BASE_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}"

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

# ── Files to update ───────────────────────────────────────────────────────────
TARGETS = [
    {
        "file":      PROJECT_ROOT / "data" / "consoles_full.json",
        "top_key":   "consoles",
        "fields":    [("thumbnail", "avatar")],   # nested: item["thumbnail"]["avatar"]
    },
    {
        "file":      PROJECT_ROOT / "data" / "belgian_chocolate_professional.json",
        "top_key":   "items",
        "fields":    [("thumbnail_avatar",)],      # flat: item["thumbnail_avatar"]
    },
]


def _to_github_url(path: str) -> str:
    """Convert a local relative path to a GitHub raw URL."""
    # Normalise: remove leading "./" or "/"
    clean = path.lstrip("./")
    return f"{BASE_URL}/{clean}"


def _is_local(value: str) -> bool:
    """Return True if this looks like a local file path (not a URL)."""
    if not value:
        return False
    if value.startswith("http://") or value.startswith("https://"):
        return False
    return True


def process_file(target: dict) -> int:
    path    = target["file"]
    top_key = target["top_key"]
    fields  = target["fields"]

    if not path.exists():
        print(f"  SKIP  {path.name} — file not found")
        return 0

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    items   = data.get(top_key, [])
    updated = 0

    for item in items:
        for field_path in fields:
            if len(field_path) == 1:
                # Flat field: item["thumbnail_avatar"]
                key   = field_path[0]
                value = item.get(key, "")
                if _is_local(value):
                    item[key] = _to_github_url(value)
                    updated  += 1

            elif len(field_path) == 2:
                # Nested field: item["thumbnail"]["avatar"]
                parent_key, child_key = field_path
                parent = item.get(parent_key, {})
                if not isinstance(parent, dict):
                    continue
                value = parent.get(child_key, "")
                if _is_local(value):
                    parent[child_key] = _to_github_url(value)
                    updated += 1

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return updated


def main() -> None:
    print(f"Converting local paths → GitHub raw URLs")
    print(f"Repo: {GITHUB_USER}/{GITHUB_REPO} @ {GITHUB_BRANCH}\n")

    total = 0
    for target in TARGETS:
        name    = target["file"].name
        updated = process_file(target)
        total  += updated
        print(f"  {name}: {updated} path(s) converted")

    print(f"\nTotal: {total} path(s) converted")

    if total > 0:
        print()
        print("Next step — commit the updated JSON files:")
        print("  git add data/consoles_full.json")
        print("  git add data/belgian_chocolate_professional.json")
        print('  git commit -m "fix: convert avatar paths to GitHub raw URLs"')
        print("  git push")
    else:
        print("\nNothing to convert — either already URLs or no avatars generated yet.")
        print("Run generate_console_avatars.py and generate_chocolate_avatars.py first.")


if __name__ == "__main__":
    main()

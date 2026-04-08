"""
scripts/generate_avatars.py
=============================
Konsol ve çikolata avatar'larını Wikipedia REST API üzerinden indirir.

Neden Wikipedia REST API?
  - Doğrudan Wikimedia image server'ı yerine /page/summary/{title} endpoint'i kullanır
  - Rate limit çok daha toleranslı (~200 req/s vs 1 req/s)
  - Zaten optimize edilmiş thumbnail URL'leri döndürür (320px)
  - 429 hatası vermez

Çalıştırmak için (proje kökünden):
    pip install requests pillow
    python scripts/generate_avatars.py

Ardından:
    git add assets/
    git add data/consoles_full.json
    git add data/belgian_chocolate_professional.json
    git commit -m "feat: add avatar thumbnails"
    git push
    python scripts/localpath_to_github_url.py
"""

from __future__ import annotations

import json
import re
import time
from io import BytesIO
from pathlib import Path

try:
    import requests
    from PIL import Image
except ImportError:
    raise SystemExit("pip install requests pillow")

# ── Config ────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

AVATAR_SIZE  = (128, 128)
SLEEP        = 1.0   # 1 saniye — Wikipedia API çok toleranslı
HEADERS      = {
    "User-Agent": "Bottany-Bot/1.0 (avatar generator; github.com/codeworksforkevy/bottany)",
    "Accept":     "application/json",
}

WIKI_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"


# ── Wikipedia slug overrides for consoles ─────────────────────────────────────
CONSOLE_SLUGS: dict[str, str] = {
    "magnavox_odyssey":          "Magnavox_Odyssey",
    "fairchild_channel_f":       "Fairchild_Channel_F",
    "commodore_64":              "Commodore_64",
    "mattel_intellivision":      "Intellivision",
    "atari_2600":                "Atari_2600",
    "atari_5200":                "Atari_5200",
    "atari_7800":                "Atari_7800",
    "coleco_colecovision":       "ColecoVision",
    "nintendo_nes":              "Nintendo_Entertainment_System",
    "sega_master_system":        "Master_System",
    "nintendo_gameboy":          "Game_Boy",
    "sega_genesis":              "Sega_Genesis",
    "nintendo_snes":             "Super_Nintendo_Entertainment_System",
    "snk_neo_geo":               "Neo_Geo_(system)",
    "nec_turbografx":            "TurboGrafx-16",
    "sega_game_gear":            "Game_Gear",
    "sony_ps1":                  "PlayStation_(console)",
    "nintendo_n64":              "Nintendo_64",
    "sega_saturn":               "Sega_Saturn",
    "3do_interactive":           "3DO_Interactive_Multiplayer",
    "sega_dreamcast":            "Dreamcast",
    "nintendo_gamecube":         "GameCube",
    "microsoft_xbox":            "Xbox_(console)",
    "sony_ps2":                  "PlayStation_2",
    "nintendo_gameboy_advance":  "Game_Boy_Advance",
    "microsoft_xbox_360":        "Xbox_360",
    "sony_ps3":                  "PlayStation_3",
    "nintendo_wii":              "Wii",
    "sony_psp":                  "PlayStation_Portable",
    "nintendo_ds":               "Nintendo_DS",
    "microsoft_xbox_one":        "Xbox_One",
    "sony_ps4":                  "PlayStation_4",
    "nintendo_wii_u":            "Wii_U",
    "nintendo_3ds":              "Nintendo_3DS",
    "sony_ps_vita":              "PlayStation_Vita",
    "microsoft_xbox_series_x":   "Xbox_Series_X",
    "microsoft_xbox_series_s":   "Xbox_Series_S",
    "sony_ps5":                  "PlayStation_5",
    "nintendo_switch":           "Nintendo_Switch",
    "nintendo_switch_oled":      "Nintendo_Switch_(OLED_model)",
    "valve_steam_deck":          "Steam_Deck",
    "nokia_ngage":               "N-Gage_(device)",
    "bandai_wonderswan":         "WonderSwan",
}

# ── Wikipedia slug overrides for chocolate brands ─────────────────────────────
CHOCOLATE_SLUGS: dict[str, str] = {
    "Neuhaus":              "Neuhaus_(chocolate)",
    "Godiva":               "Godiva_Chocolatier",
    "Leonidas":             "Leonidas_(chocolate)",
    "Guylian":              "Guylian",
    "Pierre Marcolini":     "Pierre_Marcolini",
    "Galler":               "Galler_(chocolatier)",
    "Mary Chocolatier":     "Mary_(chocolatier)",
    "Côte d'Or":            "Côte_d'Or_(chocolate)",
    "Callebaut":            "Barry_Callebaut",
    "The Chocolate Line":   "The_Chocolate_Line",
    "Dolfin":               "Dolfin_(chocolate)",
}


# ── Core functions ────────────────────────────────────────────────────────────

def fetch_thumbnail_url(wiki_slug: str) -> str | None:
    """Wikipedia REST API'den thumbnail URL'sini çek."""
    url = WIKI_SUMMARY.format(wiki_slug)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            print(f"    Wikipedia API HTTP {resp.status_code}")
            return None
        data = resp.json()
        thumb = data.get("thumbnail", {})
        return thumb.get("source")   # already a sized URL like /320px-...
    except Exception as e:
        print(f"    Wikipedia API error: {e}")
        return None


def download_and_resize(url: str, output_path: Path) -> bool:
    """URL'den görseli indir, 128x128 kare PNG olarak kaydet."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"    Image download HTTP {resp.status_code}")
            return False

        img = Image.open(BytesIO(resp.content)).convert("RGBA")

        # Centre-crop to square
        w, h = img.size
        side = min(w, h)
        img  = img.crop(((w - side) // 2, (h - side) // 2,
                          (w + side) // 2, (h + side) // 2))
        img  = img.resize(AVATAR_SIZE, Image.LANCZOS)
        img.save(output_path, "PNG")
        return True
    except Exception as e:
        print(f"    Image error: {e}")
        return False


def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s-]+", "_", s)
    return s


# ── Console avatars ───────────────────────────────────────────────────────────

def generate_console_avatars() -> None:
    registry_path = PROJECT_ROOT / "data" / "consoles_full.json"
    avatar_dir    = PROJECT_ROOT / "assets" / "consoles" / "avatars"
    avatar_dir.mkdir(parents=True, exist_ok=True)

    with open(registry_path, encoding="utf-8") as f:
        registry = json.load(f)

    consoles = registry.get("consoles", [])
    print(f"\n{'='*50}")
    print(f"CONSOLES — {len(consoles)} items")
    print(f"{'='*50}")

    updated = skipped = failed = 0

    for c in consoles:
        cid  = c.get("id", "unknown")
        name = c.get("name", "?")
        path = avatar_dir / f"{cid}.png"

        if path.exists():
            print(f"  SKIP  {name} (already exists)")
            c["thumbnail"]["avatar"] = str(path.relative_to(PROJECT_ROOT))
            skipped += 1
            continue

        # Get Wikipedia slug
        wiki_slug = CONSOLE_SLUGS.get(cid) or name.replace(" ", "_")

        print(f"  WIKI  {name} ({wiki_slug}) ... ", end="", flush=True)
        thumb_url = fetch_thumbnail_url(wiki_slug)
        time.sleep(SLEEP)

        if not thumb_url:
            # Fallback: use the full Wikimedia URL directly from JSON
            thumb_url = c.get("thumbnail", {}).get("full", "")

        if not thumb_url:
            print("no image found")
            failed += 1
            continue

        print(f"downloading ... ", end="", flush=True)
        ok = download_and_resize(thumb_url, path)
        time.sleep(SLEEP)

        if ok:
            c["thumbnail"]["avatar"] = str(path.relative_to(PROJECT_ROOT))
            print(f"OK → {path.name}")
            updated += 1
        else:
            print("FAILED")
            failed += 1

    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)

    print(f"\nConsoles: {updated} created, {skipped} skipped, {failed} failed")


# ── Chocolate avatars ─────────────────────────────────────────────────────────

def generate_chocolate_avatars() -> None:
    registry_path = PROJECT_ROOT / "data" / "belgian_chocolate_professional.json"
    avatar_dir    = PROJECT_ROOT / "assets" / "chocolate" / "avatars"
    avatar_dir.mkdir(parents=True, exist_ok=True)

    with open(registry_path, encoding="utf-8") as f:
        registry = json.load(f)

    items = registry.get("items", [])
    print(f"\n{'='*50}")
    print(f"CHOCOLATE — {len(items)} items")
    print(f"{'='*50}")

    updated = skipped = failed = 0

    for item in items:
        name = item.get("name", "unknown")
        slug = slugify(name)
        path = avatar_dir / f"{slug}.png"

        if path.exists():
            print(f"  SKIP  {name} (already exists)")
            item["thumbnail_avatar"] = str(path.relative_to(PROJECT_ROOT))
            skipped += 1
            continue

        # Try Wikipedia API first
        wiki_slug = CHOCOLATE_SLUGS.get(name) or name.replace(" ", "_")
        print(f"  WIKI  {name} ({wiki_slug}) ... ", end="", flush=True)
        thumb_url = fetch_thumbnail_url(wiki_slug)
        time.sleep(SLEEP)

        # Fallback: use image_url from JSON directly
        if not thumb_url:
            thumb_url = item.get("image_url", "")
            if thumb_url:
                print(f"fallback to image_url ... ", end="", flush=True)

        if not thumb_url:
            print("no image found")
            failed += 1
            continue

        print(f"downloading ... ", end="", flush=True)
        ok = download_and_resize(thumb_url, path)
        time.sleep(SLEEP)

        if ok:
            item["thumbnail_avatar"] = str(path.relative_to(PROJECT_ROOT))
            print(f"OK → {path.name}")
            updated += 1
        else:
            print("FAILED")
            failed += 1

    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)

    print(f"\nChocolate: {updated} created, {skipped} skipped, {failed} failed")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Bottany Avatar Generator")
    print("Source: Wikipedia REST API + Wikimedia fallback")
    print(f"Sleep between requests: {SLEEP}s\n")

    generate_console_avatars()
    generate_chocolate_avatars()

    print(f"\n{'='*50}")
    print("Done! Next steps:")
    print()
    print("  git add assets/")
    print("  git add data/consoles_full.json")
    print("  git add data/belgian_chocolate_professional.json")
    print('  git commit -m "feat: add avatar thumbnails"')
    print("  git push")
    print()
    print("  python scripts/localpath_to_github_url.py")
    print()
    print("  git add data/consoles_full.json data/belgian_chocolate_professional.json")
    print('  git commit -m "fix: avatar paths to GitHub raw URLs"')
    print("  git push")


if __name__ == "__main__":
    main()

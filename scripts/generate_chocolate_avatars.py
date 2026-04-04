"""
scripts/generate_chocolate_avatars.py
======================================
Wikimedia'dan Belçika çikolata markalarının görsellerini indirir,
128x128 PNG'ye küçültür ve data/belgian_chocolate_professional.json'a
thumbnail_avatar alanı olarak ekler.

Çalıştırmak için (proje kökünden):
    pip install requests pillow
    python scripts/generate_chocolate_avatars.py

Görseller şuraya kaydedilir:
    assets/chocolate/avatars/<brand_slug>.png

JSON güncellenir:
    data/belgian_chocolate_professional.json
        → her item'a thumbnail_avatar alanı eklenir
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
    raise SystemExit(
        "Önce gerekli paketleri yükle:\n"
        "    pip install requests pillow"
    )

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
REGISTRY     = PROJECT_ROOT / "data" / "belgian_chocolate_professional.json"
AVATAR_DIR   = PROJECT_ROOT / "assets" / "chocolate" / "avatars"

AVATAR_SIZE  = (128, 128)
SLEEP        = 0.5


# ── Helpers ────────────────────────────────────────────────────────────────────

def slugify(name: str) -> str:
    """'Pierre Marcolini' → 'pierre_marcolini'"""
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s-]+", "_", s)
    return s


def download_and_resize(url: str, output_path: Path) -> bool:
    """Görseli indir, kare crop yap, 128x128'e küçült, PNG olarak kaydet."""
    try:
        headers = {"User-Agent": "Bottany-Bot/1.0 (chocolate avatar generator)"}
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            print(f"    HTTP {resp.status_code} — atlandı")
            return False

        img = Image.open(BytesIO(resp.content)).convert("RGBA")

        # Ortadan kare crop — uzatma/bozma olmadan
        w, h  = img.size
        side  = min(w, h)
        left  = (w - side) // 2
        top   = (h - side) // 2
        img   = img.crop((left, top, left + side, top + side))

        img = img.resize(AVATAR_SIZE, Image.LANCZOS)
        img.save(output_path, "PNG")
        return True

    except Exception as e:
        print(f"    Hata: {e}")
        return False


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    if not REGISTRY.exists():
        raise SystemExit(f"Registry bulunamadı: {REGISTRY}")

    AVATAR_DIR.mkdir(parents=True, exist_ok=True)

    with open(REGISTRY, encoding="utf-8") as f:
        registry = json.load(f)

    items = registry.get("items", [])
    print(f"{len(items)} marka işlenecek\n")

    updated = 0
    skipped = 0
    failed  = 0

    for item in items:
        name      = item.get("name", "unknown")
        slug      = slugify(name)
        image_url = item.get("image_url", "")

        avatar_path = AVATAR_DIR / f"{slug}.png"

        # Zaten oluşturulmuşsa path'i güncelle ve geç
        if avatar_path.exists():
            print(f"  SKIP  {name} (zaten var)")
            item["thumbnail_avatar"] = str(avatar_path.relative_to(PROJECT_ROOT))
            skipped += 1
            continue

        if not image_url:
            print(f"  SKIP  {name} (image_url yok)")
            skipped += 1
            continue

        print(f"  FETCH {name} ... ", end="", flush=True)
        ok = download_and_resize(image_url, avatar_path)
        time.sleep(SLEEP)

        if ok:
            item["thumbnail_avatar"] = str(avatar_path.relative_to(PROJECT_ROOT))
            print(f"OK → {avatar_path.name}")
            updated += 1
        else:
            print("FAILED")
            failed += 1

    # Kaydet
    with open(REGISTRY, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)

    print(f"\nTamamlandı.")
    print(f"  Oluşturuldu:  {updated}")
    print(f"  Atlandı:      {skipped}")
    print(f"  Başarısız:    {failed}")
    print(f"\nGörseller: {AVATAR_DIR}")
    print(f"Registry güncellendi: {REGISTRY}")
    print()
    print("Commit:")
    print("  git add assets/chocolate/avatars/ data/belgian_chocolate_professional.json")
    print('  git commit -m "feat: add chocolate brand avatar thumbnails"')
    print("  git push")


if __name__ == "__main__":
    main()

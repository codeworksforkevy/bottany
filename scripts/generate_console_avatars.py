"""
scripts/generate_console_avatars.py
====================================
Wikimedia'dan konsol görsellerini indirir, 128x128 PNG'ye küçültür
ve data/consoles_full.json'daki thumbnail.avatar alanlarını günceller.

Çalıştırmak için (proje kökünden):
    pip install requests pillow
    python scripts/generate_console_avatars.py

Görseller şuraya kaydedilir:
    assets/consoles/avatars/<console_id>.png

JSON güncellenir:
    data/consoles_full.json  →  thumbnail.avatar = "assets/consoles/avatars/<id>.png"
"""

from __future__ import annotations

import json
import os
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
REGISTRY     = PROJECT_ROOT / "data" / "consoles_full.json"
AVATAR_DIR   = PROJECT_ROOT / "assets" / "consoles" / "avatars"

AVATAR_SIZE  = (128, 128)
SLEEP        = 3.0    # Wikimedia rate limit — 3 saniye bekleme
MAX_RETRIES  = 4      # 429 alınca kaç kez tekrar dene
RETRY_WAIT   = 15.0   # 429 sonrası kaç saniye bekle


# ── Image download & resize ────────────────────────────────────────────────────

def download_and_resize(url: str, output_path: Path) -> bool:
    """
    URL'den görseli indir, 128x128 PNG'ye küçült ve kaydet.
    429 (rate limit) alınca MAX_RETRIES kez tekrar dener.
    Başarılı olursa True, hata olursa False döner.
    """
    headers = {"User-Agent": "Bottany-Bot/1.0 (console avatar generator)"}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, headers=headers, timeout=20)

            if response.status_code == 429:
                wait = RETRY_WAIT * attempt
                print(f"    Rate limit (429) — {wait:.0f}s bekleniyor (deneme {attempt}/{MAX_RETRIES}) ...", end="", flush=True)
                time.sleep(wait)
                print(" tekrar deneniyor")
                continue

            if response.status_code != 200:
                print(f"    HTTP {response.status_code} — atlandı")
                return False

            img = Image.open(BytesIO(response.content)).convert("RGBA")

            # Kare crop — ortadan kırp, uzatma/bozma olmadan
            w, h = img.size
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

    print(f"    Maksimum deneme aşıldı — atlandı")
    return False


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    if not REGISTRY.exists():
        raise SystemExit(f"Registry bulunamadı: {REGISTRY}")

    AVATAR_DIR.mkdir(parents=True, exist_ok=True)

    with open(REGISTRY, encoding="utf-8") as f:
        registry = json.load(f)

    consoles = registry.get("consoles", [])
    print(f"{len(consoles)} konsol işlenecek\n")

    updated = 0
    skipped = 0
    failed  = 0

    for c in consoles:
        cid   = c.get("id", "unknown")
        name  = c.get("name", "?")
        thumb = c.get("thumbnail", {})

        avatar_path = AVATAR_DIR / f"{cid}.png"

        # Zaten oluşturulmuşsa atla
        if avatar_path.exists():
            print(f"  SKIP  {name} (zaten var)")
            # JSON'u yine de güncelle (path doğru olsun)
            c["thumbnail"]["avatar"] = str(avatar_path.relative_to(PROJECT_ROOT))
            skipped += 1
            continue

        # Kaynak URL — Wikimedia full görseli kullan
        source_url = thumb.get("full", "")
        if not source_url:
            print(f"  SKIP  {name} (source URL yok)")
            skipped += 1
            continue

        print(f"  FETCH {name} ... ", end="", flush=True)
        ok = download_and_resize(source_url, avatar_path)
        time.sleep(SLEEP)

        if ok:
            c["thumbnail"]["avatar"] = str(avatar_path.relative_to(PROJECT_ROOT))
            print(f"OK → {avatar_path.name}")
            updated += 1
        else:
            failed += 1

    # Güncellenen registry'i kaydet
    with open(REGISTRY, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)

    print(f"\nTamamlandı.")
    print(f"  Oluşturuldu:  {updated}")
    print(f"  Atlandı:      {skipped}")
    print(f"  Başarısız:    {failed}")
    print(f"\nGörseller: {AVATAR_DIR}")
    print(f"Registry güncellendi: {REGISTRY}")
    print()
    print("Sonraki adım — değişiklikleri commit et:")
    print("  git add assets/consoles/avatars/ data/consoles_full.json")
    print('  git commit -m "feat: add console avatar thumbnails"')
    print("  git push")


if __name__ == "__main__":
    main()

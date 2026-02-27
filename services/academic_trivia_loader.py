from __future__ import annotations

import json
import random
from pathlib import Path
from typing import List, Dict, Optional


# =====================================================
# LOAD ALL JSON FILES FROM academic-trivia/
# =====================================================

def load_all_trivia(base_dir: Path) -> List[Dict]:
    trivia_dir = base_dir / "academic-trivia"

    if not trivia_dir.exists():
        print("[WARN] academic-trivia directory not found.")
        return []

    pool: List[Dict] = []

    for file in trivia_dir.glob("*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)

                if not isinstance(data, list):
                    print(f"[WARN] {file.name} is not a list. Skipped.")
                    continue

                # Category otomatik olarak dosya adından türetilir
                category_name = file.stem.lower()

                for item in data:
                    if not isinstance(item, dict):
                        continue

                    if "text" not in item:
                        continue

                    item.setdefault("author", None)
                    item.setdefault("field", None)
                    item.setdefault("weight", 1)

                    # Eğer JSON içinde category yoksa dosya adını ata
                    item.setdefault("category", category_name)

                    pool.append(item)

        except Exception as e:
            print(f"[ERROR] Failed loading {file.name}: {e}")

    return pool


# =====================================================
# WEIGHTED RANDOM SELECTION
# =====================================================

def weighted_sample(pool: List[Dict], size: int) -> List[Dict]:
    if not pool:
        return []

    weights = [item.get("weight", 1) for item in pool]

    # random.choices duplicates verebilir — biz unique istiyoruz
    selected = []
    used_indexes = set()

    while len(selected) < min(size, len(pool)):
        idx = random.choices(range(len(pool)), weights=weights, k=1)[0]
        if idx not in used_indexes:
            used_indexes.add(idx)
            selected.append(pool[idx])

    return selected


# =====================================================
# PUBLIC API
# =====================================================

def get_weighted_batch(
    base_dir: Path,
    user_id: int,
    size: int = 25,
    category: Optional[str] = None
) -> List[Dict]:

    pool = load_all_trivia(base_dir)

    if not pool:
        return []

    # ---------------------------------------------
    # CATEGORY FILTER
    # ---------------------------------------------
    if category:
        category = category.lower().strip()
        pool = [
            item for item in pool
            if item.get("category", "").lower() == category
        ]

    if not pool:
        return []

    # ---------------------------------------------
    # WEIGHTED SAMPLE
    # ---------------------------------------------
    return weighted_sample(pool, size)

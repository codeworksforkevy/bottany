from __future__ import annotations

import json
import random
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


class AcademicTriviaService:

    # ==============================
    # INTERNAL STATE (CACHE)
    # ==============================

    _pool: List[Dict] = []
    _categories: set[str] = set()
    _user_seen: Dict[int, set] = {}

    _initialized: bool = False
    _last_loaded: Optional[datetime] = None

    # =====================================================
    # INITIALIZE (BOT STARTUP OR RELOAD)
    # =====================================================

@classmethod
def initialize(cls, base_dir: Path, force: bool = False) -> None:

    if cls._initialized and not force:
        return

    trivia_dir = base_dir / "academic-trivia"

    if not trivia_dir.exists():
        print("[WARN] academic-trivia directory not found.")
        cls._pool = []
        cls._categories = set()
        cls._initialized = False
        return

    pool: List[Dict] = []

    for file in trivia_dir.glob("*.json"):

        # Skip metadata file
        if file.name == "academic_trivia_index.json":
            continue

        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # ------------------------------------------------
            # SMART JSON NORMALIZATION
            # ------------------------------------------------

            if isinstance(data, dict):

                # Case 1: {"quotes": [...]}
                if "quotes" in data and isinstance(data["quotes"], list):
                    data = data["quotes"]

                # Case 2: {"1": {...}, "2": {...}}
                else:
                    data = list(data.values())

            if not isinstance(data, list):
                print(f"[WARN] {file.name} unsupported format. Skipped.")
                continue

            category_name = file.stem.lower()

            for item in data:
                if not isinstance(item, dict):
                    continue

                if "text" not in item:
                    continue

                item.setdefault("author", None)
                item.setdefault("field", None)
                item.setdefault("weight", 1)
                item.setdefault("category", category_name)

                pool.append(item)

        except Exception as e:
            print(f"[ERROR] Failed loading {file.name}: {e}")

    cls._pool = pool
    cls._categories = {item["category"] for item in pool}
    cls._user_seen = {}
    cls._initialized = True
    cls._last_loaded = datetime.utcnow()

    print(f"[AcademicTrivia] Loaded {len(pool)} items.")

    # =====================================================
    # PUBLIC ACCESS METHODS
    # =====================================================

    @classmethod
    def is_ready(cls) -> bool:
        return cls._initialized and bool(cls._pool)

    @classmethod
    def get_categories(cls) -> List[str]:
        return sorted(cls._categories)

    @classmethod
    def get_stats(cls) -> Dict:

        total = len(cls._pool)

        per_category: Dict[str, int] = {}

        for item in cls._pool:
            cat = item.get("category", "unknown")
            per_category[cat] = per_category.get(cat, 0) + 1

        return {
            "total": total,
            "categories": per_category,
            "unique_users_tracked": len(cls._user_seen)
        }

    @classmethod
    def get_cache_info(cls) -> Dict:
        return {
            "initialized": cls._initialized,
            "total_items": len(cls._pool),
            "categories": len(cls._categories),
            "users_tracked": len(cls._user_seen),
            "last_loaded": cls._last_loaded
        }

    # =====================================================
    # MAIN BATCH ACCESS
    # =====================================================

    @classmethod
    def get_batch(
        cls,
        user_id: int,
        size: int = 25,
        category: Optional[str] = None
    ) -> List[Dict]:

        if not cls.is_ready():
            return []

        pool = cls._pool

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
        # USER DUPLICATE PREVENTION
        # ---------------------------------------------
        seen = cls._user_seen.setdefault(user_id, set())

        available = [
            item for item in pool
            if id(item) not in seen
        ]

        # If exhausted → reset user session
        if not available:
            cls._user_seen[user_id] = set()
            available = pool
            seen = cls._user_seen[user_id]

        # ---------------------------------------------
        # WEIGHTED UNIQUE SAMPLE
        # ---------------------------------------------
        selected = cls._weighted_unique_sample(
            available,
            size
        )

        for item in selected:
            seen.add(id(item))

        return selected

    # =====================================================
    # INTERNAL WEIGHTED SAMPLER
    # =====================================================

    @staticmethod
    def _weighted_unique_sample(
        pool: List[Dict],
        size: int
    ) -> List[Dict]:

        if not pool:
            return []

        size = min(size, len(pool))

        selected: List[Dict] = []
        used_indexes = set()

        weights = [item.get("weight", 1) for item in pool]

        while len(selected) < size:
            idx = random.choices(
                range(len(pool)),
                weights=weights,
                k=1
            )[0]

            if idx not in used_indexes:
                used_indexes.add(idx)
                selected.append(pool[idx])

        return selected

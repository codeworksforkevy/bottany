from __future__ import annotations

import json
import random
from pathlib import Path
from typing import List, Dict, Optional


class AcademicTriviaService:

    _pool: List[Dict] = []
    _user_seen: Dict[int, set] = {}

    # =====================================================
    # INITIALIZE (BOT STARTUP)
    # =====================================================

    @classmethod
    def initialize(cls, base_dir: Path) -> None:
        trivia_dir = base_dir / "academic-trivia"

        if not trivia_dir.exists():
            print("[WARN] academic-trivia directory not found.")
            cls._pool = []
            return

        pool: List[Dict] = []

        for file in trivia_dir.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if not isinstance(data, list):
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
        print(f"[AcademicTrivia] Loaded {len(pool)} items.")

    # =====================================================
    # PUBLIC ACCESS
    # =====================================================

    @classmethod
    def get_batch(
        cls,
        user_id: int,
        size: int = 25,
        category: Optional[str] = None
    ) -> List[Dict]:

        if not cls._pool:
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

        # Eğer tüm kategori tükenmişse reset
        if not available:
            cls._user_seen[user_id] = set()
            available = pool

        # ---------------------------------------------
        # WEIGHTED UNIQUE SAMPLE
        # ---------------------------------------------
        selected = cls._weighted_unique_sample(
            available,
            size
        )

        # Seen listesine ekle
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

        selected = []
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

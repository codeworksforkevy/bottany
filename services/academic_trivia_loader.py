import json
import random
from pathlib import Path


def load_academic_directory(base_path: Path):
    """
    Loads all academic trivia JSON files from:
    academic-trivia/academic-trivia/
    """

    trivia_dir = base_path / "academic-trivia" / "academic-trivia"

    if not trivia_dir.exists():
        print(f"[WARN] Trivia directory not found: {trivia_dir}")
        return []

    all_items = []

    for file in trivia_dir.glob("*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)

            metadata = data.get("metadata", {})
            author = metadata.get("author", "Unknown Author")

            for entry in data.get("entries", []):
                text = entry.get("text", "").strip()

                if not text:
                    continue

                all_items.append({
                    "text": text,
                    "field": entry.get("field", ""),
                    "author": author,
                    "source_file": file.name
                })

        except Exception as e:
            print(f"[ERROR] Failed loading {file.name}: {e}")

    return all_items


def get_random_batch(base_path: Path, size: int = 25):
    items = load_academic_directory(base_path)

    if not items:
        return []

    random.shuffle(items)
    return items[:size]


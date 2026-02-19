import json
import os
import hashlib
from pathlib import Path


# -------------------------------------------------
# UTIL
# -------------------------------------------------

def load_module(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] Failed to load {path}: {e}")
        return None


def normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# -------------------------------------------------
# DUPLICATE DETECTOR
# -------------------------------------------------

def detect_duplicates(directory="data/academic_trivia"):

    base = Path(directory)

    if not base.exists():
        print(f"[ERROR] Directory not found: {directory}")
        return []

    seen = {}
    duplicates = []

    total_entries = 0

    for path in base.glob("*.json"):

        data = load_module(path)
        if not data:
            continue

        for entry in data.get("entries", []):

            text = entry.get("text", "")
            if not text:
                continue

            total_entries += 1

            normalized = normalize(text)
            key = hash_text(normalized)

            meta = {
                "file": path.name,
                "id": entry.get("id"),
                "text_preview": normalized[:120]
            }

            if key in seen:
                duplicates.append({
                    "original": seen[key],
                    "duplicate": meta
                })
            else:
                seen[key] = meta

    print(f"Scanned entries: {total_entries}")
    print(f"Unique entries: {len(seen)}")
    print(f"Duplicate count: {len(duplicates)}")

    return duplicates


# -------------------------------------------------
# CLI
# -------------------------------------------------

if __name__ == "__main__":

    dups = detect_duplicates()

    if not dups:
        print("No duplicates detected.")
    else:
        print("\nDuplicates found:\n")
        for d in dups:
            print("----")
            print("Original:")
            print(d["original"])
            print("Duplicate:")
            print(d["duplicate"])

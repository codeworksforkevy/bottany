import os
import json
import random

def load_academic_trivia_from_directory(base_dir):
    trivia_pool = []

    trivia_dir = os.path.join(base_dir, "academic-trivia", "academic-trivia")

    if not os.path.exists(trivia_dir):
        print(f"[WARN] Trivia directory not found: {trivia_dir}")
        return trivia_pool

    for filename in os.listdir(trivia_dir):
        if filename.endswith(".json"):
            path = os.path.join(trivia_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        trivia_pool.extend(data)
                    else:
                        print(f"[WARN] {filename} is not a list")
            except Exception as e:
                print(f"[ERROR] Failed loading {filename}: {e}")

    return trivia_pool


def get_random_trivia(base_dir):
    pool = load_academic_trivia_from_directory(base_dir)
    if not pool:
        return None
    return random.choice(pool)

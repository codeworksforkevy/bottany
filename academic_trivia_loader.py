
import json
import os
import random

BASE_DIR = "data/academic_trivia"
INDEX_FILE = os.path.join(BASE_DIR, "index.json")

def load_index():
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def load_module(name):
    path = os.path.join(BASE_DIR, f"{name}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_all_entries():
    index = load_index()
    modules = index.get("modules", [])
    all_entries = []

    for mod in modules:
        data = load_module(mod)
        all_entries.extend(data.get("entries", []))

    return all_entries

def random_trivia():
    entries = load_all_entries()
    return random.choice(entries) if entries else None

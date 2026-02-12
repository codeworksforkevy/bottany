
import json
import os
import hashlib

def load_module(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def normalize(text):
    return text.lower().strip()

def detect_duplicates(directory="data/academic_trivia"):
    seen = {}
    duplicates = []

    for filename in os.listdir(directory):
        if not filename.endswith(".json"):
            continue

        path = os.path.join(directory, filename)
        data = load_module(path)

        for entry in data.get("entries", []):
            key = hashlib.sha256(normalize(entry["text"]).encode()).hexdigest()

            if key in seen:
                duplicates.append((filename, seen[key]))
            else:
                seen[key] = filename

    return duplicates

if __name__ == "__main__":
    dups = detect_duplicates()
    if dups:
        print("Duplicates found:")
        for d in dups:
            print(d)
    else:
        print("No duplicates detected.")

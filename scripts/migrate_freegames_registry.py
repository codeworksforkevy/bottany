import os, json, shutil

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DATA_DIR = os.path.abspath(DATA_DIR)

CANON = os.path.join(DATA_DIR, "freegames_registry.json")
ALT   = os.path.join(DATA_DIR, "free_games_registry.json")

def load(p, default):
    try:
        with open(p,"r",encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save(p, obj):
    with open(p,"w",encoding="utf-8") as f:
        json.dump(obj,f,ensure_ascii=False,indent=2)

def deep_merge(a, b):
    # merge dict b into a (a wins on conflicts)
    if not isinstance(a, dict) or not isinstance(b, dict):
        return a
    out=dict(b)
    out.update(a)
    # merge nested sources dict
    if isinstance(a.get("sources"), dict) and isinstance(b.get("sources"), dict):
        s=dict(b["sources"])
        s.update(a["sources"])
        out["sources"]=s
    return out

def main():
    a = load(CANON, {})
    b = load(ALT, {})
    if not a and not b:
        print("No registry found.")
        return
    merged = deep_merge(a, b) if a else b
    save(CANON, merged)
    if os.path.exists(ALT):
        backup = ALT + ".bak"
        shutil.move(ALT, backup)
        print(f"Moved {ALT} -> {backup}")
    print(f"Wrote canonical registry: {CANON}")

if __name__ == "__main__":
    main()

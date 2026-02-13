
try:
    from rapidfuzz import process, fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    from difflib import get_close_matches
    RAPIDFUZZ_AVAILABLE = False

def fuzzy_search(query, items, key="name", limit=10, score_cutoff=60):

    if not query:
        return []

    if RAPIDFUZZ_AVAILABLE:
        choices = {item[key]: item for item in items if key in item}
        results = process.extract(
            query,
            choices.keys(),
            scorer=fuzz.WRatio,
            limit=limit
        )
        return [
            choices[name]
            for name, score, _ in results
            if score >= score_cutoff
        ]
    else:
        names = [item.get(key, "") for item in items]
        matches = get_close_matches(query, names, n=limit, cutoff=0.6)
        return [item for item in items if item.get(key) in matches]

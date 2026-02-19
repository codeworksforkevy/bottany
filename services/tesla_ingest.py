import requests
from datetime import datetime
from services.tesla_cache import load_cache, save_cache, refresh_needed


PATENTSVIEW_URL = "https://api.patentsview.org/patents/query"


def classify_category(title: str) -> str:
    t = title.lower()

    if "alternating" in t or "ac" in t:
        return "alternating_current"
    if "wireless" in t:
        return "wireless_power"
    if "radio" in t:
        return "radio_transmission"
    if "turbine" in t:
        return "turbine"
    if "motor" in t:
        return "electric_motor"
    return "electrical_general"


def fetch_from_api():
    payload = {
        "q": {
            "_and": [
                {"inventor_first_name": "Nikola"},
                {"inventor_last_name": "Tesla"}
            ]
        },
        "f": [
            "patent_number",
            "patent_title",
            "patent_date",
            "patent_abstract"
        ],
        "o": {"per_page": 200}
    }

    response = requests.post(PATENTSVIEW_URL, json=payload, timeout=20)
    response.raise_for_status()

    data = response.json()
    patents = data.get("patents", [])

    normalized = []

    for idx, p in enumerate(patents):
        normalized.append({
            "id": f"tesla_{idx+1}",
            "patent_number": p.get("patent_number"),
            "title": p.get("patent_title"),
            "year": int(p.get("patent_date", "0000")[:4]),
            "category": classify_category(p.get("patent_title", "")),
            "abstract": p.get("patent_abstract", ""),
            "source_reference": "USPTO PatentsView"
        })

    return normalized


def get_tesla_data(data_dir, config):

    cache_path = os.path.join(data_dir, config["cache_file"])
    cache_data = load_cache(cache_path)

    if refresh_needed(cache_data, config["refresh_days"]):

        try:
            entries = fetch_from_api()

            cache_data = {
                "meta": {
                    "last_refresh_utc": datetime.utcnow().isoformat(),
                    "total_entries": len(entries),
                    "source": "USPTO PatentsView API"
                },
                "entries": entries
            }

            save_cache(cache_path, cache_data)

        except Exception:
            # API fail ederse eski cache kullan
            if cache_data:
                return cache_data
            raise

    return cache_data

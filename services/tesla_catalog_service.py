
import os
import re
import random
from datetime import datetime
from bs4 import BeautifulSoup
from utils.json_io import load_json, save_json
from utils.async_http import fetch_text

MIT_URL = "https://web.mit.edu/most/Public/Tesla1/alpha_tesla.html"

def _extract_patents(html: str):
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for tr in soup.find_all("tr"):
        text = tr.get_text(" ", strip=True)
        m = re.search(r"\b(\d{3,}(?:,\d{3})*)\b", text)
        if not m:
            continue
        pat = m.group(1).replace(",", "")
        title = text.split(str(m.group(1)))[0].strip() or "Untitled"
        items.append({
            "title": title,
            "patent_number": pat,
            "grant_date": "",
            "source_name": "MIT Tesla U.S. Patent Collection",
            "source_url": MIT_URL
        })
    # dedupe
    seen = set()
    dedup = []
    for i in items:
        if i["patent_number"] in seen:
            continue
        seen.add(i["patent_number"])
        dedup.append(i)
    return dedup

async def _build_catalog(data_dir: str, target: int):
    html = await fetch_text(MIT_URL)
    items = _extract_patents(html)[:target]
    return {
        "generated_utc": datetime.utcnow().isoformat() + "Z",
        "count": len(items),
        "items": items
    }

async def get_tesla_catalog(data_dir: str, refresh_days: int = 30, target: int = 150):
    cache_path = os.path.join(data_dir, "tesla_cache.json")
    cache = load_json(cache_path)

    if cache.get("generated_utc"):
        try:
            dt = datetime.fromisoformat(cache["generated_utc"].replace("Z",""))
            if (datetime.utcnow() - dt).days < refresh_days:
                return cache
        except Exception:
            pass

    catalog = await _build_catalog(data_dir, target)
    save_json(cache_path, catalog)
    return catalog

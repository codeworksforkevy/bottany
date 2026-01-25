from __future__ import annotations
import os, json
import requests
from datetime import datetime

DATAPOINT_BASE = "http://datapoint.metoffice.gov.uk/public/data"

def main():
    key = (os.getenv("METOFFICE_API_KEY","") or "").strip()
    if not key:
        raise SystemExit("Missing METOFFICE_API_KEY.")
    url = f"{DATAPOINT_BASE}/val/wxfcs/all/json/sitelist?key={key}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()
    loc = (((data.get("Locations") or {}).get("Location")) or [])
    if isinstance(loc, dict):
        loc = [loc]
    sites = []
    for it in loc:
        sites.append({
            "id": str(it.get("id","")),
            "name": it.get("name",""),
            "latitude": it.get("latitude",""),
            "longitude": it.get("longitude",""),
            "country": it.get("country","UK"),
        })
    out = {
        "updated_utc": datetime.utcnow().replace(microsecond=0).isoformat()+"Z",
        "sites": sites,
    }
    os.makedirs("data", exist_ok=True)
    with open("data/metoffice_sites_cache.json","w",encoding="utf-8") as f:
        json.dump(out,f,ensure_ascii=False,indent=2)
    print(f"Wrote {len(sites)} sites to data/metoffice_sites_cache.json")

if __name__ == "__main__":
    main()

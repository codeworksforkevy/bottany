from __future__ import annotations
import requests
from typing import Dict, List, Optional

def search_datasets(api_base: str, query: str = "*", per_page: int = 100, max_results: int = 300, timeout_s: int = 30) -> List[Dict]:
    out: List[Dict] = []
    session = requests.Session()

    start = 0
    while start < max_results:
        r = session.get(
            f"{api_base}/search",
            params={"q": query, "type": "dataset", "per_page": per_page, "start": start},
            timeout=timeout_s,
        )
        r.raise_for_status()
        data = r.json()
        items = data.get("data", {}).get("items", []) or []
        if not items:
            break
        out.extend(items)
        start += per_page
        if len(items) < per_page:
            break

    return out[:max_results]

def get_dataset_by_persistent_id(api_base: str, persistent_id: str, timeout_s: int = 30) -> Dict:
    r = requests.get(f"{api_base}/datasets/:persistentId", params={"persistentId": persistent_id}, timeout=timeout_s)
    r.raise_for_status()
    return r.json()

def extract_cc0_fact(dataset_json: Dict) -> Dict:
    data = dataset_json.get("data", {}) or {}
    # Try a few fields: termsOfUse, license, or metadata text fields.
    terms = (data.get("termsOfUse") or "").strip()
    license_text = (data.get("license") or "").strip()
    # citation/description
    latest = data.get("latestVersion", {}) or {}
    md = latest.get("metadataBlocks", {}) or {}
    citation = md.get("citation", {}) or {}
    fields = citation.get("fields", []) or []
    title = ""
    description = ""
    for f in fields:
        if f.get("typeName") == "title":
            title = f.get("value") or ""
        if f.get("typeName") in ("dsDescription", "description"):
            # dsDescription is a list
            val = f.get("value")
            if isinstance(val, list) and val:
                # take first description value
                v0 = val[0].get("dsDescriptionValue") if isinstance(val[0], dict) else None
                if isinstance(v0, dict):
                    description = v0.get("value") or ""
                elif isinstance(v0, str):
                    description = v0
                elif isinstance(val[0], dict) and "value" in val[0]:
                    description = val[0]["value"]
            elif isinstance(val, str):
                description = val
    pid = (data.get("persistentId") or "").strip()
    return {
        "title": title,
        "description": description,
        "rights": " ".join([t for t in [license_text, terms] if t]).strip(),
        "source_url": f"https://dataverse.harvard.edu/dataset.xhtml?persistentId={pid}" if pid else "",
        "persistent_id": pid,
    }

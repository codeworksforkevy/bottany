import re
from typing import Any, Dict, Iterable, List, Optional

import requests


def _normalize_license(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip()).lower()


def _license_ok(rights_list: Any, license_allowlist: List[str]) -> bool:
    """Return True if any rightsURI / rightsIdentifier matches allowlist."""
    if not rights_list:
        return False
    allow_norm = {_normalize_license(x) for x in (license_allowlist or [])}

    for r in rights_list:
        if not isinstance(r, dict):
            continue
        for key in ("rightsUri", "rightsURI", "rightsIdentifier", "rights", "rightsIdentifierScheme"):
            v = r.get(key)
            if isinstance(v, str) and _normalize_license(v) in allow_norm:
                return True
        # Many records put the full URL in rightsUri
        v = r.get("rightsUri") or r.get("rightsURI")
        if isinstance(v, str) and any(_normalize_license(v) == a for a in allow_norm):
            return True
        # Or in rights (human-readable)
        v2 = r.get("rights")
        if isinstance(v2, str):
            n = _normalize_license(v2)
            if n in allow_norm or any(a in n for a in allow_norm if a):
                return True

    return False


def harvest_datacite_prefix(prefix: str, license_allowlist: List[str], max_results: int = 1000, page_size: int = 100) -> Iterable[Dict[str, Any]]:
    """Harvest DataCite DOIs by prefix and yield records that match license allowlist.

    Note: DataCite's cursor pagination is easy to mis-use and may return empty results depending on API behavior.
    Use classic page[number]/page[size] pagination for robustness.
    """
    q = f"prefix:{prefix} AND state:findable"
    url = "https://api.datacite.org/dois"
    headers = {
        "Accept": "application/vnd.api+json",
        # a mildly descriptive UA helps avoid some edge throttling
        "User-Agent": "academictrivia-bot/1.0 (+https://github.com/codeworksforkevy/bottany)",
    }

    yielded = 0
    page = 1
    while yielded < max_results:
        params = {
            "query": q,
            "page[size]": page_size,
            "page[number]": page,
        }
        try:
            r = requests.get(url, params=params, headers=headers, timeout=30)
            r.raise_for_status()
            payload = r.json()
        except Exception:
            return

        data = payload.get("data") or []
        if not data:
            return

        for item in data:
            attrs = (item or {}).get("attributes") or {}
            # rightsList is where DataCite encodes license/rights statements
            rights_list = attrs.get("rightsList") or []
            if not rights_list:
                continue

            if not license_matches(rights_list, license_allowlist):
                continue

            yield attrs
            yielded += 1
            if yielded >= max_results:
                return

        page += 1


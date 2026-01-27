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


def harvest_datacite_prefix(
    prefix: str,
    license_allowlist: List[str],
    page_size: int = 100,
    max_results: int = 1000,
    timeout: int = 25,
) -> List[Dict[str, Any]]:
    """Harvest DataCite DOI metadata for a DOI prefix.

    Uses the public DataCite REST API.

    Returns a list of records with keys: title, description, url, year, rights_list.
    """
    out: List[Dict[str, Any]] = []
    cursor: Optional[str] = "1"  # DataCite uses cursor pagination; "1" is the first cursor.

    while cursor and len(out) < max_results:
        url = "https://api.datacite.org/dois"
        params = {
            "prefix": prefix,
            "page[size]": str(page_size),
            "page[cursor]": cursor,
        }
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        payload = r.json()

        data = payload.get("data") or []
        if not data:
            break

        for item in data:
            attrs = (item or {}).get("attributes") or {}
            rights_list = attrs.get("rightsList") or []
            if not _license_ok(rights_list, license_allowlist):
                continue

            titles = attrs.get("titles") or []
            title = None
            if titles and isinstance(titles, list):
                t0 = titles[0]
                if isinstance(t0, dict):
                    title = t0.get("title")
                elif isinstance(t0, str):
                    title = t0

            descs = attrs.get("descriptions") or []
            description = None
            if descs and isinstance(descs, list):
                d0 = descs[0]
                if isinstance(d0, dict):
                    description = d0.get("description")
                elif isinstance(d0, str):
                    description = d0

            out.append(
                {
                    "title": title,
                    "description": description,
                    "url": attrs.get("url") or attrs.get("landingPage") or attrs.get("doi"),
                    "year": attrs.get("publicationYear"),
                    "rights_list": rights_list,
                    "source": f"datacite:{prefix}",
                }
            )
            if len(out) >= max_results:
                break

        cursor = ((payload.get("links") or {}).get("next") and (payload.get("meta") or {}).get("nextCursor"))
        # DataCite sometimes supplies next cursor in meta.nextCursor; if missing, stop.
        if not cursor:
            cursor = (payload.get("meta") or {}).get("nextCursor")

    return out

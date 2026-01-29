from __future__ import annotations

import json
import re
from typing import Any, Dict, List

import aiohttp

DEFAULT_URLS = ["https://gaming.amazon.com/home"]


def _extract_cards(html: str) -> List[Dict[str, Any]]:
    """
    Best-effort extraction for Luna cards from Prime Gaming page.
    This is heuristic and may yield 0 if the page structure changes.
    """
    out: List[Dict[str, Any]] = []

    # Look for JSON-ish blobs in the HTML that mention Luna
    for m in re.finditer(r'\\{[^\\{{\\}}]{{200,}}\\}', html):
        blob = m.group(0)
        if "luna" not in blob.lower():
            continue
        try:
            data = json.loads(blob)
        except Exception:
            continue

        stack = [data]
        while stack:
            cur = stack.pop()
            if isinstance(cur, dict):
                title = cur.get("title") or cur.get("name")
                url = cur.get("url") or cur.get("href")
                if title and url and "luna" in str(url).lower():
                    if url.startswith("/"):
                        url = "https://gaming.amazon.com" + url
                    out.append({"title": str(title), "url": str(url), "kind": "subscription", "note": "Luna"})
                for v in cur.values():
                    stack.append(v)
            elif isinstance(cur, list):
                stack.extend(cur)

    # Dedup
    seen=set()
    uniq=[]
    for item in out:
        if item["url"] in seen:
            continue
        seen.add(item["url"])
        uniq.append(item)
    return uniq[:30]


async def fetch_luna_subscription_picks(luna_cfg: Dict[str, Any], timeout_s: int = 20) -> List[Dict[str, Any]]:
    urls = luna_cfg.get("urls") or DEFAULT_URLS
    out: List[Dict[str, Any]] = []
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        for url in urls:
            try:
                async with session.get(url, timeout=timeout_s) as r:
                    r.raise_for_status()
                    html = await r.text()
                out.extend(_extract_cards(html))
            except Exception:
                continue
    return out

from __future__ import annotations

from typing import Any, Dict, List

import aiohttp
from bs4 import BeautifulSoup


async def _fetch_page(session: aiohttp.ClientSession, url: str, timeout_s: int) -> str:
    async with session.get(url, timeout=timeout_s, headers={"User-Agent": "Mozilla/5.0"}) as r:
        r.raise_for_status()
        return await r.text()


def _extract_links(html: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    out: List[Dict[str, Any]] = []
    for a in soup.select("a[href]"):
        href = a.get("href") or ""
        text = (a.get_text(" ", strip=True) or "").strip()
        if not text or len(text) < 2:
            continue
        if "/game/" in href or "/en/game/" in href:
            if href.startswith("/"):
                href = "https://www.gog.com" + href
            out.append({"title": text, "url": href, "kind": "free_to_keep", "note": ""})
    # Dedup by URL
    seen=set()
    uniq=[]
    for item in out:
        if item["url"] in seen:
            continue
        seen.add(item["url"])
        uniq.append(item)
    return uniq[:30]


async def fetch_gog_offers(session: aiohttp.ClientSession, endpoints: List[str], timeout_s: int = 20) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for url in endpoints:
        try:
            html = await _fetch_page(session, url, timeout_s)
            out.extend(_extract_links(html))
        except Exception:
            continue
    # Dedup across pages
    seen=set()
    uniq=[]
    for item in out:
        if item["url"] in seen:
            continue
        seen.add(item["url"])
        uniq.append(item)
    return uniq[:30]

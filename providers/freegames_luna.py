"""
Amazon Luna auto-refresh helper.

This file is optional because freegames_logic includes a Luna scraper and caching.
Keep this provider around if you later want a dedicated cache updater job.
"""

from __future__ import annotations

import os
import json
from typing import Any, Dict, List

import aiohttp
from bs4 import BeautifulSoup


def _save_json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


async def refresh_luna_cache(urls: List[str], cache_path: str, *, timeout_s: int = 18) -> Dict[str, Any]:
    timeout = aiohttp.ClientTimeout(total=timeout_s)
    items: List[Dict[str, str]] = []
    async with aiohttp.ClientSession() as session:
        for url in urls:
            try:
                async with session.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                    if resp.status >= 400:
                        continue
                    html = await resp.text()
            except Exception:
                continue

            soup = BeautifulSoup(html, "lxml")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                txt = (a.get_text(" ", strip=True) or "").strip()
                if not txt:
                    continue
                if "/game/" in href or "/games/" in href or "/channel/" in href or "/channels/" in href:
                    if href.startswith("/"):
                        href = "https://luna.amazon.com" + href
                    items.append({"title": txt[:140], "url": href})

    # dedupe
    seen = set()
    dedup = []
    for it in items:
        k = (it["title"], it["url"])
        if k in seen:
            continue
        seen.add(k)
        dedup.append(it)

    payload = {"items": dedup, "source_urls": urls, "ts": int(__import__("time").time())}
    _save_json(cache_path, payload)
    return payload

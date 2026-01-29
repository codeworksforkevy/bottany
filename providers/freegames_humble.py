from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

DEFAULT_URLS = [
    # Humble's promo URLs change. We keep this as a best-effort scraper for visible promos/deals.
    "https://www.humblebundle.com/store",
]

def _clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

async def fetch_humble_offers(
    session: aiohttp.ClientSession,
    urls: Optional[List[str]] = None,
    timeout_s: int = 25,
) -> List[Dict[str, Any]]:
    """
    Best-effort Humble Bundle store scraper. Returns a small set of visible offers.
    We conservatively label everything as 'deal' (not 'free-to-keep') unless we detect 100% off.
    """
    urls = urls or DEFAULT_URLS
    out: List[Dict[str, Any]] = []

    for u in urls:
        try:
            async with session.get(u, timeout=timeout_s, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                if resp.status != 200:
                    continue
                html = await resp.text()
        except Exception:
            continue

        soup = BeautifulSoup(html, "lxml")

        # Find product cards/links (heuristic).
        for a in soup.find_all("a", href=True):
            href = a.get("href") or ""
            text = _clean_text(a.get_text(" "))
            if not text or len(text) < 3:
                continue
            if any(bad in href for bad in ["#", "javascript:", "mailto:", "/login", "/search"]):
                continue

            # Keep only store item links-ish
            if "/store/" not in href and "/bundle/" not in href:
                continue

            full = href if href.startswith("http") else urljoin(u, href)
            if any(x["url"] == full for x in out):
                continue

            kind = "deal"
            note = "Humble Bundle (auto-scraped). Verify final price/eligibility on page."
            out.append({"title": text, "url": full, "kind": kind, "note": note})

        if len(out) > 40:
            out = out[:40]
            break

    return out

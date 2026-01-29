from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

DEFAULT_URLS = [
    # Public page (no login) that lists curated deals for Luna. We treat these as "subscription picks / deals".
    # If Amazon changes this page, the provider will simply return an empty list (no crash).
    "https://luna.amazon.com/sale",
]

def _clean_text(s: str) -> str:
    s = re.sub(r"\s+", " ", s or "").strip()
    return s

async def fetch_luna_subscription_picks(
    session: aiohttp.ClientSession,
    urls: Optional[List[str]] = None,
    timeout_s: int = 25,
) -> List[Dict[str, Any]]:
    """
    Best-effort Amazon Luna scraper.

    Output schema:
      { "title": str, "url": str, "kind": "subscription"|"deal", "note": str }
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

        # Heuristic: look for links that look like game detail pages or store items.
        # We avoid overfitting to exact CSS classes because Amazon changes them frequently.
        anchors = soup.find_all("a", href=True)
        for a in anchors:
            href = a.get("href") or ""
            text = _clean_text(a.get_text(" "))
            if not text or len(text) < 2:
                continue

            # Prefer likely game links; skip navigation, social, etc.
            if any(bad in href for bad in ["#", "javascript:", "mailto:", "/help", "/privacy", "/terms"]):
                continue

            # If href is relative, join.
            full = href if href.startswith("http") else urljoin(u, href)

            # De-dup by URL.
            if any(x["url"] == full for x in out):
                continue

            # Very lightweight filter: keep entries that look like titles (not menu items).
            if len(text) > 80:
                continue

            out.append(
                {
                    "title": text,
                    "url": full,
                    "kind": "subscription",  # we label as subscription picks (not guaranteed 100% free-to-keep)
                    "note": "Amazon Luna (auto-scraped). Availability may require Prime/Luna+ and may rotate.",
                }
            )

        # Safety cap (avoid massive pages)
        if len(out) > 60:
            out = out[:60]
            break

    return out

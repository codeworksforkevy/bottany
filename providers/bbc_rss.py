from __future__ import annotations
from typing import Optional, Dict, Any
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

def _http_get_text(url: str, timeout: int = 12) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "BottanyWeather/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")

def fetch_bbc_rss_by_location_id(location_id: str) -> Optional[Dict[str, Any]]:
    loc = urllib.parse.quote((location_id or "").strip())
    if not loc:
        return None
    # BBC Weather RSS is documented; this endpoint is commonly used for 3-day RSS.
    url = f"https://weather-broker-cdn.api.bbci.co.uk/en/forecast/rss/3day/{loc}"
    try:
        xml_text = _http_get_text(url)
        root = ET.fromstring(xml_text)
        channel = root.find("channel")
        if channel is None:
            return None
        title = (channel.findtext("title") or "").strip()
        desc = (channel.findtext("description") or "").strip()
        items = []
        for item in channel.findall("item")[:3]:
            items.append({
                "title": (item.findtext("title") or "").strip(),
                "description": (item.findtext("description") or "").strip(),
                "pubDate": (item.findtext("pubDate") or "").strip(),
                "link": (item.findtext("link") or "").strip(),
            })
        return {"title": title, "description": desc, "items": items, "source_url": url}
    except Exception:
        return None

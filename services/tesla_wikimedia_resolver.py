from __future__ import annotations
import aiohttp
import asyncio

WIKI_API = "https://commons.wikimedia.org/w/api.php"

async def resolve_wikimedia_patent_image(patent_number: str):

    params = {
        "action": "query",
        "format": "json",
        "prop": "imageinfo",
        "generator": "search",
        "gsrsearch": f"Tesla patent {patent_number}",
        "gsrlimit": 1,
        "iiprop": "url",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(WIKI_API, params=params, timeout=8) as resp:
                if resp.status != 200:
                    return None

                data = await resp.json()

        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            info = page.get("imageinfo")
            if info:
                return info[0].get("url")

    except Exception:
        return None

    return None


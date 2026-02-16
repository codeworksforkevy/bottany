
from utils.async_http import url_exists

async def resolve_wikimedia_patent_image(patent_number: str):
    pat = patent_number.replace(",", "").strip()
    if not pat.isdigit():
        return None
    candidates = [
        f"https://commons.wikimedia.org/wiki/Special:FilePath/Tesla_patent_{pat}.png",
        f"https://commons.wikimedia.org/wiki/Special:FilePath/US{pat}.png"
    ]
    for c in candidates:
        if await url_exists(c):
            return c
    return None

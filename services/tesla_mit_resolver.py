
from utils.async_http import url_exists

def _norm(p):
    return (p or "").replace(",", "").strip()

async def resolve_mit_patent_image(patent_number: str):
    pat = _norm(patent_number)
    if not pat.isdigit():
        return None
    candidates = [
        f"https://web.mit.edu/most/Public/Tesla1/{pat}.png",
        f"https://web.mit.edu/most/Public/Tesla1/{pat}.jpg"
    ]
    for c in candidates:
        if await url_exists(c):
            return c
    return None

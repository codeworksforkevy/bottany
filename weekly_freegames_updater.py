import os
import json
import re
import calendar
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import aiohttp

# -------------------------
# Weekly Free Games Cache Updater (Official / Stable Sources)
# -------------------------
# Epic:
# - Official freeGamesPromotions endpoint (JSON).
#
# GOG:
# - Permanent free catalog: official page /en/partner/free_games
# - Limited-time giveaways: official GOG Pressroom "Press Release" posts that include "giveaway"
#
# Prime Gaming (downloadable free-to-keep):
# - Official Prime Gaming blog "Content Updates" list page -> latest monthly content update article
#
# Amazon Luna (streaming / Included with Prime):
# - Amazon Game Studios News tag page for Luna -> latest "Content Update" article (streaming; NOT free-to-keep)
#
# Output:
# - A unified list of dict entries written to weekly_freegames_cache.json

EPIC_FREE_URL = os.getenv(
    "EPIC_FREE_URL",
    "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions?locale=en-US&country=US&allowCountries=US"
)

GOG_FREE_COLLECTION_URL = os.getenv("GOG_FREE_COLLECTION_URL", "https://www.gog.com/en/partner/free_games")
GOG_PRESS_RELEASES_URL = os.getenv("GOG_PRESS_RELEASES_URL", "https://www.gog.com/pressroom/category/press-release/")

PRIME_GAMING_CONTENT_UPDATES_URL = os.getenv("PRIME_GAMING_CONTENT_UPDATES_URL", "https://primegaming.blog/all?topic=content-updates")
PRIME_GAMING_CLAIM_URL = os.getenv("PRIME_GAMING_CLAIM_URL", "https://gaming.amazon.com/home")

AGS_LUNA_TAG_URL = os.getenv("AGS_LUNA_TAG_URL", "https://www.amazongamestudios.com/en-gb/news?tag=luna")
LUNA_ENTRY_URL = os.getenv("LUNA_ENTRY_URL", "https://luna.amazon.com")

USER_AGENT = os.getenv("FREEGAMES_UA", "BottanyBot/weekly-freegames (+official sources)")

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def _atomic_write_json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

async def _fetch_text(session: aiohttp.ClientSession, url: str, timeout: int = 25) -> str:
    async with session.get(url, timeout=timeout) as resp:
        resp.raise_for_status()
        return await resp.text()

async def _fetch_json(session: aiohttp.ClientSession, url: str, timeout: int = 25) -> Any:
    async with session.get(url, timeout=timeout) as resp:
        resp.raise_for_status()
        return await resp.json()

def _strip_tags(html: str) -> str:
    html = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    html = re.sub(r"(?is)<style.*?>.*?</style>", " ", html)
    html = re.sub(r"(?is)<br\s*/?>", "\n", html)
    html = re.sub(r"(?is)</p\s*>", "\n", html)
    html = re.sub(r"(?is)</li\s*>", "\n", html)
    html = re.sub(r"(?is)<.*?>", " ", html)
    html = re.sub(r"&nbsp;", " ", html)
    html = re.sub(r"&amp;", "&", html)
    html = re.sub(r"&quot;", '"', html)
    html = re.sub(r"\s+", " ", html)
    return html.strip()

# -------------------------
# Epic extractor
# -------------------------
def _epic_extract(entries_json: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        elements = (
            (entries_json or {})
            .get("data", {})
            .get("Catalog", {})
            .get("searchStore", {})
            .get("elements", [])
        )
    except Exception:
        elements = []

    for el in elements or []:
        title = el.get("title") or el.get("productSlug") or "Unknown"
        slug = el.get("productSlug") or el.get("urlSlug") or ""
        url = f"https://store.epicgames.com/en-US/p/{slug}" if slug else el.get("url") or ""

        price = None
        free_to_keep = False
        claim_until = None

        try:
            total = (el.get("price") or {}).get("totalPrice") or {}
            discount = total.get("discountPrice")
            price = 0 if discount == 0 else (discount if isinstance(discount, int) else None)

            promos = el.get("promotions") or {}
            offers = (promos.get("promotionalOffers") or [])
            if offers and isinstance(offers, list):
                po = offers[0].get("promotionalOffers") or []
                if po and isinstance(po, list):
                    end = po[0].get("endDate")
                    if end:
                        claim_until = end

            if discount == 0 and claim_until:
                free_to_keep = True
        except Exception:
            pass

        out.append({
            "platform": "epic",
            "title": title,
            "url": url,
            "price": 0 if free_to_keep else (price if isinstance(price, int) else None),
            "free_to_keep": bool(free_to_keep),
            "claim_until": claim_until,
            "fetched_utc": _utc_now_iso(),
        })
    return out

# -------------------------
# GOG: Permanent free catalog
# -------------------------
def _gog_free_collection_extract(html: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen = set()
    for m in re.finditer(r'href="(/en/game/[^"?#]+)"', html):
        href = m.group(1)
        if href in seen:
            continue
        seen.add(href)
        url = "https://www.gog.com" + href
        window = html[m.end(): m.end() + 400]
        title = None
        t = re.search(r'title="([^"]{2,120})"', window)
        if t:
            title = t.group(1).strip()
        if not title:
            title = href.split("/")[-1].replace("_", " ").replace("-", " ").title()
        out.append({
            "platform": "gog",
            "title": title,
            "url": url,
            "price": 0,
            "free_to_keep": True,
            "claim_until": None,
            "fetched_utc": _utc_now_iso(),
        })
    return out

# -------------------------
# GOG: Limited-time giveaways via Pressroom
# -------------------------
_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
}

def _parse_gog_until(text: str, fallback_year: int) -> Optional[str]:
    m = re.search(r"until\s+([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?\s*,\s*(\d{1,2})\s*(AM|PM)\s*UTC", text, re.IGNORECASE)
    if not m:
        return None
    mon = _MONTHS.get(m.group(1).lower())
    if not mon:
        return None
    day = int(m.group(2))
    hour12 = int(m.group(3))
    ampm = m.group(4).upper()
    hour = hour12 % 12
    if ampm == "PM":
        hour += 12
    dt = datetime(fallback_year, mon, day, hour, 0, 0, tzinfo=timezone.utc)
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")

def _parse_pressroom_date(html: str) -> Optional[datetime]:
    m = re.search(r"(20\d{2})-(\d{2})-(\d{2})", html)
    if not m:
        return None
    try:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=timezone.utc)
    except Exception:
        return None

def _extract_pressroom_title(html: str) -> str:
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
    if not m:
        return "GOG giveaway"
    return _strip_tags(m.group(1))[:140] or "GOG giveaway"

def _extract_first_gog_store_link(html: str) -> Optional[str]:
    m = re.search(r'href="(https://www\.gog\.com/(?:en/)?game/[^"?#]+)"', html)
    if m:
        return m.group(1)
    m = re.search(r'href="(/en/game/[^"?#]+)"', html)
    if m:
        return "https://www.gog.com" + m.group(1)
    return None

async def _gog_pressroom_giveaways(session: aiohttp.ClientSession, max_posts: int = 12) -> List[Dict[str, Any]]:
    index_html = await _fetch_text(session, GOG_PRESS_RELEASES_URL, timeout=25)
    links = []
    for m in re.finditer(r'href="(https://www\.gog\.com/pressroom/[^"]+/)"', index_html):
        url = m.group(1)
        if url not in links:
            links.append(url)
        if len(links) >= max_posts:
            break

    out: List[Dict[str, Any]] = []
    for url in links:
        try:
            page_html = await _fetch_text(session, url, timeout=25)
            title = _extract_pressroom_title(page_html)
            if "giveaway" not in title.lower() and "giveaway" not in page_html.lower():
                continue

            published = _parse_pressroom_date(page_html)
            fallback_year = published.year if published else datetime.now(timezone.utc).year
            plain = _strip_tags(page_html)
            claim_until = _parse_gog_until(plain, fallback_year=fallback_year)

            # policy requires claim_until; skip if not found
            if not claim_until:
                continue

            store_url = _extract_first_gog_store_link(page_html) or url

            out.append({
                "platform": "gog_giveaway",
                "title": title.replace("Claim the giveaway of ", "").strip(),
                "url": store_url,
                "price": 0,
                "free_to_keep": True,
                "claim_until": claim_until,
                "fetched_utc": _utc_now_iso(),
                "source_url": url,
            })
        except Exception:
            continue
    return out

# -------------------------
# Prime Gaming: official blog "Content Updates" -> latest monthly post
# Enhanced:
# - Extract waves (Week 1 / Week 2 / Week 3 / Week 4) when the article provides weekly dates.
# - Extract per-game claim links when present (gaming.amazon.com deep links or amazon.com claim anchors).
# Fallbacks remain safe: if no per-game link is found, use PRIME_GAMING_CLAIM_URL.
# -------------------------
def _prime_find_latest_content_update_url(index_html: str) -> Optional[str]:
    # primegaming.blog lists article links; pick first that looks like "prime-gaming-<month>-content-update"
    m = re.search(r'href="(https://primegaming\.blog/prime-gaming-[^"]+content-update[^"]*)"', index_html, re.IGNORECASE)
    if m:
        return m.group(1)
    return None

def _prime_article_month_year(plain: str) -> Optional[tuple[int,int]]:
    m = re.search(r"Prime Gaming\s+([A-Za-z]+)\s+Content Update", plain, re.IGNORECASE)
    if not m:
        return None
    mon_name = m.group(1).lower()
    mon = _MONTHS.get(mon_name)
    if not mon:
        return None
    y = re.search(r"(20\d{2})-(\d{2})-(\d{2})", plain)
    year = int(y.group(1)) if y else datetime.now(timezone.utc).year
    return (mon, year)

def _prime_end_of_month_utc(month: int, year: int) -> str:
    last_day = calendar.monthrange(year, month)[1]
    dt = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")

def _prime_extract_waves_with_links(html: str) -> list[dict]:
    """Heuristic wave parser for Prime Gaming content update posts."""
    waves = []
    h = html

    header_re = re.compile(r"(Week of|Available|Starting)\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})", re.IGNORECASE)
    headers = [(mm.start(), mm.group(2), int(mm.group(3)), mm.group(1)) for mm in header_re.finditer(h)]
    if not headers:
        return []

    for i, (pos, mon_name, day, kind) in enumerate(headers):
        end = headers[i+1][0] if i+1 < len(headers) else len(h)
        chunk = h[pos:end]
        wave_label = f"Week {i+1}"

        games = []
        for am in re.finditer(r'href="(https://gaming\.amazon\.com/[^"]+)"[^>]*>([^<]{2,140})<', chunk, re.IGNORECASE):
            url = am.group(1).strip()
            title = am.group(2).strip()
            if title.lower() in {"learn more", "read more", "prime gaming", "claim"}:
                continue
            games.append({"title": title, "claim_url": url})

        if not games:
            plain = _strip_tags(chunk)
            mm = re.search(r"including\s+(.+?)\.", plain, re.IGNORECASE)
            if mm:
                blob = re.sub(r"\([^)]*\)", "", mm.group(1))
                parts = [p.strip() for p in blob.split(",") if p.strip()]
                final = []
                for p in parts:
                    if re.search(r"\s+and\s+", p, re.IGNORECASE):
                        final.extend([s.strip() for s in re.split(r"\s+and\s+", p, flags=re.IGNORECASE) if s.strip()])
                    else:
                        final.append(p)
                seen = set()
                for t in final:
                    k = t.lower()
                    if k in seen:
                        continue
                    seen.add(k)
                    games.append({"title": t, "claim_url": None})

        if games:
            waves.append({
                "wave": wave_label,
                "available_from": f"{mon_name.title()} {day}",
                "games": games
            })

    return waves

async def _prime_gaming_official(session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
    idx_html = await _fetch_text(session, PRIME_GAMING_CONTENT_UPDATES_URL, timeout=25)
    article_url = _prime_find_latest_content_update_url(idx_html)
    if not article_url:
        return []
    art_html = await _fetch_text(session, article_url, timeout=25)
    plain_all = _strip_tags(art_html)

    my = _prime_article_month_year(plain_all)
    if not my:
        return []
    month, year = my
    default_claim_until = _prime_end_of_month_utc(month, year)

    waves = _prime_extract_waves_with_links(art_html)
    out: List[Dict[str, Any]] = []

    if waves:
        for w in waves:
            wave = w.get("wave")
            available_from = w.get("available_from")
            for g in w.get("games", []):
                title = g.get("title") or "Unknown"
                claim_url = g.get("claim_url") or PRIME_GAMING_CLAIM_URL
                out.append({
                    "platform": "prime_gaming",
                    "title": title,
                    "url": claim_url,
                    "price": 0,
                    "free_to_keep": True,
                    "claim_until": default_claim_until,
                    "wave": wave,
                    "available_from": available_from,
                    "fetched_utc": _utc_now_iso(),
                    "source_url": article_url,
                })
        return out

    # Fallback: old simple extraction (single blob)
    mm = re.search(r"can claim[^.]*including\s+(.+?)\.", plain_all, re.IGNORECASE)
    if not mm:
        return []
    blob = re.sub(r"\([^)]*\)", "", mm.group(1))
    parts = [p.strip() for p in blob.split(",") if p.strip()]
    final = []
    for p in parts:
        if re.search(r"\s+and\s+", p, re.IGNORECASE):
            final.extend([s.strip() for s in re.split(r"\s+and\s+", p, flags=re.IGNORECASE) if s.strip()])
        else:
            final.append(p)
    seen = set()
    for title in final:
        key = title.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "platform": "prime_gaming",
            "title": title,
            "url": PRIME_GAMING_CLAIM_URL,
            "price": 0,
            "free_to_keep": True,
            "claim_until": default_claim_until,
            "wave": "Month batch",
            "available_from": None,
            "fetched_utc": _utc_now_iso(),
            "source_url": article_url,
        })
    return out

# -------------------------
# Amazon Luna (streaming) via Amazon Game Studios tag page
# -------------------------
def _ags_extract_article_links(tag_html: str, max_links: int = 5) -> List[str]:
    links = []
    for m in re.finditer(r'href="(\/en-[a-z]{2}\/news\/articles\/luna-[^"]+)"', tag_html, re.IGNORECASE):
        href = m.group(1)
        url = "https://www.amazongamestudios.com" + href
        if url not in links:
            links.append(url)
        if len(links) >= max_links:
            break
    return links

def _ags_parse_luna_update(html: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    plain = _strip_tags(html)

    # Pull "Now Available:" or date-prefixed entries as game titles.
    for pat in [
        r"Now Available:\s*([^\n]{2,140})",
        r"January\s+\d{1,2}:\s*([^\n]{2,140})",
        r"February\s+\d{1,2}:\s*([^\n]{2,140})",
        r"March\s+\d{1,2}:\s*([^\n]{2,140})",
        r"April\s+\d{1,2}:\s*([^\n]{2,140})",
        r"May\s+\d{1,2}:\s*([^\n]{2,140})",
        r"June\s+\d{1,2}:\s*([^\n]{2,140})",
        r"July\s+\d{1,2}:\s*([^\n]{2,140})",
        r"August\s+\d{1,2}:\s*([^\n]{2,140})",
        r"September\s+\d{1,2}:\s*([^\n]{2,140})",
        r"October\s+\d{1,2}:\s*([^\n]{2,140})",
        r"November\s+\d{1,2}:\s*([^\n]{2,140})",
        r"December\s+\d{1,2}:\s*([^\n]{2,140})",
    ]:
        for m in re.finditer(pat, plain, re.IGNORECASE):
            title = m.group(1).strip()
            if not title or any(x["title"].lower() == title.lower() for x in out):
                continue
            out.append({
                "platform": "amazon_luna_streaming",
                "title": title,
                "url": LUNA_ENTRY_URL,
                "price": None,
                "free_to_keep": False,
                "claim_until": None,
                "fetched_utc": _utc_now_iso(),
            })
    return out

async def _amazon_luna_official(session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
    tag_html = await _fetch_text(session, AGS_LUNA_TAG_URL, timeout=25)
    article_links = _ags_extract_article_links(tag_html, max_links=3)
    if not article_links:
        return []
    page_html = await _fetch_text(session, article_links[0], timeout=25)
    return _ags_parse_luna_update(page_html)

# -------------------------
# Main updater
# -------------------------
async def update_weekly_freegames_cache(cache_path: str) -> Dict[str, Any]:
    started = _utc_now_iso()
    async with aiohttp.ClientSession(headers={"User-Agent": USER_AGENT}) as session:
        epic_json = await _fetch_json(session, EPIC_FREE_URL, timeout=25)
        epic_items = _epic_extract(epic_json)

        gog_free_html = await _fetch_text(session, GOG_FREE_COLLECTION_URL, timeout=25)
        gog_free_items = _gog_free_collection_extract(gog_free_html)

        gog_giveaways = await _gog_pressroom_giveaways(session, max_posts=15)

        prime_items = await _prime_gaming_official(session)

        luna_items = await _amazon_luna_official(session)

    combined = [*epic_items, *gog_free_items, *gog_giveaways, *prime_items, *luna_items]
    combined = [x for x in combined if x.get("url")]

    _atomic_write_json(cache_path, combined)

    return {
        "ok": True,
        "started_utc": started,
        "written_utc": _utc_now_iso(),
        "cache_path": cache_path,
        "counts": {
            "epic": len(epic_items),
            "gog_free_catalog": len(gog_free_items),
            "gog_giveaways": len(gog_giveaways),
            "prime_gaming": len(prime_items),
            "amazon_luna_streaming": len(luna_items),
            "total": len(combined),
        },
        "sources": {
            "epic": EPIC_FREE_URL,
            "gog_free_collection": GOG_FREE_COLLECTION_URL,
            "gog_pressroom": GOG_PRESS_RELEASES_URL,
            "prime_gaming_content_updates": PRIME_GAMING_CONTENT_UPDATES_URL,
            "amazon_game_studios_luna_tag": AGS_LUNA_TAG_URL,
        },
    }

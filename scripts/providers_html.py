from __future__ import annotations
import re
import requests
from lxml import html
from typing import Dict, List

UA = "AcademicTriviaBot/1.1 (+https://example.invalid; contact=admin)"

def fetch(url: str, timeout_s: int = 30) -> str:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout_s)
    r.raise_for_status()
    return r.text

def _text(el) -> str:
    t = el.text_content() if el is not None else ""
    t = re.sub(r"\s+", " ", t).strip()
    return t

def crawl_links(start_url: str, link_regex: str, max_pages: int = 50) -> List[str]:
    # naive BFS limited
    seen = set()
    queue = [start_url]
    out = []
    rgx = re.compile(link_regex)
    while queue and len(out) < max_pages:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        try:
            doc = html.fromstring(fetch(url))
            doc.make_links_absolute(url)
            links = [a.get("href") for a in doc.xpath("//a[@href]")]
            for href in links:
                if not href:
                    continue
                if rgx.search(href) and href not in seen:
                    out.append(href)
                    if len(out) >= max_pages:
                        break
        except Exception:
            continue
    return out[:max_pages]

def scrape_mit_ocw_course_desc(course_url: str) -> Dict:
    doc = html.fromstring(fetch(course_url))
    doc.make_links_absolute(course_url)
    title = _text(doc.xpath("//*[self::h1][1]")[0]) if doc.xpath("//*[self::h1][1]") else ""
    # OCW has course description blocks; this is heuristic
    paras = doc.xpath("//main//p")
    desc = ""
    for p in paras[:10]:
        txt = _text(p)
        if len(txt) > 80:
            desc = txt
            break
    return {"title": title, "description": desc, "rights": "CC BY-NC-SA 4.0", "source_url": course_url}

def scrape_oyc_course_desc(course_url: str) -> Dict:
    doc = html.fromstring(fetch(course_url))
    doc.make_links_absolute(course_url)
    title = _text(doc.xpath("//*[self::h1][1]")[0]) if doc.xpath("//*[self::h1][1]") else ""
    # Yale course pages often have a course description region
    paras = doc.xpath("//main//p | //div[contains(@class,'field--name-body')]//p")
    desc = ""
    for p in paras[:12]:
        txt = _text(p)
        if len(txt) > 80:
            desc = txt
            break
    return {"title": title, "description": desc, "rights": "CC BY-NC-SA 3.0 US (most materials)", "source_url": course_url}

def scrape_see_course_desc(course_url: str) -> Dict:
    doc = html.fromstring(fetch(course_url))
    doc.make_links_absolute(course_url)
    title = _text(doc.xpath("//*[self::h1][1]")[0]) if doc.xpath("//*[self::h1][1]") else ""
    # try to detect license note on page
    body_text = _text(doc.xpath("//body")[0]) if doc.xpath("//body") else ""
    rights = "Creative Commons (SEE)"
    if "not licensed under a creative commons" in body_text.lower():
        rights = "NOT_CC"
    # description: first substantial paragraph
    paras = doc.xpath("//p")
    desc = ""
    for p in paras[:15]:
        txt = _text(p)
        if len(txt) > 80:
            desc = txt
            break
    return {"title": title, "description": desc, "rights": rights, "source_url": course_url}

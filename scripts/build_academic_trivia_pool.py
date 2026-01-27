"""Build or expand `data/academic_trivia_pool.json` from open-licensed sources.

Safe-by-default skeleton:
- Keep only if license detected and matches allowlist
- If license missing/ambiguous -> DROP
- Sentence quality filter: length + academic-ish cue words + remove boilerplate
- Deduplicate by sha256(normalized_sentence)

Extend with:
- Per-item crawling (course pages / repository items)
- Dataverse / OAI-PMH connectors
- Better sentence segmentation (spaCy)
"""

import os, re, json, hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

import requests
from bs4 import BeautifulSoup


SENT_SPLIT = re.compile(r'(?<=[.!?])\s+')
BAD_SUBSTRINGS = [
    "all rights reserved", "copyright", "terms of use", "third-party",
    "cookie", "privacy policy", "this lecture", "this course", "subscribe"
]

ACADEMIC_CUES = [
    " is ", " refers to ", " defined as ", " was ", " were ",
    " first ", " principle ", " process ", " describes ", " demonstrates "
]


def normalize(text: str) -> str:
    return " ".join(text.strip().split())


def sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def sentence_candidates(raw_text: str) -> List[str]:
    parts = SENT_SPLIT.split(raw_text)
    out: List[str] = []
    for s in parts:
        s = normalize(s)
        if len(s) < 90 or len(s) > 240:
            continue
        low = s.lower()
        if "http://" in low or "https://" in low:
            continue
        if any(b in low for b in BAD_SUBSTRINGS):
            continue
        if not any(k in low for k in ACADEMIC_CUES):
            continue
        out.append(s)
    return out


def fetch_html(url: str) -> str:
    r = requests.get(url, timeout=30, headers={"User-Agent": "AcademicTriviaBot/1.0"})
    r.raise_for_status()
    return r.text


def extract_visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text(" ", strip=True)


def detect_license(page_text: str, expected_substrings: List[str]) -> Optional[str]:
    low = page_text.lower()
    for s in expected_substrings:
        if s.lower() in low:
            return s
    return None


def load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def build_pool(data_dir: str, target_n: int = 1000) -> None:
    sources_path = os.path.join(data_dir, "academic_trivia_sources.json")
    pool_path = os.path.join(data_dir, "academic_trivia_pool.json")

    cfg = load_json(sources_path, None)
    if not cfg:
        raise RuntimeError(f"Missing sources config: {sources_path}")

    allowlist = [a.lower() for a in cfg.get("license_allowlist", [])]
    sources = cfg.get("sources", [])

    pool = load_json(pool_path, {"version": "1.0.0", "items": []})
    items: List[Dict[str, Any]] = pool.get("items", [])
    seen = set(it.get("hash") for it in items if it.get("hash"))

    for src in sources:
        if len(items) >= target_n:
            break

        stype = src.get("type")
        if stype not in ("html_list", "rss_or_html"):
            # TODO: implement dataverse/oai-pmh/repository connectors
            continue

        index_url = src["index_url"]
        org = src.get("org", "Unknown")
        expected = src.get("expected_license_substrings", [])
        license_required = bool(src.get("license_required", True))

        try:
            html = fetch_html(index_url)
            page_text = extract_visible_text(html)
        except Exception:
            continue

        lic = detect_license(page_text, expected) if expected else None
        if license_required and not lic:
            continue

        lic_norm = lic or "(unknown)"
        if license_required and not any(a in lic_norm.lower() for a in allowlist):
            continue

        for s in sentence_candidates(page_text):
            h = sha(s)
            if h in seen:
                continue
            seen.add(h)
            items.append({
                "id": f'{src["id"]}_{len(items):06d}',
                "text": s,
                "source_org": org,
                "source_title": src.get("index_url", ""),
                "source_url": src.get("index_url", ""),
                "license": lic_norm,
                "tags": [],
                "hash": h,
                "added_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")
            })
            if len(items) >= target_n:
                break

    pool["version"] = pool.get("version", "1.0.0")
    pool["items"] = items
    save_json(pool_path, pool)
    print(f"Pool size: {len(items)} -> {pool_path}")


if __name__ == "__main__":
    data_dir = os.path.abspath(os.path.join(os.getcwd(), "data"))
    build_pool(data_dir=data_dir, target_n=1000)

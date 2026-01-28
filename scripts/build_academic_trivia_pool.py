from __future__ import annotations

import argparse
import json
import os
import hashlib
from datetime import datetime, timezone
from typing import Dict, List

try:
    from tqdm import tqdm  # type: ignore
except Exception:  # pragma: no cover
    def tqdm(x, **kwargs):
        return x


from scripts._text_utils import normalize_space, pick_best_sentences, is_factual_sentence
from scripts._dedupe_utils import NearDuplicateIndex, simhash64, hamming64, approx_similarity_from_hamming
from scripts.providers_oai import harvest_oai_dc
from scripts.providers_dataverse import search_datasets, get_dataset_by_persistent_id, extract_cc0_fact
from scripts.providers_html import crawl_links, scrape_mit_ocw_course_desc, scrape_oyc_course_desc, scrape_see_course_desc
from scripts.providers_datacite import harvest_datacite_prefix

def load_json(path: str, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def license_ok(rights_text: str, allowlist: List[str], whitelist_cfg: Dict, source_declared_license_url: str | None = None) -> bool:
    rt = (rights_text or "").strip()
    low = rt.lower()

    # If source declares a license URL we trust, accept even if rights field is empty.
    if source_declared_license_url:
        for p in (whitelist_cfg.get("allowed_license_patterns") or []):
            if p.lower() in source_declared_license_url.lower():
                return True

    # Block patterns
    for b in (whitelist_cfg.get("blocked_license_patterns") or []):
        if b.lower() in low:
            return False

    # Explicit allowlist strings from config (usually URLs or "CC0")
    for a in allowlist:
        if a.lower() in low:
            return True

    # Generic CC URL signals
    if "creativecommons.org/licenses/" in low or "creativecommons.org/publicdomain/zero" in low:
        return True

    # Pattern allowlist
    for p in (whitelist_cfg.get("allowed_license_patterns") or []):
        if p.lower() in low:
            return True

    return False
def hash_sentence(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="data/academic_trivia_sources.json")
    ap.add_argument("--out", default="data/academic_trivia_pool.json")
    ap.add_argument("--target", type=int, default=1200, help="Stop once we have at least this many unique sentences.")
    ap.add_argument("--similarity", type=float, default=0.80, help="Near-duplicate similarity threshold (0-1). Higher => stricter dedupe.")
    ap.add_argument("--license_whitelist", default="data/license_whitelist.json", help="License allow/block patterns JSON.")
    ap.add_argument("--factual_only", action="store_true", help="If set, apply heuristic factual-only filter.")
    args = ap.parse_args()

    cfg = load_json(args.config, {})
    # Load license whitelist/blocklist patterns (optional)
    whitelist_cfg = load_json(args.license_whitelist, {}) if args.license_whitelist else {}

    allowlist = whitelist_cfg.get('allow', []) or cfg.get('license_allowlist', [])
    sources = cfg.get("sources", [])

    items_out: List[Dict] = []
    seen = set()
    ndx = NearDuplicateIndex()
    id_counter = 0
    # store map from internal id -> simhash for candidates
    simhash_map: Dict[str, int] = {}

    def add_from_record(text: str, source_org: str, source_title: str,
                        source_url: str, license_str: str):
        nonlocal id_counter
        text = normalize_space(text)
        if not text:
            return
        # factual-only heuristic
        if args.factual_only and (not is_factual_sentence(text)):
            return

        # Exact dedupe
        h = hash_sentence(text)
        if h in seen:
            return

        # Near-duplicate dedupe (SimHash + bucketing)
        sh = simhash64(text)
        for cand_sh, cand_id in ndx.query_candidates(sh):
            dist = hamming64(sh, cand_sh)
            sim = approx_similarity_from_hamming(dist)
            if sim >= args.similarity:
                return

        seen.add(h)
        item_id = f"s{id_counter}"
        id_counter += 1
        simhash_map[item_id] = sh
        ndx.add(sh, item_id)

        items_out.append({
            "text": text,
            "source_org": source_org,
            "source_title": source_title,
            "source_url": source_url,
            "license": license_str,
        })
    for src in sources:
        if len(items_out) >= args.target:
            break

        stype = src.get("type")
        sid = src.get("id", stype)
        print(f"==> Source: {sid} ({stype})")

        if stype == "oai_pmh":
            recs = harvest_oai_dc(
                base_url=src["base_url"],
                metadata_prefix=src.get("metadata_prefix", "oai_dc"),
                set_spec=src.get("set"),
                max_records=int(src.get("max_records", 500))
            )
            for r in tqdm(recs, desc=sid):
                rights = r.get("rights", "")
                if not license_ok(rights, allowlist, whitelist_cfg, src.get('license_url')):
                    # many repositories include rights like "© ..." — we ignore unless CC/CC0 appears
                    continue
                # Use description first; fallback to title
                text_blob = r.get("description") or ""
                if not text_blob:
                    continue
                sents = pick_best_sentences(text_blob, max_sentences=2)
                for s in sents:
                    add_from_record(
                        text=s,
                        source_org=sid,
                        source_title=r.get("title",""),
                        source_url=r.get("source_url",""),
                        license_str=rights[:120] if rights else "CC/Unknown"
                    )
                if len(items_out) >= args.target:
                    break

        elif stype == "dataverse_search":
            api_base = src["api_base"]
            q = src.get("query", "*")
            per_page = int(src.get("per_page", 100))
            max_results = int(src.get("max_results", 300))
            required = [x.lower() for x in (src.get("required_license_contains") or [])]
            hits = search_datasets(api_base, q, per_page=per_page, max_results=max_results)
            for h in tqdm(hits, desc=sid):
                pid = h.get("global_id") or h.get("globalId") or ""
                if not pid:
                    continue
                try:
                    dj = get_dataset_by_persistent_id(api_base, pid)
                    rec = extract_cc0_fact(dj)
                    rights = (rec.get("rights") or "")
                    # Harvard Dataverse default CC0; keep only if mentions CC0 in terms/license text
                    if required and not any(x in rights.lower() for x in required):
                        continue
                    text_blob = rec.get("description") or ""
                    if not text_blob:
                        continue
                    sents = pick_best_sentences(text_blob, max_sentences=2)
                    for s in sents:
                        add_from_record(
                            text=s,
                            source_org="Harvard Dataverse",
                            source_title=rec.get("title",""),
                            source_url=rec.get("source_url",""),
                            license_str="CC0 1.0 (Dataverse terms/licensing)"
                        )
                except Exception:
                    continue
                if len(items_out) >= args.target:
                    break

        elif stype == "html_course_catalog":
            # MIT OCW: we discover course pages via a broad link pattern and sample
            base_url = src.get("base_url","")
            license_str = src.get("declared_license","")
            # discovery: find course-like links (heuristic)
            start_urls = src.get("start_urls", [])
            course_links = []
            for u in start_urls:
                # OCW course URLs look like /courses/<dept>/<number>/
                links = crawl_links(u, link_regex=r"ocw\.mit\.edu/courses/[^\s\"\']+/?$", max_pages=int(src.get("max_pages", 50)))
                course_links.extend(links)

            # If MIT OCW search pages return zero links (often JS-driven), fall back to /courses/ listing.
            if (not course_links) and any("ocw.mit.edu/search" in (u or "") for u in start_urls):
                fallback_urls = [
                    "https://ocw.mit.edu/courses/",
                    "https://ocw.mit.edu/courses/?page=1",
                ]
                for u2 in fallback_urls:
                    links2 = crawl_links(u2, link_regex=r"ocw\.mit\.edu/courses/[^\s\"\']+/?$", max_pages=max(10, int(src.get("max_pages", 60))))
                    course_links.extend(links2)
            # de-dupe
            seen_links = []
            for l in course_links:
                if l not in seen_links:
                    seen_links.append(l)
            for course_url in tqdm(seen_links, desc=sid):
                try:
                    rec = scrape_mit_ocw_course_desc(course_url)
                    text_blob = rec.get("description","")
                    if not text_blob:
                        continue
                    sents = pick_best_sentences(text_blob, max_sentences=2)
                    for s in sents:
                        add_from_record(
                            text=s,
                            source_org="MIT OpenCourseWare",
                            source_title=rec.get("title",""),
                            source_url=course_url,
                            license_str=license_str or "CC BY-NC-SA 4.0"
                        )
                except Exception:
                    continue
                if len(items_out) >= args.target:
                    break

        elif stype == "html_list":
            start_urls = src.get("start_urls", [])
            license_str = src.get("declared_license","")
            max_pages = int(src.get("max_pages", 30))
            links_all = []
            for u in start_urls:
                if "oyc.yale.edu" in u:
                    links = crawl_links(u, link_regex=r"oyc\.yale\.edu/[^\s\"\']+$", max_pages=max_pages)
                elif "see.stanford.edu" in u:
                    links = crawl_links(u, link_regex=r"see\.stanford\.edu/[^\s\"\']+$", max_pages=max_pages)
                else:
                    links = []
                links_all.extend(links)

            # keep only likely course pages
            filtered = []
            for l in links_all:
                if "courses" in l or "/node/" in l or "courseinfo" in l or "CourseInfo" in l or "Course" in l:
                    filtered.append(l)
            # de-dupe
            uniq = []
            for l in filtered:
                if l not in uniq:
                    uniq.append(l)

            for page_url in tqdm(uniq, desc=sid):
                try:
                    if "oyc.yale.edu" in page_url:
                        rec = scrape_oyc_course_desc(page_url)
                        text_blob = rec.get("description","")
                        if not text_blob:
                            continue
                        sents = pick_best_sentences(text_blob, max_sentences=2)
                        for s in sents:
                            add_from_record(
                                text=s,
                                source_org="Open Yale Courses",
                                source_title=rec.get("title",""),
                                source_url=page_url,
                                license_str=license_str or "CC BY-NC-SA 3.0 US"
                            )
                    elif "see.stanford.edu" in page_url:
                        rec = scrape_see_course_desc(page_url)
                        if rec.get("rights") == "NOT_CC":
                            continue
                        text_blob = rec.get("description","")
                        if not text_blob:
                            continue
                        sents = pick_best_sentences(text_blob, max_sentences=2)
                        for s in sents:
                            add_from_record(
                                text=s,
                                source_org="Stanford Engineering Everywhere",
                                source_title=rec.get("title",""),
                                source_url=page_url,
                                license_str="Creative Commons (SEE; verify per-page)"
                            )
                except Exception:
                    continue
                if len(items_out) >= args.target:
                    break

        elif stype == "datacite_prefix":
            # Harvest DOI metadata from DataCite public API for a given prefix
            prefix = src.get("prefix")
            if not prefix:
                print("Missing 'prefix' for datacite_prefix source; skipping")
                continue
            page_size = int(src.get("page_size", 100))
            max_results = int(src.get("max_results", 1000))
            recs = harvest_datacite_prefix(
                prefix=prefix,
                license_allowlist=allowlist,
                page_size=page_size,
                max_results=max_results,
            )

            for r in tqdm(recs, desc=sid):
                text_blob = r.get("description") or r.get("title") or ""
                if not text_blob:
                    continue
                sents = pick_best_sentences(text_blob, max_sentences=2)
                for s in sents:
                    add_from_record(
                        text=s,
                        source_org=sid,
                        source_title=(r.get("title") or ""),
                        source_url=(r.get("url") or ""),
                        license_str="CC/CC0 (DataCite rightsList matched allowlist)",
                    )
                if len(items_out) >= args.target:
                    break

        else:
            print(f"Skipping unknown source type: {stype}")

    out = {
        "version": "1.1.0",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "items": items_out,
        "stats": {
            "unique_sentences": len(items_out),
            "target": args.target,
        }
    }
    save_json(args.out, out)
    print(f"Built pool: {len(items_out)} items -> {args.out}")

if __name__ == "__main__":
    main()

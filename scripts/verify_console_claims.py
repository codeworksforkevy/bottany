"""
scripts/verify_console_claims.py
==================================
innovation ve record alanlarındaki iddiaları Wikipedia'dan
gelen resmi kaynaklı ifadelerle karşılaştırır.

Yöntem:
  - Wikipedia REST API'den her konsolun makale özetini alır
  - Makale metninde "first", "record", "pioneered", "introduced",
    "million units" gibi anahtar kelimeleri içeren cümleleri çıkarır
  - Bunları bizim innovation/record metinlerimizle yan yana koyar
  - Eşleşmeyen veya desteklenmeyen iddiaları UNVERIFIED olarak işaretler

Çalıştırmak için:
    pip install requests
    python scripts/verify_console_claims.py

Çıktı:
    data/console_claims_report.json
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    raise SystemExit("pip install requests")

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
REGISTRY     = PROJECT_ROOT / "data" / "consoles_full.json"
REPORT_OUT   = PROJECT_ROOT / "data" / "console_claims_report.json"

SLEEP = 1.0

# ── Keywords that signal a notable claim ──────────────────────────────────────
CLAIM_KEYWORDS = [
    "first", "record", "pioneer", "introduc", "invent",
    "best-selling", "best selling", "million units", "million copies",
    "revolutio", "launch", "debut", "origin", "found",
    "outsold", "surpass", "exceed", "broke", "historic",
]

# ── Wikipedia article slug overrides ──────────────────────────────────────────
# When the console name doesn't map cleanly to a Wikipedia article title
SLUG_OVERRIDES = {
    "magnavox_odyssey":      "Magnavox_Odyssey",
    "fairchild_channel_f":   "Fairchild_Channel_F",
    "commodore_64":          "Commodore_64",
    "mattel_intellivision":  "Intellivision",
    "atari_2600":            "Atari_2600",
    "atari_5200":            "Atari_5200",
    "atari_7800":            "Atari_7800",
    "coleco_colecovision":   "ColecoVision",
    "nintendo_nes":          "Nintendo_Entertainment_System",
    "nintendo_snes":         "Super_Nintendo_Entertainment_System",
    "nintendo_n64":          "Nintendo_64",
    "nintendo_gamecube":     "GameCube",
    "nintendo_wii":          "Wii",
    "nintendo_wii_u":        "Wii_U",
    "nintendo_switch":       "Nintendo_Switch",
    "nintendo_switch_oled":  "Nintendo_Switch_(OLED_model)",
    "nintendo_gameboy":      "Game_Boy",
    "nintendo_gameboy_advance": "Game_Boy_Advance",
    "nintendo_ds":           "Nintendo_DS",
    "nintendo_3ds":          "Nintendo_3DS",
    "sony_ps1":              "PlayStation_(console)",
    "sony_ps2":              "PlayStation_2",
    "sony_ps3":              "PlayStation_3",
    "sony_ps4":              "PlayStation_4",
    "sony_ps5":              "PlayStation_5",
    "sony_psp":              "PlayStation_Portable",
    "sony_ps_vita":          "PlayStation_Vita",
    "microsoft_xbox":        "Xbox_(console)",
    "microsoft_xbox_360":    "Xbox_360",
    "microsoft_xbox_one":    "Xbox_One",
    "microsoft_xbox_series_x": "Xbox_Series_X",
    "microsoft_xbox_series_s": "Xbox_Series_S",
    "valve_steam_deck":      "Steam_Deck",
    "sega_master_system":    "Master_System",
    "sega_genesis":          "Sega_Genesis",
    "sega_saturn":           "Sega_Saturn",
    "sega_dreamcast":        "Dreamcast",
    "sega_game_gear":        "Game_Gear",
    "snk_neo_geo":           "Neo_Geo_(system)",
    "3do_interactive":       "3DO_Interactive_Multiplayer",
    "nec_turbografx":        "TurboGrafx-16",
    "nokia_ngage":           "N-Gage_(device)",
    "bandai_wonderswan":     "WonderSwan",
}

WIKI_SUMMARY  = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"
WIKI_SECTIONS = "https://en.wikipedia.org/api/rest_v1/page/mobile-sections/{}"
HEADERS = {"User-Agent": "Bottany-Bot/1.0 (claims verifier; github.com/bottany)"}


# ── Fetchers ──────────────────────────────────────────────────────────────────

def fetch_summary(slug: str) -> Optional[str]:
    """Return the article extract (first few paragraphs)."""
    try:
        resp = requests.get(WIKI_SUMMARY.format(slug), headers=HEADERS, timeout=12)
        if resp.status_code == 200:
            return resp.json().get("extract", "")
    except Exception as e:
        print(f"      summary fetch error: {e}")
    return None


def fetch_lead_section(slug: str) -> Optional[str]:
    """Return the lead section text (more complete than summary)."""
    try:
        resp = requests.get(WIKI_SECTIONS.format(slug), headers=HEADERS, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            lead = data.get("lead", {})
            sections = lead.get("sections", [])
            if sections:
                # Strip HTML tags
                text = sections[0].get("text", "")
                text = re.sub(r"<[^>]+>", " ", text)
                text = re.sub(r"\s+", " ", text).strip()
                return text
    except Exception as e:
        print(f"      section fetch error: {e}")
    return None


# ── Sentence extraction ────────────────────────────────────────────────────────

def extract_claim_sentences(text: str) -> list[str]:
    """Extract sentences containing claim keywords."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    found = []
    for s in sentences:
        s = s.strip()
        if len(s) < 20:
            continue
        if any(kw in s.lower() for kw in CLAIM_KEYWORDS):
            found.append(s)
    return found[:8]  # cap at 8 most relevant


# ── Claim matching ────────────────────────────────────────────────────────────

def _keywords_from(text: str) -> set[str]:
    """Extract significant words from our claim text for fuzzy matching."""
    stop = {"the", "a", "an", "is", "was", "it", "its", "of", "to",
            "in", "on", "for", "and", "or", "by", "with", "at", "be"}
    words = re.findall(r"\b[a-z]{4,}\b", text.lower())
    return {w for w in words if w not in stop}


def match_score(our_claim: str, wiki_sentences: list[str]) -> tuple[float, Optional[str]]:
    """
    Return (score, best_matching_sentence).
    Score 0.0–1.0 — fraction of our claim keywords found in Wikipedia.
    """
    if not wiki_sentences or not our_claim:
        return 0.0, None

    our_kws = _keywords_from(our_claim)
    if not our_kws:
        return 0.0, None

    best_score = 0.0
    best_sent  = None

    wiki_text = " ".join(wiki_sentences).lower()
    wiki_kws  = _keywords_from(wiki_text)

    overlap = our_kws & wiki_kws
    score   = len(overlap) / len(our_kws)

    # Also find the single best matching sentence
    for sent in wiki_sentences:
        sent_kws = _keywords_from(sent)
        s = len(our_kws & sent_kws) / len(our_kws)
        if s > best_score:
            best_score = s
            best_sent  = sent

    return score, best_sent


def verdict(score: float) -> str:
    if score >= 0.6:  return "SUPPORTED"
    if score >= 0.3:  return "PARTIAL"
    return "UNVERIFIED"


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    if not REGISTRY.exists():
        raise SystemExit(f"Registry not found: {REGISTRY}")

    with open(REGISTRY, encoding="utf-8") as f:
        registry = json.load(f)

    consoles = registry["consoles"]
    print(f"Checking innovation/record claims for {len(consoles)} consoles...\n")

    report = []

    for c in consoles:
        cid       = c.get("id", "")
        name      = c.get("name", "?")
        our_innov = c.get("innovation", "")
        our_rec   = c.get("record", "")

        slug = SLUG_OVERRIDES.get(cid, name.replace(" ", "_"))

        print(f"  {name}")
        print(f"    Fetching: {slug}")

        # Fetch Wikipedia text
        summary = fetch_summary(slug)
        time.sleep(SLEEP * 0.5)
        lead    = fetch_lead_section(slug)
        time.sleep(SLEEP)

        full_text = " ".join(filter(None, [summary, lead]))

        if not full_text:
            print(f"    Wikipedia article not found — {slug}")
            report.append({
                "id": cid, "name": name,
                "wikipedia_slug": slug,
                "article_found": False,
                "innovation": {"ours": our_innov, "verdict": "NO ARTICLE", "evidence": []},
                "record":     {"ours": our_rec,   "verdict": "NO ARTICLE", "evidence": []},
            })
            continue

        wiki_claims = extract_claim_sentences(full_text)

        # Score our claims against Wikipedia
        innov_score, innov_evidence = match_score(our_innov, wiki_claims)
        rec_score,   rec_evidence   = match_score(our_rec,   wiki_claims)

        innov_verdict = verdict(innov_score)
        rec_verdict   = verdict(rec_score)

        # Print result
        print(f"    Innovation: {innov_verdict} ({innov_score:.0%})")
        print(f"    Record:     {rec_verdict} ({rec_score:.0%})")
        if innov_verdict == "UNVERIFIED":
            print(f"    ⚠ Innovation not corroborated — check manually")
        if rec_verdict == "UNVERIFIED":
            print(f"    ⚠ Record not corroborated — check manually")

        report.append({
            "id":              cid,
            "name":            name,
            "wikipedia_slug":  slug,
            "wikipedia_url":   f"https://en.wikipedia.org/wiki/{slug}",
            "article_found":   True,
            "innovation": {
                "ours":       our_innov,
                "verdict":    innov_verdict,
                "match_pct":  round(innov_score * 100),
                "best_evidence": innov_evidence,
                "all_wiki_claims": wiki_claims,
            },
            "record": {
                "ours":       our_rec,
                "verdict":    rec_verdict,
                "match_pct":  round(rec_score * 100),
                "best_evidence": rec_evidence,
                "all_wiki_claims": wiki_claims,
            },
        })

    # Save
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_OUT, "w", encoding="utf-8") as f:
        json.dump({"generated": "2026-04-04", "consoles": report}, f,
                  indent=2, ensure_ascii=False)

    # Summary
    supported   = sum(1 for e in report if e.get("innovation", {}).get("verdict") == "SUPPORTED")
    partial     = sum(1 for e in report if e.get("innovation", {}).get("verdict") == "PARTIAL")
    unverified  = sum(1 for e in report if e.get("innovation", {}).get("verdict") == "UNVERIFIED")
    no_article  = sum(1 for e in report if not e.get("article_found"))

    print()
    print("─" * 60)
    print(f"Innovation claims:")
    print(f"  SUPPORTED   {supported}")
    print(f"  PARTIAL     {partial}")
    print(f"  UNVERIFIED  {unverified}  ← manual review needed")
    print(f"  NO ARTICLE  {no_article}")
    print()
    print(f"Report → {REPORT_OUT}")
    print()
    print("Next step: open data/console_claims_report.json")
    print("For each UNVERIFIED entry, check the wikipedia_url")
    print("and update innovation/record with a more conservative claim.")


if __name__ == "__main__":
    main()

"""
scripts/verify_consoles.py
===========================
Resmi kaynaklardan konsol verilerini doğrular.

Kullanılan kaynaklar (API key gerekmez):
  - Wikidata SPARQL API  → units_sold, release_year, manufacturer
  - Wikipedia REST API   → makale varlığı ve özet

Çalıştırmak için (proje kökünden):
    pip install requests
    python scripts/verify_consoles.py

Çıktı:
    OK   — veri eşleşiyor
    WARN — küçük fark (±15% veya ±1 yıl)
    DIFF — önemli fark, manuel kontrol gerekli
    MISS — Wikidata'da veri yok
    ✎    — innovation/record alanı — doğrulanamaz, editoryal yorum

Rapor kaydedilir:
    data/consoles_verify_report.json
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional

try:
    import requests
except ImportError:
    raise SystemExit("pip install requests")

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
REGISTRY     = PROJECT_ROOT / "data" / "consoles_full.json"
REPORT_OUT   = PROJECT_ROOT / "data" / "consoles_verify_report.json"

SLEEP        = 0.8   # Wikidata rate limit

# ── Wikidata SPARQL ────────────────────────────────────────────────────────────
SPARQL_URL = "https://query.wikidata.org/sparql"
SPARQL_HEADERS = {
    "User-Agent": "Bottany-Bot/1.0 (console verifier; contact via GitHub)",
    "Accept": "application/sparql-results+json",
}


def sparql_query(query: str) -> list[dict]:
    """Run a SPARQL query and return rows."""
    try:
        resp = requests.get(
            SPARQL_URL,
            params={"query": query, "format": "json"},
            headers=SPARQL_HEADERS,
            timeout=15,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data.get("results", {}).get("bindings", [])
    except Exception as e:
        print(f"    SPARQL error: {e}")
        return []


def search_wikidata(name: str) -> Optional[str]:
    """Return the Wikidata QID for a console name, or None."""
    query = f"""
SELECT ?item ?label WHERE {{
  ?item wdt:P31/wdt:P279* wd:Q8076.
  ?item rdfs:label ?label.
  FILTER(LANG(?label) = "en")
  FILTER(CONTAINS(LCASE(?label), LCASE("{name.replace('"', '')}")))
}}
LIMIT 3
"""
    rows = sparql_query(query)
    if rows:
        return rows[0]["item"]["value"].split("/")[-1]
    return None


def fetch_console_facts(qid: str) -> dict:
    """Fetch units sold, earliest release year, and manufacturer for a QID."""
    query = f"""
SELECT ?units ?releaseDate ?manufacturerLabel WHERE {{
  OPTIONAL {{ wd:{qid} wdt:P2664 ?units. }}
  OPTIONAL {{ wd:{qid} wdt:P577 ?releaseDate. }}
  OPTIONAL {{
    wd:{qid} wdt:P176 ?manufacturer.
    ?manufacturer rdfs:label ?manufacturerLabel.
    FILTER(LANG(?manufacturerLabel) = "en")
  }}
}}
LIMIT 5
"""
    rows = sparql_query(query)
    facts: dict = {"units": None, "release_years": set(), "manufacturers": set()}
    for row in rows:
        if "units" in row:
            try:
                facts["units"] = float(row["units"]["value"])
            except ValueError:
                pass
        if "releaseDate" in row:
            try:
                year = int(row["releaseDate"]["value"][:4])
                facts["release_years"].add(year)
            except (ValueError, IndexError):
                pass
        if "manufacturerLabel" in row:
            facts["manufacturers"].add(row["manufacturerLabel"]["value"])
    return facts


# ── Wikipedia REST ─────────────────────────────────────────────────────────────
WIKI_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"
WIKI_HEADERS = {"User-Agent": "Bottany-Bot/1.0 (console verifier)"}


def check_wikipedia(name: str) -> Optional[str]:
    """Return a one-sentence extract if the article exists, else None."""
    slug = name.replace(" ", "_")
    try:
        resp = requests.get(
            WIKI_URL.format(slug),
            headers=WIKI_HEADERS,
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("extract", "")[:200]
    except Exception:
        pass
    return None


# ── Comparison helpers ─────────────────────────────────────────────────────────

def compare_units(our: Optional[float], wiki: Optional[float]) -> str:
    """Return OK / WARN / DIFF / MISS."""
    if wiki is None:
        return "MISS"
    if our is None:
        return f"MISS (ours null, Wikidata: {wiki}M)"
    diff_pct = abs(our - wiki) / max(our, wiki) * 100
    if diff_pct <= 15:
        return f"OK  (ours {our}M, Wikidata {wiki:.1f}M, diff {diff_pct:.0f}%)"
    return f"DIFF  (ours {our}M, Wikidata {wiki:.1f}M, diff {diff_pct:.0f}%)"


def compare_year(our_releases: dict, wiki_years: set) -> str:
    if not wiki_years:
        return "MISS"
    our_years = set()
    for v in our_releases.values():
        try:
            our_years.add(int(str(v)[:4]))
        except (ValueError, TypeError):
            pass
    if not our_years:
        return "MISS (no release dates in our data)"
    wiki_min = min(wiki_years)
    our_min  = min(our_years)
    diff     = abs(our_min - wiki_min)
    if diff == 0:
        return f"OK  (earliest release: {our_min})"
    if diff <= 1:
        return f"WARN  (ours {our_min}, Wikidata {wiki_min}, diff {diff}yr)"
    return f"DIFF  (ours {our_min}, Wikidata {wiki_min}, diff {diff}yr)"


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    if not REGISTRY.exists():
        raise SystemExit(f"Registry not found: {REGISTRY}")

    with open(REGISTRY, encoding="utf-8") as f:
        registry = json.load(f)

    consoles = registry.get("consoles", [])
    print(f"Verifying {len(consoles)} consoles via Wikidata + Wikipedia...\n")
    print(f"{'Console':<40} {'Units':^20} {'Year':^20} {'Wiki article'}")
    print("─" * 100)

    report = []

    for c in consoles:
        name   = c.get("name", "?")
        our_u  = c.get("units_sold_millions")
        our_r  = c.get("release", {})
        innov  = c.get("innovation")
        rec    = c.get("record")

        # Search Wikidata
        qid = search_wikidata(name)
        time.sleep(SLEEP)

        if qid:
            facts = fetch_console_facts(qid)
            time.sleep(SLEEP)
        else:
            facts = {"units": None, "release_years": set(), "manufacturers": set()}

        units_result = compare_units(our_u, facts["units"])
        year_result  = compare_year(our_r, facts["release_years"])

        # Wikipedia article check
        wiki_extract = check_wikipedia(name)
        wiki_status  = "OK" if wiki_extract else "NOT FOUND"
        time.sleep(SLEEP * 0.5)

        # Print row
        status_char = "OK" if all(s.startswith("OK") for s in [units_result, year_result]) else "!"
        print(f"  {status_char}  {name:<38} {units_result[:20]:<20} {year_result[:20]:<20} {wiki_status}")

        entry = {
            "name":          name,
            "qid":           qid,
            "units_sold":    {"ours": our_u,  "result": units_result},
            "release_year":  {"ours": min(int(str(v)[:4]) for v in our_r.values() if v) if our_r else None,
                              "result": year_result},
            "manufacturers": list(facts["manufacturers"]),
            "wikipedia":     wiki_status,
            "innovation":    f"✎ EDITORIAL — not verifiable: {innov}" if innov else None,
            "record":        f"✎ EDITORIAL — not verifiable: {rec}"   if rec   else None,
        }
        report.append(entry)

    # Save report
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_OUT, "w", encoding="utf-8") as f:
        json.dump({"consoles": report}, f, indent=2, ensure_ascii=False)

    # Summary
    diffs = [e for e in report if "DIFF" in str(e)]
    warns = [e for e in report if "WARN" in str(e)]
    miss  = [e for e in report if "MISS" in str(e)]

    print()
    print("─" * 100)
    print(f"DIFF (manual check needed): {len(diffs)}")
    print(f"WARN (minor difference):    {len(warns)}")
    print(f"MISS (no Wikidata match):   {len(miss)}")
    print(f"\nFull report saved → {REPORT_OUT}")
    print()
    print("Note: 'innovation' and 'record' fields are marked ✎ EDITORIAL")
    print("      in the report — these are historical interpretations,")
    print("      not verifiable facts. Review them manually.")


if __name__ == "__main__":
    main()

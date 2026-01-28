from __future__ import annotations
import re
from typing import Iterable, List

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\(\[])", re.M)

def normalize_space(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s

def is_good_sentence(s: str) -> bool:
    s = normalize_space(s)
    if len(s) < 60:  # too short to be meaningful academic trivia
        return False
    if len(s) > 280: # too long for Discord embed
        return False
    # avoid obvious boilerplate
    bad = [
        "click", "cookie", "all rights reserved", "terms of use", "privacy policy",
        "creativecommons", "download", "subscribe", "log in", "sign in"
    ]
    low = s.lower()
    if any(b in low for b in bad):
        return False
    # sentence should contain some letters
    if not re.search(r"[A-Za-z]{4,}", s):
        return False
    return True



_FACTUAL_BLACKLIST = [
    "i think", "i believe", "in my opinion", "we think", "we believe",
    "you should", "we should", "should consider", "must", "let's",
    "amazing", "awesome", "wonderful", "terrible", "great!", "best", "worst",
    "join us", "sign up", "subscribe", "learn more", "click here", "watch",
]

def is_factual_sentence(s: str) -> bool:
    """
    Heuristic 'factual-only' filter for academic trivia.
    Goal: exclude opinion/marketing/CTA tone and keep definitional or historical statements.
    This is intentionally conservative.
    """
    s = normalize_space(s)
    low = s.lower()
    if any(b in low for b in _FACTUAL_BLACKLIST):
        return False
    # exclude questions / exclamations (usually not factual trivia)
    if "?" in s:
        return False
    if s.count("!") >= 1:
        return False
    # exclude first/second person pronouns (common in essays/CTAs)
    if re.search(r"\b(i|we|you|our|my|your)\b", low):
        return False
    # prefer sentences with a verb/copula or numeric/date signal
    has_copula = re.search(r"\b(is|are|was|were|refers to|defined as|consists of|includes)\b", low) is not None
    has_date_or_num = re.search(r"\b(1[6-9]\d{2}|20\d{2}|[0-9]+(\.[0-9]+)?)\b", s) is not None
    if not (has_copula or has_date_or_num):
        # allow some passive factual constructions
        if re.search(r"\b(was discovered|was developed|was proposed|was introduced|was first)\b", low) is None:
            return False
    return True


def split_sentences(text: str) -> List[str]:
    text = normalize_space(text)
    if not text:
        return []
    parts = _SENT_SPLIT.split(text)
    out = []
    for p in parts:
        p = normalize_space(p)
        if p:
            out.append(p)
    return out

def pick_best_sentences(text: str, max_sentences: int = 3) -> List[str]:
    sents = split_sentences(text)
    good = [s for s in sents if is_good_sentence(s)]
    return good[:max_sentences]

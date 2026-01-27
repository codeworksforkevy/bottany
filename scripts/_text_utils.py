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

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-']+")

def _tokenize(s: str) -> List[str]:
    return [m.group(0).lower() for m in _WORD.finditer(s or "")]

def simhash64(text: str) -> int:
    """
    Lightweight 64-bit SimHash for near-duplicate detection.
    Reference: Charikar (2002) style simhash; implemented without extra deps.
    """
    tokens = _tokenize(text)
    if not tokens:
        return 0
    v = [0] * 64
    for t in tokens:
        # stable 64-bit hash
        h = int(hashlib.blake2b(t.encode("utf-8"), digest_size=8).hexdigest(), 16)
        for i in range(64):
            bit = (h >> i) & 1
            v[i] += 1 if bit else -1
    out = 0
    for i, w in enumerate(v):
        if w > 0:
            out |= (1 << i)
    return out

def hamming64(a: int, b: int) -> int:
    return (a ^ b).bit_count()

def approx_similarity_from_hamming(dist: int) -> float:
    # similarity proxy in [0,1] where 1=identical
    return 1.0 - (dist / 64.0)

@dataclass
class NearDuplicateIndex:
    """
    Bucketing index for SimHash to avoid O(n^2).
    Splits 64-bit hash into 4 bands of 16 bits (LSH-like).
    """
    band_bits: int = 16

    def __post_init__(self) -> None:
        self._buckets: Dict[Tuple[int,int], List[Tuple[int,str]]] = {}  # (band_index, band_value)->[(simhash, id)]

    def _bands(self, h: int) -> List[Tuple[int,int]]:
        bands = []
        mask = (1 << self.band_bits) - 1
        for bi in range(64 // self.band_bits):
            bands.append((bi, (h >> (bi * self.band_bits)) & mask))
        return bands

    def add(self, h: int, item_id: str) -> None:
        for k in self._bands(h):
            self._buckets.setdefault(k, []).append((h, item_id))

    def query_candidates(self, h: int) -> Iterable[Tuple[int,str]]:
        seen = set()
        for k in self._bands(h):
            for hh, iid in self._buckets.get(k, []):
                if iid in seen:
                    continue
                seen.add(iid)
                yield hh, iid

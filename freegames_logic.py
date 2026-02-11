
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, List

import aiohttp

from freegames_epic import fetch_epic_offers


@dataclass(frozen=True)
class Offer:
    platform: str
    kind: str
    title: str
    url: str
    thumbnail: str | None = None
    expires_at: Any = None


DEFAULT_TIMEOUT_S = 18


def _load_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


async def gather_offers(registry_path: str, *, timeout_s: int = DEFAULT_TIMEOUT_S):

    reg = _load_json(registry_path, {})
    sources = (reg or {}).get("sources", {})
    epic = sources.get("epic", {})

    offers: List[Offer] = []

    async with aiohttp.ClientSession() as session:
        endpoint = epic.get("endpoint") or "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions"

        epic_raw = await fetch_epic_offers(session, endpoint, timeout_s)

        for r in epic_raw:
            offers.append(
                Offer(
                    platform=r.get("platform", "epic"),
                    kind=r.get("kind", "free_to_keep"),
                    title=r["title"],
                    url=r["url"],
                    thumbnail=r.get("thumbnail"),
                    expires_at=r.get("expires_at"),
                )
            )

    return offers

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, List

import asyncio

from services.http_client import http_client
from services.telemetry import capture_exception
from freegames_epic import fetch_epic_offers

logger = logging.getLogger("bottany.offers")

DEFAULT_TIMEOUT_S = 18


# -------------------------------------------------
# MODEL
# -------------------------------------------------

@dataclass(frozen=True)
class Offer:
    platform: str
    kind: str
    title: str
    url: str
    thumbnail: str | None = None
    expires_at: Any = None


# -------------------------------------------------
# UTIL
# -------------------------------------------------

def _load_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Failed loading registry: %s", e)
        return default


# -------------------------------------------------
# CORE
# -------------------------------------------------

async def gather_offers(registry_path: str, *, timeout_s: int = DEFAULT_TIMEOUT_S) -> List[Offer]:

    reg = _load_json(registry_path, {})
    sources = (reg or {}).get("sources", {})
    epic = sources.get("epic", {})

    endpoint = epic.get("endpoint") or \
        "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions"

    offers: List[Offer] = []

    try:
        # enforce timeout
        epic_raw = await asyncio.wait_for(
            fetch_epic_offers(
                http_client.session,
                endpoint,
                timeout_s
            ),
            timeout=timeout_s
        )

    except asyncio.TimeoutError:
        logger.warning("Epic offers fetch timeout.")
        return []

    except Exception as e:
        capture_exception(e, context="gather_offers:epic")
        return []

    for r in epic_raw or []:
        try:
            offers.append(
                Offer(
                    platform=r.get("platform", "epic"),
                    kind=r.get("kind", "free_to_keep"),
                    title=r.get("title", "Unknown title"),
                    url=r.get("url", ""),
                    thumbnail=r.get("thumbnail"),
                    expires_at=r.get("expires_at"),
                )
            )
        except Exception as e:
            capture_exception(e, context="offer_parse")

    logger.info("Gathered %s Epic offers.", len(offers))

    return offers

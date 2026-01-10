from __future__ import annotations

import os
import json
import hashlib
from typing import Any, Dict, Optional
import aiohttp

from utils.twitch_oauth import TwitchAppTokenCache
from utils.twitch_helix import get_drops_entitlements
from utils.twitch_registry import load_curated_items

def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def state_path(base_dir: str) -> str:
    return os.path.join(base_dir, "data", "twitch_badges_and_drops_state.json")

def _load_state(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {"seen_entitlement_ids": [], "curated_hash": ""}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"seen_entitlement_ids": [], "curated_hash": ""}

def _save_state(path: str, state: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

async def poll_once(
    *,
    session: aiohttp.ClientSession,
    base_dir: str,
    data_dir: str,
    announce_channel,
    client_id: str,
    client_secret: str,
    game_id: Optional[str],
    logger,
) -> None:
    """Poll both providers:
    - LIVE (Helix entitlements): announces when new entitlement IDs appear.
    - GLOBAL (curated JSON): announces when registry content hash changes.
    """
    sp = state_path(base_dir)
    state = _load_state(sp)

    # Cache token for the life of this poll_once call set; safe to re-init in caller loop too.
    token_cache = TwitchAppTokenCache()

    # --- LIVE: entitlements ---
    if client_id and client_secret:
        try:
            token = await token_cache.get(session, client_id, client_secret)
            ent = await get_drops_entitlements(
                session,
                client_id=client_id,
                bearer_token=token,
                game_id=game_id or None,
                first=50,
            )
            seen = set(state.get("seen_entitlement_ids", []) or [])
            new_ids = []
            for e in ent:
                eid = e.get("id")
                if eid and eid not in seen:
                    new_ids.append(str(eid))

            if new_ids:
                # Persist seen first to avoid spam if send fails.
                seen.update(new_ids)
                state["seen_entitlement_ids"] = sorted(seen)
                _save_state(sp, state)

                if announce_channel:
                    await announce_channel.send(
                        f"New Twitch Drops entitlements detected: {len(new_ids)} new item(s)."
                    )
        except Exception as e:
            logger.warning("Twitch LIVE poll failed: %s", e)
    else:
        logger.info("Twitch LIVE poll skipped: missing TWITCH_CLIENT_ID/SECRET")

    # --- GLOBAL: curated registry ---
    try:
        items = load_curated_items(data_dir)
        canon = json.dumps(items, ensure_ascii=False, sort_keys=True)
        h = _sha256(canon)
        prev = state.get("curated_hash", "")
        if h != prev:
            state["curated_hash"] = h
            _save_state(sp, state)
            # ignore first run (no prev)
            if prev and announce_channel:
                await announce_channel.send("Curated Twitch badges & drops registry updated.")
    except Exception as e:
        logger.warning("Curated registry poll failed: %s", e)

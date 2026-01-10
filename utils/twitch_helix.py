from __future__ import annotations
import aiohttp

async def get_drops_entitlements(
    session: aiohttp.ClientSession,
    *,
    client_id: str,
    bearer_token: str,
    game_id: str | None = None,
    first: int = 50,
) -> list[dict]:
    """Fetch Twitch Drops entitlements (authorized scope)."""
    url = "https://api.twitch.tv/helix/entitlements/drops"
    headers = {"Client-ID": client_id, "Authorization": f"Bearer {bearer_token}"}
    params = {"first": str(first)}
    if game_id:
        params["game_id"] = game_id

    async with session.get(url, headers=headers, params=params, timeout=20) as resp:
        data = await resp.json()
        if resp.status != 200:
            raise RuntimeError(f"Helix entitlements error: {resp.status} {data}")
        return data.get("data", []) or []

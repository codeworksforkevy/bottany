
import os
from services.twitch_auth import twitch_auth
from services.http_client import http_client

HELIX = "https://api.twitch.tv/helix/eventsub/subscriptions"

async def subscribe_stream_online(user_id: str):
    token = await twitch_auth.get_token()
    headers = {
        "Client-ID": twitch_auth.client_id,
        "Authorization": f"Bearer {token}"
    }

    payload = {
        "type": "stream.online",
        "version": "1",
        "condition": {"broadcaster_user_id": user_id},
        "transport": {
            "method": "webhook",
            "callback": os.getenv("TWITCH_EVENTSUB_PUBLIC_URL"),
            "secret": os.getenv("TWITCH_EVENTSUB_SECRET")
        }
    }

    await http_client.request("POST", HELIX, json=payload, headers=headers)

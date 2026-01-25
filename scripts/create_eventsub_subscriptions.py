from __future__ import annotations
import os, argparse, json, requests

TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
HELIX_BASE = "https://api.twitch.tv/helix"

def get_app_token(client_id: str, client_secret: str) -> str:
    r = requests.post(TWITCH_TOKEN_URL, data={
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    }, timeout=20)
    r.raise_for_status()
    return r.json()["access_token"]

def helix_get(headers: dict, path: str, params: dict | None=None) -> dict:
    r = requests.get(HELIX_BASE+path, headers=headers, params=params or {}, timeout=20)
    r.raise_for_status()
    return r.json()

def helix_post(headers: dict, path: str, payload: dict) -> dict:
    r = requests.post(HELIX_BASE+path, headers=headers, json=payload, timeout=20)
    # Twitch may return 202 Accepted
    if r.status_code not in (200, 202):
        raise SystemExit(f"Twitch error {r.status_code}: {r.text[:300]}")
    return r.json() if r.text else {}

def resolve_user_id(headers: dict, login: str) -> str:
    js = helix_get(headers, "/users", params={"login": login})
    data = js.get("data") or []
    if not data:
        raise SystemExit(f"Could not resolve Twitch user id for login={login}")
    return data[0]["id"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--login", required=True, help="Twitch login to subscribe (e.g., piica)")
    ap.add_argument("--types", default="stream.online,stream.offline,channel.clip.create", help="Comma-separated EventSub types")
    args = ap.parse_args()

    client_id = (os.getenv("TWITCH_CLIENT_ID","") or "").strip()
    client_secret = (os.getenv("TWITCH_CLIENT_SECRET","") or "").strip()
    secret = (os.getenv("TWITCH_EVENTSUB_SECRET","") or "").strip()
    base = (os.getenv("PUBLIC_BASE_URL","") or "").strip().rstrip("/")
    path = (os.getenv("TWITCH_EVENTSUB_PATH","/twitch/eventsub") or "/twitch/eventsub").strip()
    callback = base + (path if path.startswith("/") else ("/"+path))

    if not client_id or not client_secret:
        raise SystemExit("Missing TWITCH_CLIENT_ID / TWITCH_CLIENT_SECRET.")
    if not secret:
        raise SystemExit("Missing TWITCH_EVENTSUB_SECRET.")
    if not base.startswith("https://"):
        raise SystemExit("PUBLIC_BASE_URL must be your public HTTPS base URL (required by Twitch).")

    # Prefer user token when provided (some EventSub types require user context)
    user_token = (os.getenv("TWITCH_USER_OAUTH_TOKEN","") or "").strip()
    token = user_token or get_app_token(client_id, client_secret)

    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    broadcaster_id = resolve_user_id(headers, args.login.lower())
    types = [t.strip() for t in args.types.split(",") if t.strip()]

    created = []
    for t in types:
        condition = {"broadcaster_user_id": broadcaster_id}
        transport = {"method": "webhook", "callback": callback, "secret": secret}
        payload = {
            "type": t,
            "version": "1",
            "condition": condition,
            "transport": transport,
        }
        js = helix_post(headers, "/eventsub/subscriptions", payload)
        created.append({"type": t, "response": js})
        print(f"Requested subscription: {t}")

    os.makedirs("data", exist_ok=True)
    with open("data/eventsub_subscriptions_last.json","w",encoding="utf-8") as f:
        json.dump({"login": args.login, "callback": callback, "created": created}, f, ensure_ascii=False, indent=2)

    print("Done. Saved data/eventsub_subscriptions_last.json")
    if not user_token:
        print("Note: if Twitch rejects some types due to auth, set TWITCH_USER_OAUTH_TOKEN (user OAuth) and retry.")

if __name__ == "__main__":
    main()

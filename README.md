# Bottany (Discord bot) — packaged build

This bundle contains a deployable Discord bot focused on:
- governance/allowlist validation for registries
- Twitch automation:
  - **Badges watcher** (official Helix API) that posts **embedded thumbnails** (fixes “download link only” behavior)
  - **EventSub webhook** server for:
    - `stream.online` / `stream.offline` notifications
    - `channel.clip.create` notifications + clip logging
  - curated **/twitch drops** registry command
- Met Office **DataPoint** weather (official) via `/weather metoffice_site` and cache-based `/weather metoffice_find`
- hybrid `/help` (auto-discovery + curated overrides)

## Quick start (local)

1) Create a `.env` (or Railway variables) with:

- `DISCORD_TOKEN` (required)
- `DEV_GUILD_ID` (optional, for faster command sync while testing)
- `TZ_NAME` (default: Europe/Luxembourg)

Twitch (optional, for badges + EventSub scripts):
- `TWITCH_CLIENT_ID`
- `TWITCH_CLIENT_SECRET`
- `TWITCH_EVENTSUB_SECRET` (required to validate webhook signatures)
- `PUBLIC_BASE_URL` (your public HTTPS base, e.g. `https://your-app.up.railway.app`)
- `TWITCH_EVENTSUB_PORT` (default 8090) and `TWITCH_EVENTSUB_PATH` (default `/twitch/eventsub`)

Met Office (optional):
- `METOFFICE_API_KEY`

2) Install and run:

```bash
pip install -r requirements.txt
python main.py
```

## Twitch: how live notifications work

There are two pieces:

1) In Discord, set a posting channel and watch list:
- `/admin setchannel topic:twitch channel:#your-channel`
- `/twitch watch twitch_login:piica channel:#your-channel`

2) Create EventSub subscriptions that point to your callback:
- Railway exposes **one** public port. This bundle runs:
  - Healthcheck on `$PORT` (Railway-provided)
  - EventSub webhook on `TWITCH_EVENTSUB_PORT` (default 8090)

Recommended for Railway:
- Run EventSub **on the same `$PORT`** as the healthcheck by setting:
  - `TWITCH_EVENTSUB_PORT=$PORT`
  - and ensure the path does not collide; default `/twitch/eventsub` is fine.

Then use:
```bash
python scripts/create_eventsub_subscriptions.py --login piica
```

The script supports both app tokens and user tokens (if you provide `TWITCH_USER_OAUTH_TOKEN`).

## Met Office sites cache

To search by city name (`/weather metoffice_find`), generate a local cache:

```bash
python scripts/update_metoffice_sites_cache.py
```

This writes `data/metoffice_sites_cache.json`.

## Files of interest

- `main.py` — bot entrypoint
- `commands/twitch_badges_watch.py` — badge polling + embedded thumbnails
- `commands/twitch_eventsub.py` — webhook listener (challenge + signature verification)
- `commands/weather_metoffice.py` — DataPoint forecast
- `commands/help.py` — hybrid help system
- `data/*.json` — registries (seeded with minimal examples)


# Bottany Patch Pack (2026-01-30)

This zip contains:

1) commands/gaming_news.py
   - Fixes Discord embed field overflow (<=1024 chars)
   - Adds:
     - /gamingnews compact:bool
     - /gamingnews sources:"ign,polygon,..."
     - Pagination (Prev/Next buttons) for multi-page results
   - Optional data/news_registry.json keys:
     - page_size (3..10): items per page shown
     - fetch_size (5..50): items fetched from NewsAPI

2) commands/twitch_badges.py
   - Provides a top-level /badges command to avoid:
       CommandNotFound: Application command 'badges' not found
   - Uses official Twitch Helix endpoint for global chat badges.

## How to apply

A) Copy files into your repo:
   - Replace: commands/gaming_news.py
   - Add:     commands/twitch_badges.py

B) In main.py (or your registrar), ensure you import and register them BEFORE tree.sync():
   - from commands.gaming_news import register_gaming_news
   - from commands.twitch_badges import register_twitch_badges

   Then call:
   - register_gaming_news(client, tree, DATA_DIR)
   - register_twitch_badges(client, tree)

C) Railway variables:
   - DISCORD_TOKEN=...
   - NEWSAPI_KEY=...
   - TWITCH_CLIENT_ID=...
   - TWITCH_OAUTH_TOKEN=...

D) Re-deploy, then re-sync commands once (your existing sync command or on_ready sync).

## Notes on the badges error

If Discord still routes /badges interactions but your code doesn't have it, you’ll see CommandNotFound.
That usually happens when:
  - the bot process started without registering the command (import/register missing), OR
  - tree.sync wasn't called after adding the command, OR
  - you changed from guild sync to global sync and the server still has an old command definition.

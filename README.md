# AcademicTrivia Discord Bot

A minimal Discord bot that provides **/academictrivia daily** (deterministic daily rotation) and **/academictrivia random**
from an **open-licensed** academic sentence pool.

## Features
- `/academictrivia daily` — same sentence for everyone each UTC day
- `/academictrivia random` — random sentence
- Pool file: `data/academic_trivia_pool.json` (target 1000+ unique one-sentence facts)
- Builder script (skeleton): `scripts/build_academic_trivia_pool.py` (ingest + license whitelist + quality filter + dedupe)

> This repo ships with an empty pool. You must build/fill the pool before the command becomes useful.

## Setup

### 1) Create a Discord application & bot
- Create an app in the Discord Developer Portal
- Add a bot user
- Copy the bot token

### 2) Configure environment variables
Create a `.env` file (or set variables on your host):

```
DISCORD_TOKEN=YOUR_TOKEN_HERE
DATA_DIR=./data
TZ_NAME=UTC
```

### 3) Install and run
```
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

### 4) Build the pool (optional but recommended)
The builder script is a **safe-by-default skeleton**:
- It only keeps sentences when it detects a license string that matches the allowlist.
- If license info is missing, it drops the page.

Run:
```
python scripts/build_academic_trivia_pool.py
```

Then verify `data/academic_trivia_pool.json` contains >= 1000 items.

## Licensing note
Only ingest content where each item/page clearly exposes an open license (e.g., Creative Commons).
If license is missing/ambiguous, do not ingest.

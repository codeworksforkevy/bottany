# Gaming + Art Culture Hub Bot 

## What’s new in this version
- Prestigious English dictionaries registry + definition command:
  - /dictionaries
  - /define phrase:"what's the meaning of <word>"
- Daily academic trivia (1 per day) with reference link:
  - /trivia setchannel (admin)
  - /trivia now
  - /trivia sources
  - Background daily post at 09:00 Europe/Istanbul to the configured #trivia channel

## Railway variables

## Local run
pip install -r requirements.txt
export DISCORD_TOKEN="..."
python main.py

- Added dictionaries: Longman (LDOCE), Macmillan.

## Weather (official sources)
- /weather country:BE city:Brussels
- Uses official NMHS links (e.g., RMI Belgium) and WMO WWIS directory.

## Added in v2.4 (Academic+)
- /define_word word:<word> — direct definition (no phrase needed)
- /define_compare word:<word> — UK vs US comparison card
- Dictionary features explicitly include IPA + audio (via official pages)
- Academic-only policy preserved (no scraping)

## Added in v2.5 (Academic Extended)
- /define_etymology word:<word> — historical origin (OED, Merriam-Webster)
- /define_usage word:<word> — usage examples & synonyms (Oxford, Cambridge, Merriam-Webster)
- /define_pronunciation word:<word> — IPA & audio via official pages

### Further recommendations
- Add /word_of_the_day (academic dictionaries only)
- Add /etymology_timeline (OED-guided, link-based)
- Add /academic_random_fact (drawn from peer-reviewed or museum sources)

## Added in v2.6 (Academic Elite)
A full academic-only command suite under **/academic** (link-first, no scraping):
- /academic concept_map
- /academic timeline
- /academic institution_compare
- /academic academic_sources
- /academic museum_archive
- /academic reading_path
- /academic glossary
- /academic citation_helper
- /academic open_access
- /academic academic_ethics
- /academic methodology_guide
- /academic discipline_bridge
- /academic canonical_texts
- /academic primary_secondary
- /academic academic_debate
- /academic theory_origin
- /academic research_gap
- /academic academic_vocabulary
- /academic digital_archive_map
- /academic academic_skill

Data file: data/academic_registry.json (edit to expand topic coverage).

## Added in v2.7 (Academic Fashion)
- /fashion — free academic/institutional fashion resources (museum collections, university guides, official journal pages)
Data file: data/fashion_registry.json

## Added in v2.8 (All)
- /fashion country:<CODE> — country filter
- /settings enable|disable|status — per-server module toggles
- Registry expansions (fashion + academic modules)

# v3.0 — Quality & Governance
## What’s new
- Domain allowlists + registry validation (academic-only enforcement) via data/governance_config.json
- Runtime governance report: /governance status | /governance report | /governance validate
- Academic embeds always include an “Academic references (official)” field; missing refs are flagged.

## Governance configuration
Edit data/governance_config.json:
- allowlists: domain lists per module
- rules.require_reference_field: require refs[] for academic modules
- rules.max_report_items: limit report size
- rules.block_on_violation: if true, you may choose to stop bot startup (advanced)


# v3.1 — Hard-fail Governance + Admin Registry Updates
## Changes
- Governance hard-fail enabled (block_on_violation=true) in data/governance_config.json
  - If violations exist, bot startup is blocked until registries are fixed.
- Expanded allowlists for TR/BE/UK/JP/SE/US/FR plus academic infrastructure domains.
- Admin-only registry update commands (validated against allowlists):
  - /registry add_fashion_source name:<...> url:<...> country:<...> notes:<...>
  - /registry add_academic_ref group:<...> name:<...> url:<...>
  - /registry validate

## Operational note
If startup is blocked due to violations, fix registries locally (or allowlist) and redeploy.

# v3.2 — Policy Tightening (Institutional vs Publisher Separation)
## What changed
- Governance allowlists are now split into:
  - allowlists.academic_institutional (universities, museums, libraries, official institutions)
  - allowlists.publishers (journal platforms / academic presses / publisher infrastructure)
- Publisher domains require explicit typing:
  - type must be one of: publisher | journal_platform | press
- /registry add_academic_ref now accepts kind:<institutional|publisher|journal_platform|press> and validates accordingly.
- Hard-fail governance remains enabled: violations block startup.

Files:
- data/governance_config.json
- data/academic_registry.json (publisher links tagged)


## Public Mode
All interaction responses are public (ephemeral disabled everywhere).


## Tesla command
- `/tesla random` — one Tesla invention/patent per call (catalog caches up to 150 items).
- `/tesla sources` — institutional sources used.


## Da Vinci command
- `/davinci list category:<all|machine|drawing|manuscript|painting> page:<n>` — paginated registry items.
- `/davinci random category:<...>` — one item per call.
- `/davinci sources` — official/institutional sources.


## Philosophy command
- `/philosophy game_theory` — John Nash and game theory (pure theory), with academic references.


## Music companion (ToS-safe)
- `/music recommend query:<...>` — official platform search links (no streaming).
- `/music playlist mood:<focus|soft|gaming>` — official playlist links.
- `/music nowplaying url:<...>` — share a Spotify/YouTube/Apple Music link.
- `/music join` — joins your voice channel (no playback).
- `/music leave` — leaves voice.


## Weather (official)
- `/weather official country:<CODE>` — links to official national meteorological services.
- `/weather forecast lat:<..> lon:<..>` — official forecast via MET Norway API (by coordinates).


## Free games (official sources)
- `/freegames now` — official free-games pages (buttons) and best-effort Epic promotion titles.


## Awards (official)
- `/awards tga year:<YYYY> category:<...>` — lookup winners from registry (starter: Game of the Year).
- `/awards sources` — official award sources.


### Awards upgrades
- `/awards lookup award:<tga|bafta|dice|gja> year:<YYYY> category:<...> genre:<optional>` — registry search.
- `/awards list award:<...> year:<optional> page:<n>` — paginated entries.


### Scheduled free games announcements
- `/freegames set_channel channel:<#channel>` (Manage Server) — sets the weekly announcement channel.
- A weekly job posts an update in the configured channel.


### Healthcheck
- HTTP server listens on Railway `PORT` and serves `/health`.


## Awards full coverage
- `/awards categories award:<tga|bafta|dice|gja>` — official sources and known category slugs.
- `/awards sync award:<bafta|dice|gja> param:<...> force:<true|false>` — sync official pages into local cache (Manage Server).

This expands coverage without shipping a huge static dataset.


## Free games weekly diff
Weekly free-games post is skipped if the official payload has not changed since last run (per channel).


### Awards batch sync
- `/awards sync_batch award:bafta bafta_all:true force:false`
- `/awards sync_batch award:gja start:2023 end:2025 force:false`
- `/awards lookup ... bafta_slug:<slug>` (BAFTA cache fallback)


### Awards sync-all + autosync
- `/awards sync_all gja_years_back:2 sleep_seconds:2 force:false` — syncs DICE hub, all known BAFTA slugs, and recent GJA years.
- `/awards autosync enabled:true gja_years_back:2 sleep_seconds:2 bafta_slug_limit:25` — enables weekly autosync (default off).


## New commands (v4.3)
- `/art painter` — one major painter + one artwork image (Met API seed).
- `/anime history` — source-based overview with short excerpts + links.
- `/anime award_winner kind:any|anime|cartoon` — one award-winning animated film with official source link.
- `/anime techniques_anime` — anime production techniques.
- `/anime techniques_cartoon` — cartoon techniques (cel/stop-motion/cut-out).
- `/anime tools_random` — one technique + one traditional tool.
- `/food chocolate_europe_history` — short European chocolate history with sources.
- `/food michelin_star_meaning` — what Michelin Stars mean (official Michelin Guide).


## Restaurants commands (v4.4)
- `/restaurants michelin_starred` — one starred restaurant (seed) + official Michelin Guide link.
- `/restaurants michelin_find query:<city/country>` — official Michelin Guide entry point.
- `/restaurants award_winner year:<0|YYYY> award:<optional>` — one non-Michelin award item by year.

## Anime history (quotes)
- `/anime history` — short direct quotes with authoritative links (copyright-safe).


## Animation awards registry
The bot ships with an expandable registry at `data/animation_awards_registry.json` populated from official organizers (Oscars database, Annie Awards, Annecy Festival). Edit JSON to add more titles.


## Anime awards upgrades (v4.6)
- `/anime award_winner kind:any|anime|cartoon award:any|oscars|annie|annecy year:0|YYYY`
- `/anime awards_stats` — counts by award/type/decade
- `/anime international_award_winner year:0|YYYY award:<optional>` — separate international film-awards track (registry-driven)


## International animation awards (v4.7)
- Populated `data/animation_international_awards_registry.json` with BAFTA + Cannes + Berlinale official entries.
- Governance allowlist category `animation` added to restrict links.

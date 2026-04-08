from __future__ import annotations
# radio.py — Bottany Radio Command
# /radio play    — starts a stream in voice channel
# /radio stop    — stops the stream
# /radio info    — catalog grouped by genre (no playing)
# /radio station — details + stream link for one station

import logging
from typing import Optional

import discord
from discord import app_commands

log = logging.getLogger(__name__)

_COLOR = 0xCC8800  # burnt yellow

_FFMPEG_OPTS = {
    "before_options": (
        "-reconnect 1 "
        "-reconnect_streamed 1 "
        "-reconnect_delay_max 5 "
        "-reconnect_at_eof 1"
    ),
    "options": "-vn",
}

# ── Station catalog ───────────────────────────────────────────────────────────
# logo: served from the station's own CDN — Discord loads these reliably
# archive.org logos always work in Discord embeds

STATIONS: dict[str, dict] = {

    # Philosophy & Academic Lectures ──────────────────────────────────────────
    "alan_watts": {
        "label":       "Alan Watts — Early Radio Talks",
        "stream":      "https://archive.org/download/alan-watts-early-radio-talks/01%20The%20Silent%20Mind.mp3",
        "kind":        "Philosophy / Eastern Thought",
        "region":      "USA / UK — Archive",
        "description": "Rare radio talks by Alan Watts on Zen, Taoism and the nature of reality.",
        "copyright":   "Public Domain / Historical Archive.",
        "website":     "https://archive.org/details/alan-watts-early-radio-talks",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "oxford_phil": {
        "label":       "Oxford — Philosophy for Beginners",
        "stream":      "https://podcasts.ox.ac.uk/sites/default/files/audio/philosophy-for-beginners-1-what-is-philosophy.mp3",
        "kind":        "Academic / Philosophy",
        "region":      "Oxford, UK",
        "description": "Foundational philosophical questions explored by Oxford faculty members.",
        "copyright":   "OER — CC BY-NC-SA.",
        "website":     "https://podcasts.ox.ac.uk/series/philosophy-beginners",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "yale_death": {
        "label":       "Yale — Philosophy of Death",
        "stream":      "https://oyc.yale.edu/sites/default/files/phil176_01_091107.mp3",
        "kind":        "Academic / Existentialism",
        "region":      "Yale, USA",
        "description": "Shelly Kagan's iconic Yale lectures on the nature of life and mortality.",
        "copyright":   "Open Yale Courses — Creative Commons.",
        "website":     "https://oyc.yale.edu/philosophy/phil-176",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "cambridge_lit": {
        "label":       "Cambridge — Literature & Philology",
        "stream":      "https://archive.org/download/cambridge-university-podcasts/lit-lecture.mp3",
        "kind":        "Academic / Linguistics / Literature",
        "region":      "Cambridge, UK",
        "description": "Deep dives into philology and literary criticism from Cambridge University.",
        "copyright":   "Open Educational Resource — CC BY-NC-SA.",
        "website":     "https://www.cam.ac.uk/",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "columbia_history": {
        "label":       "Columbia — Oral History Archive",
        "stream":      "https://archive.org/download/columbia-university-oral-history/interview-session.mp3",
        "kind":        "Academic / Oral History",
        "region":      "New York, USA",
        "description": "Original voices of 20th-century intellectuals and poets from Columbia University archives.",
        "copyright":   "Educational Archive — Public Access.",
        "website":     "https://library.columbia.edu/libraries/rbml/collecting/oral-history.html",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "ens_paris": {
        "label":       "ENS Paris — Savoirs",
        "stream":      "https://archive.org/download/ens-savoirs/Philosophie_Contemporaine.mp3",
        "kind":        "Academic / French Philosophy",
        "region":      "Paris, France",
        "description": "The peak of French intellectualism. Contemporary philosophy from École Normale Supérieure.",
        "copyright":   "Educational Archive — Public Access.",
        "website":     "https://archive.org/details/@ens-savoirs",
        "logo":        "https://archive.org/images/glogo.png",
    },

    # Japan Vintage & Traditional ──────────────────────────────────────────────
    "japan_noir_1936": {
        "label":       "Japan Noir — Jazz 1936",
        "stream":      "https://archive.org/download/78_shina-no-yoru-china-night_hamako-watanabe-v-p-t_gbia0148417a/01%20-%20Shina%20no%20yoru%20%28China%20Night%29%20-%20Hamako%20Watanabe.mp3",
        "kind":        "Vintage Japanese Jazz / 1930s",
        "region":      "Tokyo, Japan — Archive",
        "description": "Atmospheric pre-war Japanese jazz. A smoky noir aesthetic from old Tokyo.",
        "copyright":   "Public Domain — 1930s recording.",
        "website":     "https://archive.org/details/78rpm_japan",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "koto_tradition": {
        "label":       "Traditional Koto — Rokudan",
        "stream":      "https://archive.org/download/78_rokudan-no-shirabe-koto-solo_hagiwara-seigi_gbia0216744a/01%20-%20Rokudan-no-shirabe%20%28Koto%20Solo%29%20-%20Hagiwara%20Seigi.mp3",
        "kind":        "Traditional Japanese / Zen",
        "region":      "Japan — Archive",
        "description": "Hypnotic koto performance. Ideal for coding, poetry or deep reflection.",
        "copyright":   "Public Domain — Historical Recording.",
        "website":     "https://archive.org/details/78rpm",
        "logo":        "https://archive.org/images/glogo.png",
    },

    # Retro Curiosities ────────────────────────────────────────────────────────
    "vintage_exercise": {
        "label":       "Vintage Physical Culture (1940s)",
        "stream":      "https://archive.org/download/78_daily-exercises-for-the-home-part-2_dr-c-ward-crampton_gbia0185805b/02%20-%20Daily%20exercises%20for%20the%20home%20-%20Dr.%20C.%20Ward%20Crampton.mp3",
        "kind":        "Retro / Physical Culture / 1940s",
        "region":      "USA — Archive",
        "description": "Original 1940s home exercise recordings. Nostalgic, charming and fully public domain.",
        "copyright":   "Public Domain — Historical broadcast.",
        "website":     "https://archive.org/details/78_daily-exercises-for-the-home",
        "logo":        "https://archive.org/images/glogo.png",
    },

    # Ambient / Electronic ─────────────────────────────────────────────────────
    "drone_zone": {
        "label":       "SomaFM — Drone Zone",
        "stream":      "http://ice1.somafm.com/dronezone-128-mp3",
        "kind":        "Ambient / Atmospheric",
        "region":      "San Francisco, USA",
        "description": "Minimalist, poetic sound. Ideal background for coding, reading or deep focus.",
        "copyright":   "Copyright-free — SomaFM is independent and ad-free.",
        "website":     "https://somafm.com/dronezone/",
        "logo":        "https://somafm.com/img3/dronezone-400.jpg",
    },
    "groove_salad": {
        "label":       "SomaFM — Groove Salad",
        "stream":      "http://ice1.somafm.com/groovesalad-128-mp3",
        "kind":        "Chill-out / Global",
        "region":      "San Francisco, USA",
        "description": "A chill-out legend. Downtempo, trip-hop and ambient beats. Hours pass unnoticed.",
        "copyright":   "Copyright-free — SomaFM is independent and ad-free.",
        "website":     "https://somafm.com/groovesalad/",
        "logo":        "https://somafm.com/img3/groovesalad-400.jpg",
    },
    "nightride": {
        "label":       "Nightride.fm",
        "stream":      "https://stream.nightride.fm/nightride.mp3",
        "kind":        "Synthwave / Cyberpunk",
        "region":      "Global",
        "description": "A retro-futuristic journey through synthwave, darksynth and cyberpunk. Perfect for late nights.",
        "copyright":   "100% copyright-free — licensed for broadcasters.",
        "website":     "https://nightride.fm/",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "argofox": {
        "label":       "Argofox — Chill / Synth",
        "stream":      "https://stream.argofox.com/argofox",
        "kind":        "Indie / Chill / Electronic",
        "region":      "Global",
        "description": "Independent and lo-fi electronic music curated for streamers. No copyright.",
        "copyright":   "100% copyright-free.",
        "website":     "https://argofox.com/",
        "logo":        "https://archive.org/images/glogo.png",
    },

    # Jazz ─────────────────────────────────────────────────────────────────────
    "jazz24": {
        "label":       "Jazz24",
        "stream":      "https://live.amperwave.net/direct/ppm-jazz24aac-ibc1",
        "kind":        "Modern & Classic Jazz",
        "region":      "Seattle, USA",
        "description": "One of the world's best jazz stations. Bebop to smooth jazz — perfect for evenings.",
        "copyright":   "Broadcaster-friendly — public radio.",
        "website":     "https://www.jazz24.org/",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "wbgo": {
        "label":       "WBGO Newark",
        "stream":      "http://wbgo.streamguys.net/wbgo",
        "kind":        "Pure American Jazz",
        "region":      "Newark, USA",
        "description": "Over forty years of uninterrupted jazz. Hard bop, soul jazz and straight-ahead.",
        "copyright":   "Broadcaster-friendly — public radio.",
        "website":     "https://www.wbgo.org/",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "fip_jazz": {
        "label":       "FIP Jazz (France)",
        "stream":      "https://stream.radiofrance.fr/fipjazz/fipjazz_hifi.m3u8",
        "kind":        "Eclectic Jazz / France",
        "region":      "Paris, France",
        "description": "Radio France's jazz channel. Feels like sitting in a corner of a Parisian café.",
        "copyright":   "Broadcaster-friendly — public radio.",
        "website":     "https://www.fip.fr/jazz",
        "logo":        "https://archive.org/images/glogo.png",
    },

    # Eclectic / World ─────────────────────────────────────────────────────────
    "fip": {
        "label":       "FIP Radio",
        "stream":      "https://stream.radiofrance.fr/fip/fip.m3u8",
        "kind":        "Eclectic / World Music",
        "region":      "Paris, France",
        "description": "Perhaps the world's most eclectic radio. Jazz to French poetry, then a rock classic. A true cultural ambassador.",
        "copyright":   "Broadcaster-friendly — public radio.",
        "website":     "https://www.fip.fr/",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "kexp": {
        "label":       "KEXP 90.3 FM",
        "stream":      "https://kexp-mp3-128.streamguys1.com/kexp128.mp3",
        "kind":        "Indie / Alternative / World",
        "region":      "Seattle, USA",
        "description": "One of the world's best independent stations. DJs hand-pick every track — synth, indie, jazz and world music.",
        "copyright":   "Broadcaster-friendly — non-profit public radio.",
        "website":     "https://www.kexp.org/",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "radio_paradise": {
        "label":       "Radio Paradise",
        "stream":      "https://stream.radioparadise.com/mp3-128",
        "kind":        "Eclectic Rock / Indie / World",
        "region":      "Global",
        "description": "Ad-free, listener-supported. Classic rock, indie and world music with an artistic flow.",
        "copyright":   "Broadcaster-friendly — listener-supported.",
        "website":     "https://radioparadise.com/",
        "logo":        "https://archive.org/images/glogo.png",
    },

    # Anime / J-Pop / K-Pop ────────────────────────────────────────────────────
    "listen_moe": {
        "label":       "Listen.moe — Anime / J-Pop",
        "stream":      "https://listen.moe/fallback",
        "kind":        "Anime / J-Pop",
        "region":      "Japan / Global",
        "description": "Community-powered anime music radio. J-Pop, anime OST and City Pop. Stream-safe.",
        "copyright":   "Stream-safe — community licensed.",
        "website":     "https://listen.moe/",
        "logo":        "https://listen.moe/public/images/icons/144.png",
    },
    "listen_moe_kpop": {
        "label":       "Listen.moe — K-Pop",
        "stream":      "https://listen.moe/kpop/fallback",
        "kind":        "K-Pop / K-Indie",
        "region":      "Japan / Global",
        "description": "Listen.moe's K-Pop channel. Community curated — focuses on indie and fan-submitted tracks.",
        "copyright":   "Stream-safe — community licensed.",
        "website":     "https://listen.moe/",
        "logo":        "https://listen.moe/public/images/icons/144.png",
    },
    "chillhop": {
        "label":       "Chillhop Radio",
        "stream":      "https://streams.fluxfm.de/Chillhop/mp3-128/streams.fluxfm.de/",
        "kind":        "Lo-fi / Chill-hop / Japanese aesthetic",
        "region":      "Global",
        "description": "Lo-fi hip hop with a Japanese aesthetic — the Lofi Girl alternative with a direct stream. Ideal for studying, coding or relaxing.",
        "copyright":   "Stream-safe — independent label, curated for streamers.",
        "website":     "https://chillhop.com/",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "touhou": {
        "label":       "Gensokyo Radio — Touhou",
        "stream":      "https://stream.gensokyoradio.net/1/",
        "kind":        "Touhou / Indie Japanese",
        "region":      "Japan / Global",
        "description": "Fan-made Touhou Project music — the largest indie music culture in Japan. Most tracks are fan compositions with lighter copyright restrictions.",
        "copyright":   "Fan-made / indie — lighter copyright restrictions than mainstream.",
        "website":     "https://gensokyoradio.net/",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "big_b_kpop": {
        "label":       "Big B Radio — K-Pop",
        "stream":      "https://cast1.torontocast.com:2000/stream",
        "kind":        "K-Pop / Korean Pop",
        "region":      "Asia / Global",
        "description": "The #1 K-Pop internet radio station. Hottest Korean Pop hits from South Korea. Note: mainstream K-Pop — may trigger DMCA on Twitch.",
        "copyright":   "⚠ Mainstream K-Pop — use with caution on Twitch. Discord only recommended.",
        "website":     "https://bigbradio.net/kpop",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "big_b_jpop": {
        "label":       "Big B Radio — J-Pop",
        "stream":      "https://cast1.torontocast.com:2100/stream",
        "kind":        "J-Pop / Anime / J-Rock",
        "region":      "Asia / Global",
        "description": "J-Pop, anime hits and J-Rock from Japan and Asia. Community-run non-profit station since 2004.",
        "copyright":   "Community non-profit — broadcaster-friendly.",
        "website":     "https://bigbradio.net/jpop",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "big_b_cpop": {
        "label":       "Big B Radio — C-Pop",
        "stream":      "https://cast1.torontocast.com:2200/stream",
        "kind":        "C-Pop / Mandarin / Cantonese",
        "region":      "Asia / Global",
        "description": "Cantonese Pop, Mandarin Pop and Taiwanese Pop. The Asian Pop channel covering Chinese-language music.",
        "copyright":   "Community non-profit — broadcaster-friendly.",
        "website":     "https://bigbradio.net/cpop",
        "logo":        "https://archive.org/images/glogo.png",
    },

    # Broadcaster-safe ─────────────────────────────────────────────────────────
    "pretzel": {
        "label":       "Pretzel Rocks",
        "stream":      "https://stream.pretzel.rocks/",
        "kind":        "Mixed / Broadcaster-safe",
        "region":      "Global",
        "description": "Designed specifically for Twitch and Discord streamers. Fully licensed, zero copyright claims.",
        "copyright":   "100% copyright-free — streamer-licensed.",
        "website":     "https://www.pretzel.rocks/",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "wfmu": {
        "label":       "WFMU 91.1 FM",
        "stream":      "https://stream0.wfmu.org/freeform-128k",
        "kind":        "Freeform / Eclectic / Independent",
        "region":      "New Jersey, USA",
        "description": "America's oldest independent radio station and founder of the Free Music Archive. Punk, jazz, experimental, 78 RPM records — completely unpredictable. Most music played is copyright-free or shareware-licensed.",
        "copyright":   "Broadcaster-friendly — non-profit, Free Music Archive founder.",
        "website":     "https://www.wfmu.org/",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "jamendo": {
        "label":       "Jamendo — Indie Radio",
        "stream":      "https://streaming.jamendo.com/JamIndie",
        "kind":        "Indie / Creative Commons",
        "region":      "Luxembourg / Belgium / Global",
        "description": "The world's largest Creative Commons music platform, based in Luxembourg-Belgium. Indie, jazz and electronic — all tracks are copyright-free and streamer-safe.",
        "copyright":   "100% Creative Commons — zero copyright risk.",
        "website":     "https://www.jamendo.com/",
        "logo":        "https://archive.org/images/glogo.png",
    },

    # Belgium — Independent Radio ──────────────────────────────────────────────
    "radio_panik": {
        "label":       "Radio Panik — Brussels",
        "stream":      "http://streaming.domainepublic.net:8000/radiopanik.mp3",
        "kind":        "Experimental / Jazz / World",
        "region":      "Brussels, Belgium",
        "description": "Independent community radio broadcasting since 1983. Multilingual, experimental, jazz and world music. Belgian independent radio at its finest.",
        "copyright":   "Community radio — independent artists, broadcaster-friendly.",
        "website":     "https://www.radiopanik.org/",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "radio_centraal": {
        "label":       "Radio Centraal — Antwerp",
        "stream":      "http://streaming.radiocentraal.org:8000/radiocentraal.mp3",
        "kind":        "Avant-garde / Noise / Independent Jazz",
        "region":      "Antwerp, Belgium",
        "description": "One of Belgium's oldest independent stations. Artistic and niche — avant-garde, noise and independent jazz. Antwerp's cultural underground.",
        "copyright":   "Community radio — independent artists, broadcaster-friendly.",
        "website":     "https://www.radiocentraal.org/",
        "logo":        "https://archive.org/images/glogo.png",
    },

    # Archive — Public Domain Radio Theatre ────────────────────────────────────
    "suspense": {
        "label":       "Suspense — Noir Mystery (1942–1962)",
        "stream":      "https://archive.org/download/OTRR_Suspense_Singles/Suspense_42-06-17_001_Summer_Night.mp3",
        "kind":        "Noir / Radio Theatre",
        "region":      "USA — Archive",
        "description": "The greatest mystery radio series in history. Hitchcock-style suspense. Fully public domain.",
        "copyright":   "Public Domain — no copyright.",
        "website":     "https://archive.org/details/OTRR_Suspense_Singles",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "broadway": {
        "label":       "Broadway Is My Beat (1949–1954)",
        "stream":      "https://archive.org/download/OTRR_Broadway_Is_My_Beat_Singles/Broadway_49-02-26_e01_The_Louis_Reinhardt_Murder_Case.mp3",
        "kind":        "Noir Detective / Radio Theatre",
        "region":      "USA — Archive",
        "description": "A detective on New York's dark streets. The finest example of film noir in audio form.",
        "copyright":   "Public Domain — no copyright.",
        "website":     "https://archive.org/details/OTRR_Broadway_Is_My_Beat_Singles",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "x_minus_one": {
        "label":       "X Minus One — Sci-Fi (1955–1958)",
        "stream":      "https://archive.org/download/OTRR_X_Minus_One_Singles/X_Minus_One_55-04-24_001_No_Contact.mp3",
        "kind":        "Science Fiction / Radio Theatre",
        "region":      "USA — Archive",
        "description": "First audio adaptations of Ray Bradbury and Isaac Asimov. Futuristic yet retro.",
        "copyright":   "Public Domain — no copyright.",
        "website":     "https://archive.org/details/OTRR_X_Minus_One_Singles",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "waam_1928": {
        "label":       "WAAM 1928 — First Radio Experiment",
        "stream":      "https://archive.org/download/waam-september-11-1928/waam-september-11-1928.mp3",
        "kind":        "Historical Recording / 1928",
        "region":      "Newark, USA — Archive",
        "description": "September 11, 1928 — one of history's first pre-recorded radio broadcast experiments. Rare and fully public domain.",
        "copyright":   "Public Domain — pre-1928, no copyright.",
        "website":     "https://archive.org/details/waam-september-11-1928",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "78rpm": {
        "label":       "78 RPM & Cylinder Archive",
        "stream":      "https://archive.org/download/78_tiger-rag_original-dixieland-jass-band-sbarbaro-shields-edwards-la/78_tiger-rag_original-dixieland-jass-band-sbarbaro-shields-edwards-la_02_3.3_EQ.mp3",
        "kind":        "Historical / Jazz / Pre-1928",
        "region":      "Global — Archive",
        "description": "Digitized 78 RPM and cylinder recordings from 1900–1928. Jazz, blues and world music. Fully public domain.",
        "copyright":   "Public Domain — pre-1928 recordings.",
        "website":     "https://archive.org/details/georgeblood",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "belgian_jazz_1942": {
        "label":       "Gus Viseur — Belgian Jazz 1942",
        "stream":      "https://archive.org/download/78_swing-42_gus-viseur-et-son-orchestre_gbia0148416a/01%20-%20Swing%2042%20-%20Gus%20Viseur%20et%20son%20orchestre.mp3",
        "kind":        "Belgian Jazz / 1942 / Public Domain",
        "region":      "Brussels, Belgium — Archive",
        "description": "Gus Viseur and his orchestra — Brussels jazz from 1942. Belgium was one of Europe's jazz centres. Rare, atmospheric and fully public domain.",
        "copyright":   "Public Domain — 1942 recording, copyright expired.",
        "website":     "https://archive.org/details/78_swing-42_gus-viseur-et-son-orchestre_gbia0148416a",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "belgian_vintage": {
        "label":       "Belgian Vintage — Mon Ami le Vent (1940s)",
        "stream":      "https://archive.org/download/78_mon-ami-le-vent_nina-mona-jack-s-orchestra-v-p-t_gbia0148416b/03%20-%20Mon%20ami%20le%20vent%20-%20Nina%20Mona.mp3",
        "kind":        "Belgian Chanson / 1940s / Public Domain",
        "region":      "Belgium — Archive",
        "description": "Nina Mona with Jack's Orchestra — a Belgian chanson from the 1940s. The crackling sound of vintage Belgian radio, fully public domain.",
        "copyright":   "Public Domain — 1940s recording, copyright expired.",
        "website":     "https://archive.org/details/78_mon-ami-le-vent_nina-mona-jack-s-orchestra-v-p-t_gbia0148416b",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "flemish_vintage": {
        "label":       "De Vrolijke Belgen — Flemish Vintage",
        "stream":      "https://archive.org/download/78_ik-ben-verliefd-op-jou_de-vrolijke-belgen-l-p-t_gbia0151241b/02%20-%20Ik%20ben%20verliefd%20op%20jou%20-%20De%20Vrolijke%20Belgen.mp3",
        "kind":        "Flemish Pop / 1940s / Public Domain",
        "region":      "Belgium — Archive",
        "description": "De Vrolijke Belgen — cheerful Flemish pop from the 1940s. A window into Belgian culture before television. Fully public domain.",
        "copyright":   "Public Domain — 1940s recording, copyright expired.",
        "website":     "https://archive.org/details/78_ik-ben-verliefd-op-jou_de-vrolijke-belgen-l-p-t_gbia0151241b",
        "logo":        "https://archive.org/images/glogo.png",
    },
}

GROUPS: dict[str, list[str]] = {
    "philosophy": ["alan_watts", "oxford_phil", "yale_death", "cambridge_lit", "columbia_history", "ens_paris"],
    "ambient":    ["drone_zone", "groove_salad", "nightride", "argofox", "koto_tradition"],
    "jazz":       ["jazz24", "wbgo", "fip_jazz"],
    "eclectic":   ["fip", "kexp", "radio_paradise", "wfmu", "jamendo"],
    "anime":      ["listen_moe", "listen_moe_kpop", "chillhop", "touhou"],
    "asian":      ["big_b_kpop", "big_b_jpop", "big_b_cpop", "japan_noir_1936"],
    "safe":       ["pretzel"],
    "belgium":    ["radio_panik", "radio_centraal", "belgian_jazz_1942", "belgian_vintage", "flemish_vintage"],
    "archive":    ["suspense", "broadway", "x_minus_one", "waam_1928", "78rpm", "vintage_exercise"],
}

GROUP_LABELS: dict[str, str] = {
    "philosophy": "Philosophy & Academic Lectures",
    "ambient":    "Ambient / Electronic / Zen",
    "jazz":       "Jazz",
    "eclectic":   "Eclectic / World / Independent",
    "anime":      "Anime / Lo-fi / Touhou",
    "asian":      "Asian Pop & Vintage (K / J / C-Pop)",
    "safe":       "Broadcaster-safe",
    "belgium":    "Belgium — Independent & Archive",
    "archive":    "Archive — Radio Theatre & Curiosities (Public Domain)",
}

STATION_CHOICES = [
    app_commands.Choice(name=v["label"][:100], value=k)
    for k, v in STATIONS.items()
]


# ── Embed builders ────────────────────────────────────────────────────────────

def _station_embed(key: str, playing: bool = False) -> discord.Embed:
    s      = STATIONS[key]
    status = "▶  Now Playing" if playing else s["kind"]
    embed  = discord.Embed(
        title       = s["label"],
        description = f"*{s['description']}*",
        color       = _COLOR,
        url         = s["website"],
    )
    embed.add_field(name="Genre",      value=s["kind"],           inline=True)
    embed.add_field(name="Region",     value=s["region"],         inline=True)
    embed.add_field(name="License",    value=s["copyright"],      inline=False)
    embed.add_field(name="Stream URL", value=f"`{s['stream']}`",  inline=False)
    embed.add_field(name="More info",  value=s["website"],        inline=False)

    if s.get("logo"):
        embed.set_thumbnail(url=s["logo"])

    embed.set_footer(text=f"[ BOTTANY RADIO ]  {status}")
    return embed


def _catalog_embeds(group_key: Optional[str] = None) -> list[discord.Embed]:
    groups = {group_key: GROUPS[group_key]} if group_key else GROUPS
    embeds: list[discord.Embed] = []
    for gk, keys in groups.items():
        embed = discord.Embed(
            title = f"Bottany Radio — {GROUP_LABELS[gk]}",
            color = _COLOR,
        )
        for k in keys:
            s = STATIONS[k]
            embed.add_field(
                name  = s["label"],
                value = (
                    f"*{s['kind']}  ·  {s['region']}*\n"
                    f"{s['description']}\n"
                    f"[Website]({s['website']})"
                ),
                inline = False,
            )
        embed.set_footer(text="[ BOTTANY RADIO ]  /radio play <station>")
        embeds.append(embed)
    return embeds


# ── Registration ──────────────────────────────────────────────────────────────

async def register(bot: discord.Client, data_dir: str) -> None:
    if bot.tree.get_command("radio"):
        return

    group = app_commands.Group(
        name        = "radio",
        description = "Bottany Radio — live radio and archive streams",
    )

    @group.command(name="play", description="Start a radio stream in your voice channel")
    @app_commands.describe(station="Select a station to play")
    @app_commands.choices(station=STATION_CHOICES)
    async def radio_play(interaction: discord.Interaction, station: str) -> None:
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return
        member = interaction.guild.get_member(interaction.user.id)
        if not member or not member.voice or not member.voice.channel:
            await interaction.response.send_message("Join a voice channel first.", ephemeral=True)
            return
        if station not in STATIONS:
            await interaction.response.send_message("Unknown station.", ephemeral=True)
            return

        await interaction.response.defer()
        s  = STATIONS[station]
        vc: Optional[discord.VoiceClient] = interaction.guild.voice_client  # type: ignore
        if vc:
            if vc.is_playing(): vc.stop()
            if vc.channel != member.voice.channel: await vc.move_to(member.voice.channel)
        else:
            vc = await member.voice.channel.connect()

        source = discord.FFmpegPCMAudio(s["stream"], **_FFMPEG_OPTS)
        vc.play(source, after=lambda e: log.error("Radio error: %s", e) if e else None)
        vc.source = discord.PCMVolumeTransformer(vc.source, volume=0.8)
        await interaction.followup.send(embed=_station_embed(station, playing=True))

    @group.command(name="stop", description="Stop the radio and leave the voice channel")
    async def radio_stop(interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return
        vc: Optional[discord.VoiceClient] = interaction.guild.voice_client  # type: ignore
        if not vc or not vc.is_connected():
            await interaction.response.send_message("No active radio stream.", ephemeral=True)
            return
        await vc.disconnect()
        embed = discord.Embed(description="Radio stopped.", color=_COLOR)
        embed.set_footer(text="[ BOTTANY RADIO ]")
        await interaction.response.send_message(embed=embed)

    @group.command(name="info", description="Browse all stations grouped by genre")
    @app_commands.describe(genre="Filter by genre (optional)")
    @app_commands.choices(genre=[
        app_commands.Choice(name=v, value=k) for k, v in GROUP_LABELS.items()
    ])
    async def radio_info(interaction: discord.Interaction, genre: Optional[str] = None) -> None:
        await interaction.response.defer()
        embeds = _catalog_embeds(genre)
        for i in range(0, len(embeds), 10):
            if i == 0:
                await interaction.followup.send(embeds=embeds[i:i+10])
            else:
                await interaction.followup.send(embeds=embeds[i:i+10])

    @group.command(name="station", description="Detailed info and stream link for one station")
    @app_commands.describe(station="Select a station")
    @app_commands.choices(station=STATION_CHOICES)
    async def radio_station(interaction: discord.Interaction, station: str) -> None:
        if station not in STATIONS:
            await interaction.response.send_message("Unknown station.", ephemeral=True)
            return
        await interaction.response.send_message(embed=_station_embed(station))

    bot.tree.add_command(group)

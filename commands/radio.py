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
        "logo":        "https://nightride.fm/favicon.ico",
    },
    "argofox": {
        "label":       "Argofox — Chill / Synth",
        "stream":      "https://stream.argofox.com/argofox",
        "kind":        "Indie / Chill / Electronic",
        "region":      "Global",
        "description": "Independent and lo-fi electronic music curated for streamers. No copyright.",
        "copyright":   "100% copyright-free.",
        "website":     "https://argofox.com/",
        "logo":        "https://argofox.com/favicon.ico",
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
        "logo":        "https://www.jazz24.org/wp-content/uploads/jazz24-logo-1400x1400.png",
    },
    "wbgo": {
        "label":       "WBGO Newark",
        "stream":      "http://wbgo.streamguys.net/wbgo",
        "kind":        "Pure American Jazz",
        "region":      "Newark, USA",
        "description": "Over forty years of uninterrupted jazz. Hard bop, soul jazz and straight-ahead.",
        "copyright":   "Broadcaster-friendly — public radio.",
        "website":     "https://www.wbgo.org/",
        "logo":        "https://www.wbgo.org/sites/wbgo/files/WBGO_Logo_Square.png",
    },
    "fip_jazz": {
        "label":       "FIP Jazz (France)",
        "stream":      "https://stream.radiofrance.fr/fipjazz/fipjazz_hifi.m3u8",
        "kind":        "Eclectic Jazz / France",
        "region":      "Paris, France",
        "description": "Radio France's jazz channel. Feels like sitting in a corner of a Parisian café.",
        "copyright":   "Broadcaster-friendly — public radio.",
        "website":     "https://www.fip.fr/jazz",
        "logo":        "https://www.fip.fr/sites/fip/files/styles/image_600/public/2021-06/FIP_JAZZ_CARRE.jpg",
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
        "logo":        "https://www.fip.fr/sites/fip/files/styles/image_600/public/2021-06/FIP_CARRE.jpg",
    },
    "kexp": {
        "label":       "KEXP 90.3 FM",
        "stream":      "https://kexp-mp3-128.streamguys1.com/kexp128.mp3",
        "kind":        "Indie / Alternative / World",
        "region":      "Seattle, USA",
        "description": "One of the world's best independent stations. DJs hand-pick every track — synth, indie, jazz and world music.",
        "copyright":   "Broadcaster-friendly — non-profit public radio.",
        "website":     "https://www.kexp.org/",
        "logo":        "https://www.kexp.org/static/images/kexp-social.jpg",
    },
    "radio_paradise": {
        "label":       "Radio Paradise",
        "stream":      "https://stream.radioparadise.com/mp3-128",
        "kind":        "Eclectic Rock / Indie / World",
        "region":      "Global",
        "description": "Ad-free, listener-supported. Classic rock, indie and world music with an artistic flow.",
        "copyright":   "Broadcaster-friendly — listener-supported.",
        "website":     "https://radioparadise.com/",
        "logo":        "https://radioparadise.com/graphics/logo_1400.jpg",
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

    # Broadcaster-safe ─────────────────────────────────────────────────────────
    "pretzel": {
        "label":       "Pretzel Rocks",
        "stream":      "https://stream.pretzel.rocks/",
        "kind":        "Mixed / Broadcaster-safe",
        "region":      "Global",
        "description": "Designed specifically for Twitch and Discord streamers. Fully licensed, zero copyright claims.",
        "copyright":   "100% copyright-free — streamer-licensed.",
        "website":     "https://www.pretzel.rocks/",
        "logo":        "https://www.pretzel.rocks/static/images/pretzel-logo.png",
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
}

GROUPS: dict[str, list[str]] = {
    "ambient":  ["drone_zone", "groove_salad", "nightride", "argofox"],
    "jazz":     ["jazz24", "wbgo", "fip_jazz"],
    "eclectic": ["fip", "kexp", "radio_paradise"],
    "anime":    ["listen_moe", "listen_moe_kpop"],
    "safe":     ["pretzel"],
    "archive":  ["suspense", "broadway", "x_minus_one", "waam_1928", "78rpm"],
}

GROUP_LABELS: dict[str, str] = {
    "ambient":  "Ambient / Electronic",
    "jazz":     "Jazz",
    "eclectic": "Eclectic / World",
    "anime":    "Anime / K-Pop",
    "safe":     "Broadcaster-safe",
    "archive":  "Archive — Radio Theatre (Public Domain)",
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

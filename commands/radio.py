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

STATIONS: dict[str, dict] = {

    # Philosophy & Academic (Cambridge, Columbia, Yale, Oxford, ENS) ───────────
    "cambridge_lit": {
        "label":       "Cambridge — Literature & Philology",
        "stream":      "https://archive.org/download/cambridge-university-podcasts/lit-lecture.mp3",
        "kind":        "Academic / Linguistics / Literature",
        "region":      "Cambridge, UK",
        "description": "Deep dives into Virginia Woolf, philology, and literary criticism from Cambridge University.",
        "copyright":   "Open Educational Resource — CC BY-NC-SA.",
        "website":     "https://www.cam.ac.uk/",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "columbia_history": {
        "label":       "Columbia — Oral History Archive",
        "stream":      "https://archive.org/download/columbia-university-oral-history/interview-session.mp3",
        "kind":        "Academic / Oral History / Philosophy",
        "region":      "New York, USA",
        "description": "Original voices of 20th-century intellectuals and poets from the Columbia University archives.",
        "copyright":   "Educational Archive — Public Access.",
        "website":     "https://library.columbia.edu/libraries/rbml/collecting/oral-history.html",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "oxford_phil": {
        "label":       "Oxford — Philosophy for Beginners",
        "stream":      "https://podcasts.ox.ac.uk/sites/default/files/audio/philosophy-for-beginners-1-what-is-philosophy.mp3",
        "kind":        "Academic / Philosophy",
        "region":      "Oxford, UK",
        "description": "Foundational philosophical questions explored by Oxford Faculty members.",
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
    "alan_watts": {
        "label":       "Alan Watts — Early Radio Talks",
        "stream":      "https://archive.org/download/alan-watts-early-radio-talks/01%20The%20Silent%20Mind.mp3",
        "kind":        "Philosophy / Eastern Thought",
        "region":      "USA / UK — Archive",
        "description": "Rare radio talks by Alan Watts on Zen, Taoism, and the nature of reality.",
        "copyright":   "Public Domain / Historical Archive.",
        "website":     "https://archive.org/details/alan-watts-early-radio-talks",
        "logo":        "https://archive.org/images/glogo.png",
    },

    # Japan & Asian Culture (Vintage & Modern) ────────────────────────────────
    "japan_noir_1936": {
        "label":       "Japan Noir — Jazz 1936",
        "stream":      "https://archive.org/download/78_shina-no-yoru-china-night_hamako-watanabe-v-p-t_gbia0148417a/01%20-%20Shina%20no%20yoru%20%28China%20Night%29%20-%20Hamako%20Watanabe.mp3",
        "kind":        "Vintage Japanese Jazz / 1930s",
        "region":      "Tokyo, Japan — Archive",
        "description": "Atmospheric pre-war Japanese jazz. A smoky, noir aesthetic from old Tokyo.",
        "copyright":   "Public Domain — 1930s recording.",
        "website":     "https://archive.org/details/78rpm_japan",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "koto_tradition": {
        "label":       "Traditional Koto — Rokudan",
        "stream":      "https://archive.org/download/78_rokudan-no-shirabe-koto-solo_hagiwara-seigi_gbia0216744a/01%20-%20Rokudan-no-shirabe%20%28Koto%20Solo%29%20-%20Hagiwara%20Seigi.mp3",
        "kind":        "Traditional Japanese / Zen",
        "region":      "Japan — Archive",
        "description": "Hypnotic Koto performance. Ideal for coding, poetry reading, or reflection.",
        "copyright":   "Public Domain — Historical Recording.",
        "website":     "https://archive.org/details/78rpm",
        "logo":        "https://archive.org/images/glogo.png",
    },
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

    # Belgium — Independent & Archive ──────────────────────────────────────────
    "radio_panik": {
        "label":       "Radio Panik — Brussels",
        "stream":      "http://streaming.domainepublic.net:8000/radiopanik.mp3",
        "kind":        "Experimental / Jazz / World",
        "region":      "Brussels, Belgium",
        "description": "Independent community radio since 1983. Multilingual and avant-garde.",
        "copyright":   "Independent artists — broadcaster-friendly.",
        "website":     "https://www.radiopanik.org/",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "belgian_jazz_1942": {
        "label":       "Gus Viseur — Belgian Jazz 1942",
        "stream":      "https://archive.org/download/78_swing-42_gus-viseur-et-son-orchestre_gbia0148416a/01%20-%20Swing%2042%20-%20Gus%20Viseur%20et%20son%20orchestre.mp3",
        "kind":        "Belgian Jazz / 1942 / Public Domain",
        "region":      "Brussels, Belgium — Archive",
        "description": "Brussels jazz from 1942. Atmospheric, rare and fully public domain.",
        "copyright":   "Public Domain — 1942 recording.",
        "website":     "https://archive.org/details/78_swing-42_gus-viseur-et-son-orchestre_gbia0148416a",
        "logo":        "https://archive.org/images/glogo.png",
    },

    # Noir & Radio Theatre (Archive) ───────────────────────────────────────────
    "suspense": {
        "label":       "Suspense — Noir Mystery (1942–1962)",
        "stream":      "https://archive.org/download/OTRR_Suspense_Singles/Suspense_42-06-17_001_Summer_Night.mp3",
        "kind":        "Noir / Radio Theatre",
        "region":      "USA — Archive",
        "description": "The gold standard of radio drama. Hitchcock-style noir mysteries.",
        "copyright":   "Public Domain — no copyright.",
        "website":     "https://archive.org/details/OTRR_Suspense_Singles",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "broadway": {
        "label":       "Broadway Is My Beat (1949–1954)",
        "stream":      "https://archive.org/download/OTRR_Broadway_Is_My_Beat_Singles/Broadway_49-02-26_e01_The_Louis_Reinhardt_Murder_Case.mp3",
        "kind":        "Noir Detective / Radio Theatre",
        "region":      "USA — Archive",
        "description": "The finest example of film noir in audio. Gritty detective stories.",
        "copyright":   "Public Domain — no copyright.",
        "website":     "https://archive.org/details/OTRR_Broadway_Is_My_Beat_Singles",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "waam_1928": {
        "label":       "WAAM 1928 — Radio History",
        "stream":      "https://archive.org/download/waam-september-11-1928/waam-september-11-1928.mp3",
        "kind":        "Historical Recording / 1928",
        "region":      "Newark, USA — Archive",
        "description": "A window into history. One of the first pre-recorded radio broadcast experiments.",
        "copyright":   "Public Domain — pre-1928.",
        "website":     "https://archive.org/details/waam-september-11-1928",
        "logo":        "https://archive.org/images/glogo.png",
    },

    # Ambient / Electronic / Jazz (Stable Streams) ──────────────────────────────
    "drone_zone": {
        "label":       "SomaFM — Drone Zone",
        "stream":      "http://ice1.somafm.com/dronezone-128-mp3",
        "kind":        "Ambient / Atmospheric",
        "region":      "San Francisco, USA",
        "description": "Minimalist, poetic sound for deep focus and reading.",
        "copyright":   "Copyright-free — SomaFM is independent.",
        "website":     "https://somafm.com/dronezone/",
        "logo":        "https://somafm.com/img3/dronezone-400.jpg",
    },
    "jazz24": {
        "label":       "Jazz24",
        "stream":      "https://live.amperwave.net/direct/ppm-jazz24aac-ibc1",
        "kind":        "Modern & Classic Jazz",
        "region":      "Seattle, USA",
        "description": "One of the world's best jazz stations. From bebop to smooth jazz.",
        "copyright":   "Broadcaster-friendly — public radio.",
        "website":     "https://www.jazz24.org/",
        "logo":        "https://archive.org/images/glogo.png",
    },
    "vintage_exercise": {
        "label":       "Vintage Physical Culture (1940s)",
        "stream":      "https://archive.org/download/78_daily-exercises-for-the-home-part-2_dr-c-ward-crampton_gbia0185805b/02%20-%20Daily%20exercises%20for%20the%20home%20-%20Dr.%20C.%20Ward%20Crampton.mp3",
        "kind":        "Retro Health / Physical Ed.",
        "region":      "USA — Archive",
        "description": "Original 1940s home exercise recordings. Nostalgic but healthy.",
        "copyright":   "Public Domain — Historical broadcast.",
        "website":     "https://archive.org/details/78_daily-exercises-for-the-home",
        "logo":        "https://archive.org/images/glogo.png",
    },
}

GROUPS: dict[str, list[str]] = {
    "philosophy": ["cambridge_lit", "columbia_history", "oxford_phil", "yale_death", "ens_paris", "alan_watts"],
    "ambient":    ["drone_zone", "koto_tradition", "listen_moe"],
    "jazz_noir":  ["jazz24", "japan_noir_1936", "belgian_jazz_1942"],
    "archive":    ["suspense", "broadway", "waam_1928", "vintage_exercise"],
    "belgium":    ["radio_panik", "belgian_jazz_1942"],
}

GROUP_LABELS: dict[str, str] = {
    "philosophy": "Philosophy & Academic Lectures (Ivy League/EU)",
    "ambient":    "Ambient, Zen & Japanese Aesthetic",
    "jazz_noir":  "Jazz & Vintage Noir Atmosphere",
    "archive":    "Historical Archive & Radio Theatre",
    "belgium":    "Belgium — Independent & Vintage",
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
        description = "Bottany Radio — live radio and academic archives",
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

# Translated version (EN + NL simplified inline replacement)
# NOTE: Language chosen: English (primary). Dutch equivalents commented.

from __future__ import annotations
import asyncio
import logging
from typing import Optional

import discord
from discord import app_commands

log = logging.getLogger(__name__)

_COLOR = 0xCC8800

_FFMPEG_OPTS = {
    "before_options": (
        "-reconnect 1 "
        "-reconnect_streamed 1 "
        "-reconnect_delay_max 5 "
        "-reconnect_at_eof 1"
    ),
    "options": "-vn",
}

STATIONS: dict[str, dict] = {
    "drone_zone": {
        "label": "SomaFM — Drone Zone",
        "stream": "http://ice1.somafm.com/dronezone-128-mp3",
        "kind": "Ambient / Atmospheric",
        "region": "San Francisco, USA",
        "description": "Minimalist, poetic sound experience. Ideal for coding, reading, or deep thinking.",
        "copyright": "Copyright-free — SomaFM is independent and ad-free.",
        "website": "https://somafm.com/dronezone/",
    },
    "groove_salad": {
        "label": "SomaFM — Groove Salad",
        "stream": "http://ice1.somafm.com/groovesalad-128-mp3",
        "kind": "Chill-out / Global",
        "region": "San Francisco, USA",
        "description": "A chill-out legend. Downtempo, trip-hop, and ambient beats.",
        "copyright": "Copyright-free — SomaFM is independent and ad-free.",
        "website": "https://somafm.com/groovesalad/",
    },
    "nightride": {
        "label": "Nightride.fm",
        "stream": "https://stream.nightride.fm/nightride.mp3",
        "kind": "Synthwave / Cyberpunk",
        "region": "Global",
        "description": "A retro-futuristic journey. Synthwave, darksynth, cyberpunk.",
        "copyright": "100% copyright-free — licensed for streaming.",
        "website": "https://nightride.fm/",
    },
}

STATION_CHOICES = [
    app_commands.Choice(name=v["label"][:100], value=k)
    for k, v in STATIONS.items()
]


def _station_embed(key: str, playing: bool = False) -> discord.Embed:
    s = STATIONS[key]
    status = "▶ Now Playing" if playing else s["kind"]

    embed = discord.Embed(
        title=s["label"],
        description=f"*{s['description']}*",
        color=_COLOR,
        url=s["website"],
    )

    embed.add_field(name="Genre", value=s["kind"], inline=True)
    embed.add_field(name="Region", value=s["region"], inline=True)
    embed.add_field(name="License", value=s["copyright"], inline=False)
    embed.add_field(name="Stream URL", value=f"`{s['stream']}`", inline=False)
    embed.add_field(name="More info", value=s["website"], inline=False)

    embed.set_footer(text=f"[ BOTTANY RADIO ] {status}")
    return embed


async def register(bot: discord.Client, data_dir: str) -> None:
    if bot.tree.get_command("radio"):
        return

    group = app_commands.Group(
        name="radio",
        description="Bottany Radio — live radio and archive streams",
    )

    @group.command(name="play", description="Start a radio stream in a voice channel")
    @app_commands.describe(station="Select a station")
    @app_commands.choices(station=STATION_CHOICES)
    async def radio_play(interaction: discord.Interaction, station: str) -> None:

        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used in servers.", ephemeral=True
            )
            return

        member = interaction.guild.get_member(interaction.user.id)
        if not member or not member.voice or not member.voice.channel:
            await interaction.response.send_message(
                "You need to join a voice channel first.", ephemeral=True
            )
            return

        if station not in STATIONS:
            await interaction.response.send_message(
                "Unknown station.", ephemeral=True
            )
            return

        await interaction.response.defer()

        voice_channel = member.voice.channel
        s = STATIONS[station]

        vc: Optional[discord.VoiceClient] = interaction.guild.voice_client
        if vc:
            if vc.is_playing():
                vc.stop()
            if vc.channel != voice_channel:
                await vc.move_to(voice_channel)
        else:
            vc = await voice_channel.connect()

        source = discord.FFmpegPCMAudio(s["stream"], **_FFMPEG_OPTS)
        vc.play(source, after=lambda e: log.error("Radio error: %s", e) if e else None)
        vc.source = discord.PCMVolumeTransformer(vc.source, volume=0.8)

        embed = _station_embed(station, playing=True)
        await interaction.followup.send(embed=embed)

    @group.command(name="stop", description="Stop the radio and leave the channel")
    async def radio_stop(interaction: discord.Interaction) -> None:

        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used in servers.", ephemeral=True
            )
            return

        vc: Optional[discord.VoiceClient] = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            await interaction.response.send_message(
                "There is no active radio stream.", ephemeral=True
            )
            return

        await vc.disconnect()

        embed = discord.Embed(
            description="Radio stopped.",
            color=_COLOR,
        )
        embed.set_footer(text="[ BOTTANY RADIO ]")

        await interaction.response.send_message(embed=embed)

    @group.command(name="info", description="Show all stations and stream links")
    async def radio_info(interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Station catalog coming soon.")

    bot.tree.add_command(group)

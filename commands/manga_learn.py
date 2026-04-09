from __future__ import annotations

import logging
import discord
from discord import app_commands

log = logging.getLogger(__name__)

def register(bot: discord.Client, data_dir: str = None) -> None:
    if bot.tree.get_command("manga"):
        return

    manga_group = app_commands.Group(name="manga", description="Academic knowledge on Manga history, drafting techniques, lexicon, and awards.")

    # =====================================================================
    # 1. HISTORICAL ORIGINS (/manga history)
    # =====================================================================
    @manga_group.command(name="history", description="Explore the official historical origins and evolution of Japanese Manga.")
    @app_commands.choices(era=[
        app_commands.Choice(name="Heian Period (12th C.): Chōjū-giga", value="heian"),
        app_commands.Choice(name="Edo Period (18th C.): Kibyōshi & Hokusai", value="edo"),
        app_commands.Choice(name="Pre-War (1930s): Kamishibai Theater", value="prewar"),
        app_commands.Choice(name="Post-War (1945+): Tezuka's Cinematic Revolution", value="postwar"),
        app_commands.Choice(name="The Gekiga Movement (1957+): Dramatic Pictures", value="gekiga")
    ])
    async def history(interaction: discord.Interaction, era: str):
        embed = discord.Embed(color=0x002147)
        
        if era == "heian":
            embed.title = "ᨒ Chōjū-jinbutsu-giga (鳥獣人物戯画)"
            embed.description = "### The Genesis of Sequential Art\n*Officially recognized by the Kyoto National Museum as the earliest origin of Japanese sequential art.*\n"
            embed.add_field(name="Academic Concept: Iji dōzu (異時同図)", value="*A groundbreaking technique meaning 'different times, same picture'. The scrolls depicted a continuous narrative where the same character appears multiple times across the same landscape, establishing the right-to-left chronological flow still used today.*", inline=False)
        
        elif era == "edo":
            embed.title = "📚 Kibyōshi (黄表紙) & Hokusai Manga (北斎漫画)"
            embed.description = "### The Lexical Birth of 'Manga'\n*The integration of text and illustration for mass consumption.*\n"
            embed.add_field(name="Kibyōshi: The First Comic Books", value="*Originating in 1775, these 'yellow-backed' books were revolutionary for integrating 'Moji' (文字 - text) directly into the 'E' (絵 - picture) space, foreshadowing the modern speech balloon.*", inline=False)
            
        elif era == "prewar":
            embed.title = "☼ Kamishibai (紙芝居) - The Paper Theater"
            embed.description = "### The Pacing of the Page-Turn\n*The psychological predecessor to modern manga reading rhythm.*\n"
            embed.add_field(name="Performative Sequential Art", value="*Thriving in the 1930s, storytellers used illustrated boards to tell stories. The dramatic 'reveal' of sliding one picture board away to show the next directly influenced the modern manga page-turn (Mekuri).* ✍", inline=False)

        elif era == "postwar":
            embed.title = "🌌 Osamu Tezuka (手塚治虫)"
            embed.description = "### Modern Manga Architecture\n*The cinematic framing revolution initiated post-1945.*"
            embed.add_field(name="Eiga-teki shuho (映画的手法)", value="*Tezuka introduced 'Cinematic Techniques'. Influenced by French cinema, he broke away from the theatrical stage-play perspective, introducing extreme close-ups, dynamic panning, and decompressed time pacing.*", inline=False)

        elif era == "gekiga":
            embed.title = "🍷 The Gekiga Movement (劇画)"
            embed.description = "### The Maturation of the Medium\n*A rebellion against the Disney-esque, rounded styles of early post-war manga.*"
            embed.add_field(name="Dramatic Pictures", value="*Coined in 1957 by Yoshihiro Tatsumi. 'Geki' (劇) translates to drama, and 'Ga' (画) to picture. It introduced gritty realism, heavy cinematic shadows, and mature psychological themes, directly birthing the modern Seinen demographic.*", inline=False)

        embed.set_footer(text="Verified by Historical Archives ✅")
        await interaction.response.send_message(embed=embed)


    # =====================================================================
    # 2. DRAFTING & TECHNIQUES (/manga technique)
    # =====================================================================
    @manga_group.command(name="technique", description="Advanced methodologies for drafting, inking, and manipulating space.")
    @app_commands.choices(method=[
        app_commands.Choice(name="Drafting: Nēmu (ネーム) & Paneling", value="drafting"),
        app_commands.Choice(name="Inking: Stroke Dynamics (入り/抜き)", value="inking"),
        app_commands.Choice(name="Textures: Tone-kezuri (トーン削り) & Beta", value="textures"),
        app_commands.Choice(name="Philosophy: The Concept of Ma (間)", value="philosophy")
    ])
    async def technique(interaction: discord.Interaction, method: str):
        embed = discord.Embed(color=0x002147)
        
        if method == "drafting":
            embed.title = "✏️ Architectural Drafting: Nēmu (ネーム)"
            embed.description = "### Storyboarding & Structural Pacing\n*The foundational architectural draft of Manga creation.*\n"
            embed.add_field(name="Kishōtenketsu (起承転結)", value="*A classic four-act narrative pacing: Introduction (Ki), Development (Shō), Twist (Ten), Conclusion (Ketsu).* ✍", inline=False)
            
        elif method == "inking":
            embed.title = "🖌️ Traditional Inking Dynamics (ペン先)"
            embed.description = "### Mastering Line Weight and Pressure\n*The physical analog tools that defined the traditional aesthetic.*\n"
            embed.add_field(name="Stroke Anatomy: Iri (入り) & Nuki (抜き)", value="*The fundamental kinetic pressure of a professional stroke. 'Iri' is the heavy entry point where the nib meets the paper. 'Nuki' is the tapering, weightless exit as the pen lifts.*\n", inline=False)

        elif method == "textures":
            embed.title = "🫧 Atmospheric Rendering: Ink & Screentones"
            embed.description = "### Advanced Texture Manipulation\n*Creating gradients and density by hand.*"
            embed.add_field(name="Tone-kezuri (トーン削り)", value="*A highly advanced physical technique. Artists apply physical screentone sheets to the paper, and then use a sharp craft knife to literally scrape away the printed dots, creating ethereal glowing light effects or smoke.*\n", inline=False)
            embed.add_field(name="Beta-nuri (ベタ塗り)", value="*The technique of filling designated areas entirely with solid black ink to dictate lighting sources and psychological weight.*", inline=False)

        elif method == "philosophy":
            embed.title = "🌌 The Philosophy of Space: Ma (間)"
            embed.description = "### The Pacing of Silence\n*The purposeful use of emptiness in sequential art.*\n"
            embed.add_field(name="Resonance", value="*In traditional Japanese aesthetics, 'Ma' translates to gap or pause. In manga, it is the silent panel—a sky, a dropped teacup, a lingering glance—used not to advance the plot, but to allow the reader's emotion to resonate.*", inline=False)

        embed.set_footer(text="Drafting Standards & Methodology ☕")
        await interaction.response.send_message(embed=embed)


    # =====================================================================
    # 3. LINGUISTIC LEXICON (/manga lexicon)
    # =====================================================================
    @manga_group.command(name="lexicon", description="Bilingual academic dictionary of Manga industry and structural terms.")
    @app_commands.choices(category=[
        app_commands.Choice(name="Manuscript Architecture (Tachi-kiri, Fukidashi)", value="architecture"),
        app_commands.Choice(name="The Publishing Ecosystem (Yomikiri, Dōjinshi)", value="ecosystem")
    ])
    async def lexicon(interaction: discord.Interaction, category: str):
        embed = discord.Embed(title="📕 Official Industry Lexicon", color=0x002147)
        
        if category == "architecture":
            embed.description = "### Manuscript Architecture\n*Linguistic breakdowns of page layout terminology.*"
            terms = (
                "🔵 **Tachi-kiri (断ち切り):** *The 'Bleed'. Artwork that intentionally extends to the absolute physical edge of the paper, destroying the boundary of the panel to create an illusion of infinite space.*\n\n"
                "🔵 **Fukidashi (吹き出し):** *The Speech Balloon. Derived from 'fukidasu' (to blow out), it is visually interpreted as a character's breath and soul escaping their body into the physical space of the page.*\n\n"
                "🔵 **Genga (原画):** *The finalized original manuscripts before the printing process. Represents the absolute final vision of the Mangaka.*"
            )
            embed.add_field(name="Vocabulary & Etymology", value=terms, inline=False)
            
        elif category == "ecosystem":
            embed.description = "### The Publishing Ecosystem\n*The structural terms of the Japanese publishing industry.*"
            terms = (
                "🔵 **Yomikiri (読み切り):** *A 'one-shot' manga. A self-contained story published in a single issue. It is the ultimate test for a new Mangaka to gauge reader popularity before serializing.*\n\n"
                "🔵 **Dōjinshi (同人誌):** *Self-published, independent works. Historically the most vital breeding ground for professional talent in Japan, allowing creators to bypass editorial restrictions.*\n\n"
                "🔵 **Ashisutanto (アシスタント):** *The atelier apprentice system. Assistants master architectural perspective and apply screentones, ensuring generational knowledge transfer.*"
            )
            embed.add_field(name="Industry Structure", value=terms, inline=False)

        embed.set_footer(text="Bilingual Database 📚")
        await interaction.response.send_message(embed=embed)


    # =====================================================================
    # 4. AWARDS & INSTITUTIONS (/manga awards)
    # =====================================================================
    @manga_group.command(name="awards", description="Explore the highest cultural and academic institutions in the Manga industry.")
    async def awards(interaction: discord.Interaction):
        embed = discord.Embed(title="🥂 Institutional Recognition", color=0x002147)
        embed.description = "### Official Award Sources\n*The governing bodies honoring narrative and artistic excellence.*"
        
        embed.add_field(name="Tezuka Osamu Cultural Prize (手塚治虫文化賞)", value="*Sponsored by the Asahi Shimbun since 1997. Named after the 'God of Manga', it rewards works that follow his rigorous, humanist, and cinematic tradition.*", inline=False)
        embed.add_field(name="Shogakukan Manga Award (小学館漫画賞)", value="*One of Japan's oldest and most prestigious awards, running since 1955. It rigorously categorizes excellence across demographics: Jidō (Children), Shōnen (Boys), Shōjo (Girls), and Ippan (General).* 📚", inline=False)
        embed.add_field(name="Kodansha Manga Award (講談社漫画賞)", value="*Established in 1977. Alongside Shogakukan, it serves as the ultimate benchmark for commercial and critical success in the Japanese publishing industry.*", inline=False)
        
        embed.set_footer(text="Cultural Merit Registry 🍾")
        await interaction.response.send_message(embed=embed)

    bot.tree.add_command(manga_group)

from __future__ import annotations
import urllib.parse
from typing import Dict, List, Tuple
import discord
from discord import app_commands

def _q(s: str) -> str:
    return urllib.parse.quote((s or "").strip())

def _mk_links(query: str) -> Dict[str, List[Tuple[str, str]]]:
    q = _q(query)
    # Reviews: use site-native search where possible to avoid brittle direct-slug guessing.
    reviews = [
        ("Metacritic search", f"https://www.metacritic.com/search/{q}/?category=game"),
        ("OpenCritic search", f"https://opencritic.com/search?q={q}"),
        ("IGN search", f"https://www.ign.com/search?q={q}"),
        ("GameSpot search", f"https://www.gamespot.com/search/?q={q}"),
        ("PC Gamer search", f"https://www.pcgamer.com/search/?searchTerm={q}"),
        ("Eurogamer search", f"https://www.eurogamer.net/search?q={q}"),
        ("Digital Foundry search", f"https://www.eurogamer.net/digitalfoundry/search?q={q}"),
        ("Steam store search", f"https://store.steampowered.com/search/?term={q}"),
        ("GOG search", f"https://www.gog.com/en/games?query={q}"),
    ]

    # Game databases / reference
    reference = [
        ("Wikipedia", f"https://en.wikipedia.org/wiki/Special:Search?search={q}"),
        ("MobyGames", f"https://www.mobygames.com/search/?q={q}"),
        ("IGDB", f"https://www.igdb.com/search?type=1&q={q}"),
        ("PCGamingWiki", f"https://www.pcgamingwiki.com/w/index.php?search={q}"),
    ]

    # Museums / archives (games + material culture)
    museums = [
        ("V&A Collections search", f"https://collections.vam.ac.uk/search/?q={q}"),
        ("Smithsonian search", f"https://www.si.edu/search?edan_q={q}"),
        ("The Strong National Museum of Play (site)", "https://www.museumofplay.org/"),
        ("Computer History Museum (site)", "https://computerhistory.org/"),
        ("MoMA Collection search", f"https://www.moma.org/collection/?q={q}"),
    ]

    # Fashion archives / costume collections (useful for character/costume research)
    fashion = [
        ("V&A Fashion (site)", "https://www.vam.ac.uk/collections/fashion"),
        ("The Met Costume Institute (site)", "https://www.metmuseum.org/about-the-met/collection-areas/the-costume-institute"),
        ("The Met Collection search", f"https://www.metmuseum.org/art/collection/search?q={q}"),
        ("FIT Museum (site)", "https://www.fitnyc.edu/museum/"),
        ("Kyoto Costume Institute (site)", "https://www.kci.or.jp/en/"),
    ]

    # Dictionaries / terminology (gaming terms, general English usage)
    dictionaries = [
        ("Merriam-Webster (search)", f"https://www.merriam-webster.com/dictionary/{q}"),
        ("Cambridge Dictionary (search)", f"https://dictionary.cambridge.org/dictionary/english/{q}"),
        ("Oxford Learner's Dictionaries (search)", f"https://www.oxfordlearnersdictionaries.com/definition/english/{q}"),
        ("Stanford Encyclopedia of Philosophy (search)", f"https://plato.stanford.edu/search/searcher.py?query={q}"),
    ]

    return {
        "Reviews": reviews,
        "Reference": reference,
        "Museums & archives": museums,
        "Fashion archives": fashion,
        "Dictionaries & terminology": dictionaries,
    }

def _add_field(embed: discord.Embed, name: str, links: List[Tuple[str, str]], *, max_items: int = 6) -> None:
    lines = []
    for title, url in links[:max_items]:
        lines.append(f"• [{title}]({url})")
    embed.add_field(name=name, value="\n".join(lines) if lines else "—", inline=False)

def register_game_sources(bot, data_dir: str) -> None:
    @app_commands.command(name="game_sources", description="Curated links for a game: reviews, museums/archives, fashion, dictionaries.")
    @app_commands.describe(query="Game title (or keyword)")
    async def game_sources(interaction: discord.Interaction, query: str):
        q = (query or "").strip()
        if not q:
            await interaction.response.send_message("Please provide a game title. Example: /game_sources Hades", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Sources for: {q}",
            description="Curated entry points across reviews, reference databases, museums/archives, fashion collections, and dictionaries.",
        )
        groups = _mk_links(q)
        _add_field(embed, "Reviews (prestige)", groups["Reviews"], max_items=6)
        _add_field(embed, "Reference databases", groups["Reference"], max_items=5)
        _add_field(embed, "Museums & archives", groups["Museums & archives"], max_items=5)
        _add_field(embed, "Fashion archives", groups["Fashion archives"], max_items=4)
        _add_field(embed, "Dictionaries & terminology", groups["Dictionaries & terminology"], max_items=4)

        embed.set_footer(text="Tip: Use exact titles for better search matches. Some museum/fashion sites may require in-site searching.")
        await interaction.response.send_message(embed=embed)

    bot.tree.add_command(game_sources)

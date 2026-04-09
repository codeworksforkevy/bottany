from __future__ import annotations
import random
import discord
from discord import app_commands

class LFGView(discord.ui.View):
    def __init__(self, host: discord.Member, game: str, role: str, max_players: int):
        super().__init__(timeout=3600)
        self.host = host
        self.game = game
        self.role = role
        self.max_players = max_players
        self.players: set[discord.Member] = {host}

    def generate_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"💽 LFG: {self.game}",
            description=f"### Party Finder\n*{self.host.mention} is looking for players!*\n\n**Requested Role:** *{self.role}*",
            color=0x00FFFF if len(self.players) < self.max_players else 0xFF003C
        )
        player_mentions = "\n".join([f"🔵 *{p.mention}*" for p in self.players])
        embed.add_field(name=f"Players ({len(self.players)}/{self.max_players})", value=player_mentions, inline=False)
        if len(self.players) >= self.max_players:
            embed.set_footer(text="Party is full! 🤖")
        else:
            embed.set_footer(text="Click Join to hop in! ✅")
        return embed

    @discord.ui.button(label="Join", style=discord.ButtonStyle.success, custom_id="lfg_join")
    async def join_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.players) >= self.max_players:
            await interaction.response.send_message("*Party is already full!*", ephemeral=True)
            return
        if interaction.user in self.players:
            await interaction.response.send_message("*You are already in the party!*", ephemeral=True)
            return
        self.players.add(interaction.user)
        if len(self.players) >= self.max_players:
            button.disabled = True
        await interaction.response.edit_message(embed=self.generate_embed(), view=self)

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.danger, custom_id="lfg_leave")
    async def leave_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.players:
            await interaction.response.send_message("*You aren't in this party.*", ephemeral=True)
            return
        if interaction.user == self.host:
            await interaction.response.send_message("*The host cannot leave. Please dismiss the group instead.*", ephemeral=True)
            return
        self.players.remove(interaction.user)
        self.join_btn.disabled = False
        await interaction.response.edit_message(embed=self.generate_embed(), view=self)


def register(bot, data_dir=None):
    if bot.tree.get_command("gaming"):
        return

    gaming_group = app_commands.Group(name="gaming", description="Gaming stats, LFG, and history")

    @gaming_group.command(name="lfg", description="Create a Looking For Group post.")
    async def lfg(interaction: discord.Interaction, game: str, role: str, max_players: int):
        view = LFGView(host=interaction.user, game=game, role=role, max_players=max_players)
        await interaction.response.send_message(embed=view.generate_embed(), view=view)

    @gaming_group.command(name="stats", description="Fetch player statistics for a game.")
    async def stats(interaction: discord.Interaction, game: str, username: str):
        embed = discord.Embed(title=f"👨‍💻 {username}'s Stats in {game.title()}", color=0x00FFFF)
        embed.description = "### Performance Metrics\n*Latest competitive season data.*"
        embed.add_field(name="Win Rate", value="*54.2%*", inline=True)
        embed.add_field(name="K/D Ratio", value="*1.18*", inline=True)
        embed.set_footer(text="Stat Tracker")
        await interaction.response.send_message(embed=embed)

    @gaming_group.command(name="today-in-history", description="Discover what happened today in gaming history.")
    async def today_in_history(interaction: discord.Interaction):
        events = [
            "💽 **1996:** *Nintendo 64 was officially released in Japan.*",
            "👨‍💻 **2011:** *Minecraft reached 10 million registered users.*",
            "📘 **2004:** *Half-Life 2 was officially announced to be completed.*"
        ]
        embed = discord.Embed(title="📘 Today in Gaming History", description=f"### Historical Archive\n{random.choice(events)}", color=0x00FFFF)
        await interaction.response.send_message(embed=embed)

    @gaming_group.command(name="indie-discovery", description="Discover a hidden gem indie game.")
    async def indie_discovery(interaction: discord.Interaction):
        embed = discord.Embed(title="🌌 Indie Gem: Hollow Knight", color=0x002147)
        embed.description = "### Metroidvania Masterpiece\n*Forge your own path in Hollow Knight! An epic action adventure through a vast ruined kingdom of insects and heroes.*"
        embed.add_field(name="Rating", value="*Overwhelmingly Positive* ✅", inline=True)
        await interaction.response.send_message(embed=embed)

    @gaming_group.command(name="collection", description="Check the retro market price for a game/console.")
    async def collection(interaction: discord.Interaction, item: str):
        embed = discord.Embed(title=f"💽 Market Value: {item.title()}", color=0x002147)
        embed.description = "### Retro Market Prices\n*Current estimated valuation for collectors.*"
        embed.add_field(name="Loose Price", value="*$45.00*", inline=True)
        embed.add_field(name="Complete in Box", value="*$115.50*", inline=True)
        await interaction.response.send_message(embed=embed)

    bot.tree.add_command(gaming_group)

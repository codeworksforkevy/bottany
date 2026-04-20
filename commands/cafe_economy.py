from __future__ import annotations
import discord
import random
from discord import app_commands

economy_db = {}

def get_user_data(user_id: int) -> dict:
    if user_id not in economy_db:
        economy_db[user_id] = {
            "balance": 7000, 
            "debt_fed": 0,
            "debt_kevin": 0
        }
    return economy_db[user_id]

LIMIT_FED = 5000
LIMIT_KEVIN = 10000

CHEFS = ["Kevy", "Keats", "Jordan", "Extinct", "Sim", "G", "Kenny"]

ASCII_ARTS = [
    # 1. Classic Coffee
    r"""
         )))
        (((
      +-----+
      |     |]
      `-----'
    """,
    # 2. 180 Degree Pizza Slice
    r"""
     .-----------.
     \___________/
      \ o  o  o /
       \ o   o /
        \  o  /
         \ o /
          \ /
           '
    """,
    # 3. Classic Pasta Bowl
    r"""
            \ | /
          '-..-..-'
          /_\/_\/_\
          \_______/
    """,
    # 4. The Regency Cafe - Tetley Tea
    r"""
         (  )   (   )
          ) (   )  (
        .-------------.
        |   TETLEY    |.-.
        |   CLASSIC   |  |
        `-------------'`-'
    """
]

# TODAY'S MENU - THE GINA, CALI & BELGIAN EXPEDITION (25 Items Max)
MENU = {
    # Morning Brews & Bakery
    "espresso": {"name": "Espresso al Banco", "price": 2, "emoji": "☕"},
    "wc_mocha": {"name": "White Chocolate Mocha", "price": 6, "emoji": "☕"},
    "tetley_tea": {"name": "The Regency Cafe Tetley Tea", "price": 2, "emoji": "🫖"},
    "blue_bottle": {"name": "Blue Bottle New Orleans Iced (CA)", "price": 6, "emoji": "🧊"},
    "tartine_bun": {"name": "Tartine Bakery Morning Bun (SF)", "price": 6, "emoji": "🧁"},
    "dandoy_waffle": {"name": "Maison Dandoy Liege Waffle (Brussels)", "price": 8, "emoji": "🧇"},
    
    # Gina Istanbul - Italian Elegance
    "gina_burrata": {"name": "Gina Burrata con Pomodorini (Istanbul)", "price": 18, "emoji": "🧀"},
    "gina_carpaccio": {"name": "Gina Carpaccio di Manzo (Istanbul)", "price": 22, "emoji": "🥩"},
    "gina_risotto": {"name": "Gina Risotto ai Funghi Porcini", "price": 26, "emoji": "🥘"},
    "gina_lobster": {"name": "Gina Linguine all'Astice", "price": 38, "emoji": "🍝"},
    "gina_tiramisu": {"name": "Gina Tiramisu Tradizionale", "price": 12, "emoji": "🍰"},
    
    # California Culinary Journey
    "innout_burger": {"name": "In-N-Out Double-Double (CA)", "price": 5, "emoji": "🍔"},
    "malibu_toast": {"name": "Malibu Farm Avocado Toast (CA)", "price": 16, "emoji": "🥑"},
    "boudin_chowder": {"name": "Boudin Clam Chowder Sourdough (SF)", "price": 12, "emoji": "🍲"},
    "spago_pizza": {"name": "Spago Smoked Salmon Pizza (Beverly Hills)", "price": 32, "emoji": "🍕"},
    "nobu_yellowtail": {"name": "Nobu Malibu Yellowtail Jalapeño", "price": 32, "emoji": "🍱"},
    "providence_salmon": {"name": "Providence Wild King Salmon (LA)", "price": 65, "emoji": "🐟"},
    
    # Belgian Classics & Sweets
    "chez_leon": {"name": "Chez Léon Moules-Frites (Brussels)", "price": 28, "emoji": "🦪"},
    "fritland": {"name": "Fritland Belgian Fries with Andalouse", "price": 6, "emoji": "🍟"},
    "marcolini_box": {"name": "Pierre Marcolini Praline Box (Brussels)", "price": 45, "emoji": "🍫"},
    "neuhaus_truffles": {"name": "Neuhaus Artisanal Truffles", "price": 35, "emoji": "🍫"},
    "ghirardelli": {"name": "Ghirardelli Hot Fudge Sundae (SF)", "price": 15, "emoji": "🍨"},
    
    # The Cellar & Taphouse
    "delirium_ale": {"name": "Delirium Tremens Blonde Ale (Brussels)", "price": 8, "emoji": "🍺"},
    "cantillon": {"name": "Cantillon Gueuze Lambic Beer (Brussels)", "price": 12, "emoji": "🍻"},
    "opus_one": {"name": "Opus One 2018 Napa Valley (Glass)", "price": 95, "emoji": "🍷"}
}

def register(bot: discord.Client, data_dir: str = None) -> None:
    if bot.tree.get_command("cafe"):
        return

    cafe_group = app_commands.Group(name="cafe", description="The International Bottany Cafe & Bakery")
    bank_group = app_commands.Group(name="bank", description="Kevin Bottany & Co. and Federal Reserve")

    # =====================================================================
    # ☕ CAFE COMMANDS
    # =====================================================================
    @cafe_group.command(name="menu", description="View the international menu and daily specials.")
    async def menu(interaction: discord.Interaction):
        embed = discord.Embed(title="☕ The Bottany Cafe Menu", color=0x002147)
        
        selected_ascii = random.choice(ASCII_ARTS).strip("\n")
        ascii_block = f"```text\n{selected_ascii}\n```"
        
        embed.description = f"### Today's Global Selection\n*Authentic culinary experiences sourced from world-renowned restaurants.*\n{ascii_block}"
        
        morning_brews = (
            f"☕ **Espresso / White Choc Mocha** — *$ 2 / $ 6*\n"
            f"🫖 **The Regency Cafe Tetley Tea** — *$ 2*\n"
            f"🧊 **Blue Bottle New Orleans Iced Coffee** (CA) — *$ 6*\n"
            f"🧁 **Tartine Bakery Morning Bun** (SF) — *$ 6*\n"
            f"🧇 **Maison Dandoy Liege Waffle** (Brussels) — *$ 8*"
        )
        embed.add_field(name="Morning Bakery & Brews", value=morning_brews, inline=False)

        gina_istanbul = (
            f"🧀 **Gina Burrata con Pomodorini** — *$ 18*\n"
            f"🥩 **Gina Carpaccio di Manzo** — *$ 22*\n"
            f"🥘 **Gina Risotto ai Funghi Porcini** — *$ 26*\n"
            f"🍝 **Gina Linguine all'Astice** — *$ 38*\n"
            f"🍰 **Gina Tiramisu Tradizionale** — *$ 12*"
        )
        embed.add_field(name="Gina Istanbul - Italian Elegance", value=gina_istanbul, inline=False)

        california_journey = (
            f"🍔 **In-N-Out Double-Double** (CA) — *$ 5*\n"
            f"🥑 **Malibu Farm Avocado Toast** — *$ 16*\n"
            f"🍲 **Boudin Clam Chowder Sourdough** (SF) — *$ 12*\n"
            f"🍕 **Spago Smoked Salmon Pizza** (Beverly Hills) — *$ 32*\n"
            f"🍱 **Nobu Malibu Yellowtail Jalapeño** — *$ 32*\n"
            f"🐟 **Providence Wild King Salmon** (LA) — *$ 65*"
        )
        embed.add_field(name="California Culinary Journey", value=california_journey, inline=False)

        belgian_classics = (
            f"🦪 **Chez Léon Moules-Frites** (Brussels) — *$ 28*\n"
            f"🍟 **Fritland Belgian Fries with Andalouse** — *$ 6*\n"
            f"🍫 **Pierre Marcolini Praline Box** (Brussels) — *$ 45*\n"
            f"🍫 **Neuhaus Artisanal Truffles** — *$ 35*\n"
            f"🍨 **Ghirardelli Hot Fudge Sundae** (SF) — *$ 15*"
        )
        embed.add_field(name="Belgian Classics & Sweets", value=belgian_classics, inline=False)

        cellar_taphouse = (
            f"🍺 **Delirium Tremens Blonde Ale** (Brussels) — *$ 8*\n"
            f"🍻 **Cantillon Gueuze Lambic Beer** — *$ 12*\n"
            f"🍷 **Opus One 2018 Napa Valley** (Glass) — *$ 95*"
        )
        embed.add_field(name="The Cellar & Taphouse", value=cellar_taphouse, inline=False)
        
        embed.set_footer(text="Order with /cafe buy ✍")
        await interaction.response.send_message(embed=embed)

    @cafe_group.command(name="buy", description="Buy food or drinks for yourself or treat a friend!")
    @app_commands.choices(item=[app_commands.Choice(name=v["name"], value=k) for k, v in MENU.items()])
    async def buy(interaction: discord.Interaction, item: str, friend: discord.Member = None):
        buyer_data = get_user_data(interaction.user.id)
        selected = MENU[item]
        cost = selected["price"]

        if buyer_data["balance"] < cost:
            await interaction.response.send_message(f"*Your card was declined. 💳 Try taking a loan from the bank!* 🤖", ephemeral=True)
            return

        buyer_data["balance"] -= cost
        emoji = selected["emoji"]
        chef = random.choice(CHEFS)

        embed = discord.Embed(color=0xF9F6EE)
        if friend and friend.id != interaction.user.id:
            embed.description = f"### A Generous Gift!\n*{interaction.user.mention} has graciously treated {friend.mention} to a {selected['name']}!* {emoji}\n\n*Transaction: $ {cost}* 💳"
        else:
            embed.description = f"### Bon Appétit!\n*{interaction.user.mention} ordered the {selected['name']}. Enjoy!* {emoji}\n\n*Transaction: $ {cost}* 💳"
            
        embed.set_footer(text=f"Prepared with care by Chef {chef} 👨‍💻")
        await interaction.response.send_message(embed=embed)

    # =====================================================================
    # 🏦 BANKING COMMANDS
    # =====================================================================
    @bank_group.command(name="balance", description="Check your Kevy Dollars and outstanding debt.")
    async def balance(interaction: discord.Interaction):
        user_data = get_user_data(interaction.user.id)
        embed = discord.Embed(title="📘 Account Overview", color=0x002147)
        embed.description = f"### Financial Status\n*Current holdings and lines of credit for {interaction.user.name}.*"
        embed.add_field(name="Kevy Dollars", value=f"*$ {user_data['balance']}* 🪙", inline=False)
        embed.add_field(name="Debt: Bottany Federal Reserve", value=f"*$ {user_data['debt_fed']} / {LIMIT_FED}* 💳", inline=True)
        embed.add_field(name="Debt: Kevin Bottany & Co.", value=f"*$ {user_data['debt_kevin']} / {LIMIT_KEVIN}* 💳", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bank_group.command(name="loan", description="Take a loan from the prestigious banking institutions.")
    @app_commands.choices(bank=[
        app_commands.Choice(name="The Bottany Federal Reserve", value="fed"),
        app_commands.Choice(name="Kevin Bottany & Co.", value="kevin")
    ])
    async def loan(interaction: discord.Interaction, bank: str, amount: int):
        user_data = get_user_data(interaction.user.id)
        
        if amount <= 0:
            await interaction.response.send_message("*Invalid loan amount.* 🤖", ephemeral=True)
            return

        if bank == "fed":
            if user_data["debt_fed"] + amount > LIMIT_FED:
                await interaction.response.send_message(f"*Loan denied by The Bottany Federal Reserve. You exceed the credit limit of $ {LIMIT_FED}.* 📕", ephemeral=True)
                return
            user_data["debt_fed"] += amount
            bank_name = "The Bottany Federal Reserve"
            
        elif bank == "kevin":
            if user_data["debt_kevin"] + amount > LIMIT_KEVIN:
                await interaction.response.send_message(f"*Loan denied by Kevin Bottany & Co. You exceed the credit limit of $ {LIMIT_KEVIN}.* 📕", ephemeral=True)
                return
            user_data["debt_kevin"] += amount
            bank_name = "Kevin Bottany & Co."

        user_data["balance"] += amount
        
        embed = discord.Embed(color=0x002147)
        embed.description = f"### Loan Approved\n*A loan of $ {amount} 🪙 has been successfully credited to your account by {bank_name}.*\n\n*Please ensure timely repayments to maintain your financial standing.* ✅"
        embed.set_footer(text="Bottany Financial Services 🖲️")
        await interaction.response.send_message(embed=embed)

    @bank_group.command(name="public_reminder", description="Admin only: Publicly remind a user of their debt.")
    @app_commands.default_permissions(manage_guild=True)
    async def public_reminder(interaction: discord.Interaction, member: discord.Member):
        user_data = get_user_data(member.id)
        total_debt = user_data["debt_fed"] + user_data["debt_kevin"]
        
        if total_debt == 0:
            await interaction.response.send_message("*This user has no outstanding debts.* ✅", ephemeral=True)
            return
            
        embed = discord.Embed(title="📘 Public Financial Notice", color=0x002147)
        embed.description = f"### Debt Collection\n*It has come to our attention that {member.mention} still owes a total of **$ {total_debt}** 💳 to our institutions.*\n\n*We politely request you settle your debts to maintain your high-society status in the server!* 🤖"
        await interaction.response.send_message(embed=embed)

    bot.tree.add_command(cafe_group)
    bot.tree.add_command(bank_group)

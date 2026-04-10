from __future__ import annotations
import discord
import random
from discord import app_commands

# Basit bir bellek-içi veritabanı
economy_db = {}

def get_user_data(user_id: int) -> dict:
    if user_id not in economy_db:
        economy_db[user_id] = {
            "balance": 7000, 
            "debt_fed": 0,
            "debt_kevin": 0
        }
    return economy_db[user_id]

# Kredi Limitleri
LIMIT_FED = 5000
LIMIT_KEVIN = 10000

# Şef Rotasyonu
CHEFS = ["Kevy", "Keats", "Jordan", "Extinct", "Sim", "G", "Kenny"]

# Rastgele ASCII Görselleri (Jilet gibi hizalanmış)
ASCII_ARTS = [
    # 1. Klasik Kahve
    r"""
         )))
        (((
      +-----+
      |     |]
      `-----'
    """,
    # 2. 180 Derece Döndürülmüş Üçgen Pizza
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
    # 3. Klasik Kase Makarna
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

# GÜNÜN MENÜSÜ (Tam 25 Ürün - Discord Limiti)
MENU = {
    # Coffee, Tea & Morning Pastries
    "espresso": {"name": "Espresso al Banco", "price": 2, "emoji": "☕"},
    "wc_mocha": {"name": "White Chocolate Mocha", "price": 6, "emoji": "☕"},
    "tetley_tea": {"name": "The Regency Cafe Tetley Tea", "price": 2, "emoji": "🫖"},
    "cronut": {"name": "Dominique Ansel Cronut (NYC)", "price": 7, "emoji": "🥐"},
    "balthazar": {"name": "Balthazar Butter Croissant", "price": 5, "emoji": "🥐"},
    "beignet": {"name": "Cafe Du Monde Beignets (NOLA)", "price": 4, "emoji": "🍩"},
    
    # Italian Masterpieces
    "diavola": {"name": "Da Michele Pizza Diavola", "price": 8, "emoji": "🍕"},
    "sorbillo": {"name": "Gino Sorbillo Pizza Fritta", "price": 9, "emoji": "🍕"},
    "truffle_gnocchi": {"name": "Trattoria al Forno Truffle Gnocchi", "price": 25, "emoji": "🍝"},
    "parmigiano": {"name": "Osteria Francescana Five Ages of Parmigiano", "price": 90, "emoji": "🍝"},
    
    # Global Fine Dining & Asian
    "nobu_cod": {"name": "Nobu Black Cod Miso", "price": 42, "emoji": "🍱"},
    "jiro_uni": {"name": "Jiro Uni (Sea Urchin) Nigiri", "price": 20, "emoji": "🍣"},
    "dintaifung": {"name": "Din Tai Fung Kurobuta Xiaolongbao", "price": 15, "emoji": "🥟"},
    "peter_luger": {"name": "Peter Luger Dry Aged Steak for Two", "price": 140, "emoji": "🥩"},
    
    # Cult Fast Food
    "shakeshack": {"name": "Shake Shack ShackBurger", "price": 7, "emoji": "🍔"},
    "fiveguys": {"name": "Five Guys Bacon Cheeseburger", "price": 10, "emoji": "🍔"},
    "innout": {"name": "In-N-Out Double-Double", "price": 5, "emoji": "🍔"},
    "kfc_bucket": {"name": "KFC Original Recipe Bucket", "price": 15, "emoji": "🍗"},
    
    # Desserts
    "laduree_ispahan": {"name": "Ladurée Ispahan Macaron", "price": 10, "emoji": "🧁"},
    "berthillon": {"name": "Berthillon Wild Strawberry Sorbet", "price": 8, "emoji": "🍨"},
    "ritz_madeleine": {"name": "Ritz Paris Classic Madeleine", "price": 6, "emoji": "🧁"},
    
    # Signature Cocktails & Wine
    "bellini": {"name": "Harry's Bar Original Bellini", "price": 22, "emoji": "🥂"},
    "hanky_panky": {"name": "The Savoy Hanky Panky Cocktail", "price": 28, "emoji": "🍸"},
    "serendipity": {"name": "Bar Hemingway Serendipity", "price": 35, "emoji": "🍹"},
    "margaux": {"name": "Château Margaux 2015 (Glass)", "price": 150, "emoji": "🍷"}
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
        embed = discord.Embed(title="☕ The Bottany Cafe Menu", color=0xD35400)
        
        selected_ascii = random.choice(ASCII_ARTS).strip("\n")
        ascii_block = f"```text\n{selected_ascii}\n```"
        
        embed.description = f"### Today's Global Selection\n*Authentic culinary experiences sourced from world-renowned restaurants.*\n{ascii_block}"
        
        coffee_pastries = (
            f"☕ **Espresso al Banco** — *$ 2*\n"
            f"🫖 **The Regency Cafe Tetley Tea** — *$ 2*\n"
            f"🥐 **Dominique Ansel Cronut** (NYC) — *$ 7*\n"
            f"🍩 **Cafe Du Monde Beignets** (New Orleans) — *$ 4*"
        )
        embed.add_field(name="Morning Bakery & Brews", value=coffee_pastries, inline=False)

        italian_fine = (
            f"🍕 **Da Michele Pizza Diavola** (Naples) — *$ 8*\n"
            f"🍝 **Osteria Francescana Five Ages of Parmigiano** — *$ 90*\n"
            f"🍱 **Nobu Black Cod Miso** — *$ 42*\n"
            f"🥩 **Peter Luger Dry Aged Steak for Two** — *$ 140*"
        )
        embed.add_field(name="Michelin & Italian Masterpieces", value=italian_fine, inline=False)

        fast_food = (
            f"🍔 **In-N-Out Double-Double** — *$ 5*\n"
            f"🍔 **Five Guys Bacon Cheeseburger** — *$ 10*\n"
            f"🍗 **KFC Original Recipe Bucket** — *$ 15*"
        )
        embed.add_field(name="Cult Classics & Fast Food", value=fast_food, inline=False)

        bar_desserts = (
            f"🥂 **Harry's Bar Original Bellini** (Venice) — *$ 22*\n"
            f"🍷 **Château Margaux 2015** (Glass) — *$ 150*\n"
            f"🧁 **Ladurée Ispahan Macaron** (Paris) — *$ 10*"
        )
        embed.add_field(name="The Cellar & Desserts", value=bar_desserts, inline=False)
        
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

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

# TODAY'S MENU - FRANCO-ITALIAN TIRAMISU TASTING (25 Items Max)
MENU = {
    # Morning Brews & Classics
    "espresso": {"name": "Espresso al Banco", "price": 2, "emoji": "☕"},
    "wc_mocha": {"name": "White Chocolate Mocha", "price": 6, "emoji": "☕"},
    "tetley_tea": {"name": "The Regency Cafe Tetley Tea", "price": 2, "emoji": "🫖"},
    "angelina_hc": {"name": "Angelina Paris Hot Chocolate", "price": 10, "emoji": "☕"},
    
    # The Tiramisu Tasting Collection (8 Unique Establishments)
    "tiramisu_pompi": {"name": "Bar Pompi Classic Tiramisu (Rome)", "price": 6, "emoji": "🍰"},
    "tiramisu_enzo": {"name": "Da Enzo al 29 Artisanal Tiramisu (Rome)", "price": 8, "emoji": "🍰"},
    "tiramisu_beccherie": {"name": "Le Beccherie Original Tiramisu (Treviso)", "price": 10, "emoji": "🍰"},
    "tiramisu_massari": {"name": "Iginio Massari Tiramisu (Milan)", "price": 15, "emoji": "🍰"},
    "tiramisu_alfonso": {"name": "Don Alfonso 1890 Tiramisu (Campania) [**]", "price": 25, "emoji": "🍰"},
    "tiramisu_palagio": {"name": "Il Palagio Tiramisu (Florence) [*]", "price": 30, "emoji": "🍰"},
    "tiramisu_duomo": {"name": "Piazza Duomo Tiramisu (Alba) [***]", "price": 35, "emoji": "🍰"},
    "tiramisu_osteria": {"name": "Osteria Francescana Tiramisu (Modena) [***]", "price": 45, "emoji": "🍰"},
    
    # French & Italian Fine Dining (No Fowl/Snails)
    "chartier_soup": {"name": "Bouillon Chartier French Onion Soup (Paris)", "price": 8, "emoji": "🍲"},
    "cotedor_ratatouille": {"name": "La Côte d'Or Ratatouille (Burgundy) [**]", "price": 45, "emoji": "🥗"},
    "entrecote_steak": {"name": "Le Relais de l'Entrecôte Steak Frites (Paris)", "price": 35, "emoji": "🥩"},
    "ducasse_risotto": {"name": "Alain Ducasse Truffle Risotto (Paris) [***]", "price": 110, "emoji": "🥘"},
    "da_michele": {"name": "Da Michele Margherita (Naples)", "price": 7, "emoji": "🍕"},
    "roscioli_carbonara": {"name": "Roscioli Traditional Carbonara (Rome)", "price": 20, "emoji": "🍝"},
    "pinchiorri_ravioli": {"name": "Enoteca Pinchiorri Artisanal Ravioli [***]", "price": 90, "emoji": "🍝"},
    "reale_veal": {"name": "Reale Veal Milanese (Castel di Sangro) [***]", "price": 120, "emoji": "🥩"},
    
    # The Cellar & Parisian Pastries
    "grolet_eclair": {"name": "Cédric Grolet Vanilla Eclair (Paris)", "price": 15, "emoji": "🧁"},
    "laduree_ispahan": {"name": "Ladurée Ispahan Macaron (Paris)", "price": 10, "emoji": "🧁"},
    "harrys_bellini": {"name": "Harry's Bar Original Bellini (Venice)", "price": 22, "emoji": "🥂"},
    "margaux_wine": {"name": "Château Margaux 2015 (Glass)", "price": 150, "emoji": "🍷"},
    "barolo_wine": {"name": "Barolo Monfortino 2013 (Glass)", "price": 180, "emoji": "🍷"}
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
            f"☕ **Angelina Paris Hot Chocolate** — *$ 10*"
        )
        embed.add_field(name="Morning Bakery & Brews", value=morning_brews, inline=False)

        tiramisu_tasting = (
            f"🍰 **Bar Pompi Classic Tiramisu** (Rome) — *$ 6*\n"
            f"🍰 **Da Enzo al 29 Artisanal Tiramisu** (Rome) — *$ 8*\n"
            f"🍰 **Le Beccherie Original Tiramisu** (Treviso) — *$ 10*\n"
            f"🍰 **Iginio Massari Tiramisu** (Milan) — *$ 15*\n"
            f"🍰 **Don Alfonso 1890 Tiramisu** [**] — *$ 25*\n"
            f"🍰 **Il Palagio Tiramisu** (Florence) [*] — *$ 30*\n"
            f"🍰 **Piazza Duomo Tiramisu** (Alba) [***] — *$ 35*\n"
            f"🍰 **Osteria Francescana Tiramisu** [***] — *$ 45*"
        )
        embed.add_field(name="The Tiramisu Tasting Collection", value=tiramisu_tasting, inline=False)

        fine_dining = (
            f"🍲 **Bouillon Chartier French Onion Soup** — *$ 8*\n"
            f"🥩 **Le Relais de l'Entrecôte Steak Frites** — *$ 35*\n"
            f"🥘 **Alain Ducasse Truffle Risotto** [***] — *$ 110*\n"
            f"🥗 **La Côte d'Or Ratatouille** [**] — *$ 45*\n"
            f"🍕 **Da Michele Margherita** (Naples) — *$ 7*\n"
            f"🍝 **Roscioli Traditional Carbonara** — *$ 20*\n"
            f"🍝 **Enoteca Pinchiorri Artisanal Ravioli** [***] — *$ 90*\n"
            f"🥩 **Reale Veal Milanese** [***] — *$ 120*"
        )
        embed.add_field(name="French & Italian Fine Dining", value=fine_dining, inline=False)

        cellar_desserts = (
            f"🧁 **Cédric Grolet Vanilla Eclair** (Paris) — *$ 15*\n"
            f"🧁 **Ladurée Ispahan Macaron** (Paris) — *$ 10*\n"
            f"🥂 **Harry's Bar Original Bellini** (Venice) — *$ 22*\n"
            f"🍷 **Château Margaux 2015** (Glass) — *$ 150*\n"
            f"🍷 **Barolo Monfortino 2013** (Glass) — *$ 180*"
        )
        embed.add_field(name="The Cellar & Parisian Pastries", value=cellar_desserts, inline=False)
        
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

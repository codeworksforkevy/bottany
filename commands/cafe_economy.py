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

# TODAY's MENU - THE GLOBAL EXPEDITION (25 Items Max)
MENU = {
    # Coffee, Tea & Bakery
    "espresso": {"name": "Espresso al Banco", "price": 2, "emoji": "☕"},
    "wc_mocha": {"name": "White Chocolate Mocha", "price": 6, "emoji": "☕"},
    "tetley_tea": {"name": "The Regency Cafe Tetley Tea", "price": 2, "emoji": "🫖"},
    "matcha": {"name": "Koffee Mameya Matcha Latte (Tokyo)", "price": 6, "emoji": "🍵"},
    "pasteis": {"name": "Pastéis de Belém (Lisbon)", "price": 2, "emoji": "🥧"},
    "russ_bagel": {"name": "Russ & Daughters Lox Bagel (NYC)", "price": 15, "emoji": "🥯"},
    
    # Global Street Food
    "baja_taco": {"name": "La Guerrerense Fish Taco (Ensenada)", "price": 4, "emoji": "🌮"},
    "banh_mi": {"name": "Bánh Mì Phượng Sandwich (Hoi An)", "price": 2, "emoji": "🥖"},
    "currywurst": {"name": "Curry 36 Currywurst & Fries (Berlin)", "price": 6, "emoji": "🌭"},
    "schwartz_meat": {"name": "Schwartz's Smoked Meat (Montreal)", "price": 12, "emoji": "🥪"},
    "smashburger": {"name": "7th Street Burger (NYC)", "price": 7, "emoji": "🍔"},
    
    # World Masterpieces & Fine Dining
    "yaprak_sarma": {"name": "Karaköy Lokantası Yaprak Sarma", "price": 8, "emoji": "🌿"},
    "shabu_shabu": {"name": "Imahan Wagyu Shabu-Shabu (Tokyo)", "price": 90, "emoji": "🍲"},
    "ceviche": {"name": "Astrid y Gastón Ceviche Clásico (Lima)", "price": 28, "emoji": "🥗"},
    "peking_duck": {"name": "Quanjude Peking Duck Half (Beijing)", "price": 40, "emoji": "🦆"},
    "paella": {"name": "Casa Carmela Paella Valenciana (Spain)", "price": 45, "emoji": "🥘"},
    "wellington": {"name": "Savoy Grill Beef Wellington (London)", "price": 65, "emoji": "🥩"},
    
    # World Famous Desserts
    "baklava": {"name": "Karaköy Güllüoğlu Pistachio Baklava", "price": 8, "emoji": "🥮"},
    "tiramisu": {"name": "Bar Pompi Classic Tiramisu (Rome)", "price": 6, "emoji": "🍰"},
    "basque_cake": {"name": "La Viña Basque Cheesecake (San Sebastian)", "price": 8, "emoji": "🍰"},
    
    # Iconic Cellar & Bar
    "singapore_sling": {"name": "Raffles Hotel Singapore Sling", "price": 30, "emoji": "🍹"},
    "old_fashioned": {"name": "The Dead Rabbit Old Fashioned (NYC)", "price": 20, "emoji": "🥃"},
    "aperol_spritz": {"name": "Caffè Florian Aperol Spritz (Venice)", "price": 18, "emoji": "🥂"},
    "lafite": {"name": "Château Lafite Rothschild 2010 (Glass)", "price": 200, "emoji": "🍷"}
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
        
        morning_brews = (
            f"☕ **Espresso / White Choc Mocha** — *$ 2 / $ 6*\n"
            f"🫖 **The Regency Cafe Tetley Tea** — *$ 2*\n"
            f"🍵 **Koffee Mameya Matcha Latte** (Tokyo) — *$ 6*\n"
            f"🥯 **Russ & Daughters Lox Bagel** (NYC) — *$ 15*\n"
            f"🥧 **Pastéis de Belém** (Lisbon) — *$ 2*"
        )
        embed.add_field(name="Morning Bakery & Brews", value=morning_brews, inline=False)

        street_food = (
            f"🍔 **7th Street Smashburger** (NYC) — *$ 7*\n"
            f"🥪 **Schwartz's Smoked Meat** (Montreal) — *$ 12*\n"
            f"🌭 **Curry 36 Currywurst & Fries** (Berlin) — *$ 6*\n"
            f"🌮 **La Guerrerense Fish Taco** (Ensenada) — *$ 4*\n"
            f"🥖 **Bánh Mì Phượng Sandwich** (Hoi An) — *$ 2*"
        )
        embed.add_field(name="Global Street Food & Deli", value=street_food, inline=False)

        fine_dining = (
            f"🥩 **Savoy Grill Beef Wellington** (London) — *$ 65*\n"
            f"🍲 **Imahan Wagyu Shabu-Shabu** (Tokyo) — *$ 90*\n"
            f"🦆 **Quanjude Peking Duck Half** (Beijing) — *$ 40*\n"
            f"🥘 **Casa Carmela Paella Valenciana** — *$ 45*\n"
            f"🌿 **Karaköy Lokantası Yaprak Sarma** (Istanbul) — *$ 8*\n"
            f"🥗 **Astrid y Gastón Ceviche Clásico** (Lima) — *$ 28*"
        )
        embed.add_field(name="World Masterpieces & Fine Dining", value=fine_dining, inline=False)

        cellar_desserts = (
            f"🍷 **Château Lafite Rothschild 2010** — *$ 200*\n"
            f"🍹 **Raffles Hotel Singapore Sling** — *$ 30*\n"
            f"🥃 **The Dead Rabbit Old Fashioned** (NYC) — *$ 20*\n"
            f"🥂 **Caffè Florian Aperol Spritz** (Venice) — *$ 18*\n"
            f"🥮 **Karaköy Güllüoğlu Pistachio Baklava** — *$ 8*\n"
            f"🍰 **La Viña Basque Cheesecake** — *$ 8*\n"
            f"🍰 **Bar Pompi Classic Tiramisu** (Rome) — *$ 6*"
        )
        embed.add_field(name="The Cellar & Desserts", value=cellar_desserts, inline=False)
        
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

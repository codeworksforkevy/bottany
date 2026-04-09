from __future__ import annotations
import discord
import random
from discord import app_commands

# Basit bir bellek-içi veritabanı (Bunu daha sonra PostgreSQL bot.db'ne bağlayabilirsin)
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

# Rastgele ASCII Görselleri (Sıfır kayma için Raw String formatı)
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

# Küresel Menü (Gerçek dünya fiyatları ve mekanları)
MENU = {
    # Coffee, Tea & Bar
    "espresso": {"name": "Espresso al Banco", "price": 2, "emoji": "☕"},
    "wc_mocha": {"name": "White Chocolate Mocha", "price": 6, "emoji": "☕"},
    "tetley_tea": {"name": "The Regency Cafe Tetley Tea", "price": 2, "emoji": "🫖"},
    "martini": {"name": "Classic Dry Martini", "price": 25, "emoji": "🍸"},
    
    # Japanese Sushi (Michelin Starred)
    "jiro_omakase": {"name": "Sukiyabashi Jiro Omakase", "price": 300, "emoji": "🍣"},
    "saito_nigiri": {"name": "Sushi Saito Nigiri Set", "price": 150, "emoji": "🍣"},
    
    # Belgian Chocolates & Ice Cream
    "godiva_choc": {"name": "Godiva Dark Chocolate Gelato", "price": 9, "emoji": "🍦"},
    "vanilla_bean": {"name": "Madagascar Vanilla Ice Cream", "price": 8, "emoji": "🍨"},
    "marcolini_box": {"name": "Pierre Marcolini Box", "price": 45, "emoji": "🍫"},
    
    # UK Breakfast, Tea & Waffles
    "uk_pancakes": {"name": "The Breakfast Club Pancakes", "price": 15, "emoji": "🥞"},
    "uk_crepe": {"name": "My Old Dutch Classic Crepe", "price": 13, "emoji": "🥞"},
    "belgian_waffle": {"name": "Brussels Authentic Waffle", "price": 11, "emoji": "🧇"},
    
    # Italian Classics
    "margherita": {"name": "Da Michele Margherita", "price": 7, "emoji": "🍕"},
    "carbonara": {"name": "Roscioli Traditional Carbonara", "price": 20, "emoji": "🍝"},
    "cacioepepe": {"name": "Da Enzo Cacio e Pepe", "price": 15, "emoji": "🍝"},
    
    # Fast Food
    "baconator": {"name": "Wendy's Baconator", "price": 9, "emoji": "🍔"},
    "spicy_chicken": {"name": "Wendy's Spicy Chicken", "price": 7, "emoji": "🍔"},
    "frosty": {"name": "Wendy's Classic Frosty", "price": 3, "emoji": "🥤"}
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
        
        # ASCII çizimini rastgele seç ve başındaki/sonundaki boşlukları temizle
        selected_ascii = random.choice(ASCII_ARTS).strip("\n")
        ascii_block = f"```text\n{selected_ascii}\n```"
        
        embed.description = f"### Today's Selection\n{ascii_block}"
        
        coffee_sweets = (
            f"☕ **White Chocolate Mocha** — *$ 6*\n"
            f"🍦 **Godiva Dark Choc Gelato** (Belgium) — *$ 9*\n"
            f"🍫 **Pierre Marcolini Box** (Brussels) — *$ 45*"
        )
        embed.add_field(name="Cafe & Desserts", value=coffee_sweets, inline=False)

        asian_cuisine = (
            f"🍣 **Sukiyabashi Jiro Omakase** (Tokyo) — *$ 300*\n"
            f"🍣 **Sushi Saito Nigiri Set** (Tokyo) — *$ 150*"
        )
        embed.add_field(name="Japanese Fine Dining", value=asian_cuisine, inline=False)

        brunch_tea = (
            f"🫖 **The Regency Cafe Tetley Tea** (London) — *$ 2*\n"
            f"🥞 **The Breakfast Club Pancakes** (London) — *$ 15*\n"
            f"🧇 **Brussels Authentic Waffle** — *$ 11*"
        )
        embed.add_field(name="UK Brunch & Traditional Tea", value=brunch_tea, inline=False)

        italian = (
            f"🍕 **Da Michele Margherita** (Naples) — *$ 7*\n"
            f"🍝 **Roscioli Traditional Carbonara** (Rome) — *$ 20*"
        )
        embed.add_field(name="Italian Classics", value=italian, inline=False)

        fast_food = (
            f"🍔 **Wendy's Baconator** — *$ 9*\n"
            f"🥤 **Wendy's Classic Frosty** — *$ 3*"
        )
        embed.add_field(name="Fast Food Favorites", value=fast_food, inline=False)
        
        embed.set_footer(text="Order with /cafe buy ✍")
        await interaction.response.send_message(embed=embed)

    @cafe_group.command(name="buy", description="Buy food or drinks for yourself or treat a friend!")
    @app_commands.choices(item=[app_commands.Choice(name=v["name"], value=k) for k, v in MENU.items()][:25])
    async def buy(interaction: discord.Interaction, item: str, friend: discord.Member = None):
        buyer_data = get_user_data(interaction.user.id)
        selected = MENU[item]
        cost = selected["price"]

        if buyer_data["balance"] < cost:
            await interaction.response.send_message(f"*Your card was declined. 💳 Try taking a loan from the bank?* 🤖", ephemeral=True)
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

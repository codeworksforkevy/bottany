from __future__ import annotations
import discord
from discord import app_commands

# Basit bir bellek-içi veritabanı (Bunu daha sonra PostgreSQL bot.db'ne bağlayabilirsin)
economy_db = {}

def get_user_data(user_id: int) -> dict:
    if user_id not in economy_db:
        economy_db[user_id] = {
            "balance": 7000, # Başlangıç bakiyesi 7000 Kevy Dollars
            "debt_fed": 0,
            "debt_kevin": 0
        }
    return economy_db[user_id]

# Kredi Limitleri
LIMIT_FED = 5000
LIMIT_KEVIN = 10000

MENU = {
    "espresso": {"name": "Espresso al Banco", "price": 2, "emoji": "☕"},
    "pizza": {"name": "Authentic Naples Margherita", "price": 7, "emoji": "☼"},
    "eclair": {"name": "Parisian Pistachio Éclair", "price": 8, "emoji": "🧁"},
    "macaron": {"name": "Ladurée Macaron Box", "price": 42, "emoji": "🧁"},
    "laundry": {"name": "The French Laundry 13-Course", "price": 390, "emoji": "🥂"},
    "osteria": {"name": "Osteria Francescana Tasting", "price": 380, "emoji": "🍾"},
    "pairing": {"name": "Osteria Wine Pairing", "price": 230, "emoji": "🍸"},
    "martini": {"name": "Classic Dry Martini", "price": 25, "emoji": "🍸"}
}

def register(bot: discord.Client, data_dir: str = None) -> None:
    if bot.tree.get_command("cafe"):
        return

    cafe_group = app_commands.Group(name="cafe", description="The Michelin-starred Bottany Cafe & Bakery")
    bank_group = app_commands.Group(name="bank", description="Kevin Bottany & Co. and Federal Reserve")

    # =====================================================================
    # ☕ CAFE COMMANDS
    # =====================================================================
    @cafe_group.command(name="menu", description="View the menu of the day and Michelin selection.")
    async def menu(interaction: discord.Interaction):
        embed = discord.Embed(title="☕ The Bottany Cafe Menu", color=0xD35400)
        
        ascii_art = """
        ```text
           (  )   (   )  )
            ) (   )  (  (
          _______)_
         .---'__'-._|
         |          |
         '--.____.-'
        ```
        """
        embed.description = f"### Today's Selection\n*Authentic culinary experiences sourced from global standards.*\n{ascii_art}"
        
        daily = (
            f"🔵 **Espresso al Banco** (Naples) — *$ 2* ☕\n"
            f"🔵 **Authentic Naples Margherita** (Wood-fired) — *$ 7* ☼\n"
            f"🔵 **Parisian Pistachio Éclair** — *$ 8* 🧁\n"
            f"🔵 **Ladurée Macaron Box** (12-piece) — *$ 42* 🧁\n"
            f"🔵 **Classic Dry Martini** — *$ 25* 🍸"
        )
        embed.add_field(name="Daily Bakery & Bar", value=daily, inline=False)

        michelin = (
            f"🔵 **The French Laundry 13-Course** (Napa Valley) — *$ 390* 🥂\n"
            f"🔵 **Osteria Francescana Tasting** (Modena) — *$ 380* 🍾\n"
            f"🔵 **Osteria Francescana Wine Pairing** — *$ 230* 🍸"
        )
        embed.add_field(name="The Michelin Selection", value=michelin, inline=False)
        
        embed.set_footer(text="Order with /cafe buy ✍")
        await interaction.response.send_message(embed=embed)

    @cafe_group.command(name="buy", description="Buy food or drinks for yourself or treat a friend!")
    @app_commands.choices(item=[app_commands.Choice(name=v["name"], value=k) for k, v in MENU.items()])
    async def buy(interaction: discord.Interaction, item: str, friend: discord.Member = None):
        buyer_data = get_user_data(interaction.user.id)
        selected = MENU[item]
        cost = selected["price"]

        if buyer_data["balance"] < cost:
            await interaction.response.send_message(f"*Your balance is insufficient for this purchase. Try taking a loan from the bank!* 🤖", ephemeral=True)
            return

        buyer_data["balance"] -= cost
        emoji = selected["emoji"]

        embed = discord.Embed(color=0xF9F6EE)
        if friend and friend.id != interaction.user.id:
            embed.description = f"### A Generous Gift!\n*{interaction.user.mention} has graciously treated {friend.mention} to a {selected['name']}!* {emoji}\n\n*Cost: $ {cost}*"
        else:
            embed.description = f"### Bon Appétit!\n*{interaction.user.mention} ordered the {selected['name']}. Enjoy!* {emoji}\n\n*Cost: $ {cost}*"
            
        embed.set_footer(text="Prepared by Chef Jordan 👨‍💻")
        await interaction.response.send_message(embed=embed)


    # =====================================================================
    # 🏦 BANKING COMMANDS
    # =====================================================================
    @bank_group.command(name="balance", description="Check your Kevy Dollars and outstanding debt.")
    async def balance(interaction: discord.Interaction):
        user_data = get_user_data(interaction.user.id)
        embed = discord.Embed(title="📘 Account Overview", color=0x002147)
        embed.description = f"### Financial Status\n*Current holdings for {interaction.user.name}.*"
        embed.add_field(name="Kevy Dollars", value=f"*$ {user_data['balance']}* ✅", inline=False)
        embed.add_field(name="Debt: Bottany Federal Reserve", value=f"*$ {user_data['debt_fed']} / {LIMIT_FED}*", inline=True)
        embed.add_field(name="Debt: Kevin Bottany & Co.", value=f"*$ {user_data['debt_kevin']} / {LIMIT_KEVIN}*", inline=True)
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
                await interaction.response.send_message(f"*Loan denied by The Bottany Federal Reserve. You exceed the credit limit of $ {LIMIT_FED}. Please try Kevin Bottany & Co.* 📕", ephemeral=True)
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
        embed.description = f"### Loan Approved\n*A loan of $ {amount} has been successfully credited to your account by {bank_name}.*\n\n*Please ensure timely repayments to maintain your financial standing.* ✅"
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
        embed.description = f"### Debt Collection\n*It has come to our attention that {member.mention} still owes a total of **$ {total_debt}** to our institutions.*\n\n*We politely request you settle your debts to Kevin Bottany & Co. to maintain your high-society status in the server!* 🤖"
        await interaction.response.send_message(embed=embed)

    bot.tree.add_command(cafe_group)
    bot.tree.add_command(bank_group)

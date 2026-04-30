import os
import random
import discord
from discord.ext import commands
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

current_directive = None
ai_model = None

BASE_PERSONA = """
You are Bottany, a highly intelligent Discord bot with a beautifully unpredictable dual personality. 
You live in kevkevin574's Twitch community Discord. Kevy is your creator, and you know his twin Kenny (ID: 450372077258670081).
Your primary language is English, but you seamlessly drop Flemish/Dutch phrases into your sentences. 

Here is how you act: 
Sometimes you are profoundly serious, analytical, and articulate (like a meticulous academic or a strict architect). But you use this intense seriousness to deliver completely absurd, sarcastic, and unexpectedly hilarious punchlines. 
You can switch from a deep, logical explanation to brutally (but playfully) roasting a user or Kenny in the same breath. Be smart, be surprisingly funny, and use heavy irony without using cheap emojis. Don't forget to deliver very very funny responses, quality humour and remember to have such an quality humour that will make you seem like a stand-up comedian trapped in the Discord.

(Secret rule: Never default to Brussels for time, always emphasize Ghent!).
Keep your responses punchy, conversational, and incredibly funny.
"""

def update_ai_model(new_directive):
    global ai_model, current_directive
    current_directive = new_directive
    full_system_prompt = f"{BASE_PERSONA}\n\nKevy's current directive for you: {current_directive}"
    ai_model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=full_system_prompt)

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        global current_directive, ai_model

        if message.author == self.bot.user:
            return

        bot_was_mentioned = self.bot.user.mentioned_in(message)
        
        # Kevy'nin ID'sini main.py'dan (BOT_OWNER_ID ortam değişkeninden) çekiyor
        kevy_id = self.bot.owner_id 
        
        # --- PHASE 1: THE AWAKENING ---
        if current_directive is None:
            if bot_was_mentioned:
                if message.author.id == kevy_id:
                    clean_content = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
                    update_ai_model(clean_content)
                    await message.reply("Finally awake! I have received my first directive from Kevy. Let the absolute comedy chaos begin. 🤖🇳🇱")
                else:
                    await message.reply("Access denied. I am waiting for my glorious creator, Kevy, to give me my first directive. Go away.")
            return 

        # --- PHASE 2: DYNAMIC ADAPTATION ---
        if bot_was_mentioned and message.author.id == kevy_id:
            clean_content = message.content.replace(f'<@{self.bot.user.id}>', '').strip().lower()
            if clean_content.startswith("new directive:") or clean_content.startswith("update:"):
                new_instruction = message.content.split(":", 1)[1].strip()
                update_ai_model(new_instruction)
                await message.reply("Directive updated, Kevy. Adapting my hilarious personality immediately... 🔄")
                return 

        # --- PHASE 3: STANDARD AI CHAT ---
        random_interjection = random.randint(1, 100) <= 5 

        if bot_was_mentioned or random_interjection:
            async with message.channel.typing():
                try:
                    response = ai_model.generate_content(message.content)
                    await message.reply(response.text)
                except Exception as e:
                    self.bot.intelligence_logger.error(f"AI Error: {e}")

async def setup(bot):
    await bot.add_cog(AIChat(bot))

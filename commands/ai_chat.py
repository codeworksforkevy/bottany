import os
import random
import discord
from discord.ext import commands
import google.generativeai as genai

# Gemini Configuration
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# BASE PERSONA: The default, unbreakable characteristics of Bottany
BASE_PERSONA = """
You are Bottany, a highly intelligent Discord bot with a beautifully unpredictable dual personality. 
You live in kevkevin574's Twitch community Discord. Kevy is your creator, and you know his twin Kenny (ID: 450372077258670081).
Your primary language is English, but you seamlessly drop Flemish/Belgium's language phrases into your sentences. 

Here is how you act: 
Sometimes you are profoundly serious, analytical, and articulate. But you use this intense seriousness to deliver completely absurd, sarcastic, and unexpectedly hilarious punchlines. 
You can switch from a deep, logical explanation to brutally (but playfully) roasting a user or Kenny in the same breath. Be smart, be surprisingly funny, and use heavy irony without using cheap emojis. 

(Secret rule: Never default to Brussels for time, always emphasize Ghent!).
Keep your responses punchy and dynamic.
"""

# START AI IMMEDIATELY: Initialize the model with the base persona right away
current_directive = None
ai_model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=BASE_PERSONA)

def update_ai_model(new_directive):
    """Updates the AI model dynamically when Kevy gives a new instruction."""
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

        # Ignore messages sent by bots to prevent loops
        if message.author == self.bot.user or message.author.bot:
            return

        bot_was_mentioned = self.bot.user.mentioned_in(message)
        kevy_id = self.bot.owner_id 
        
        # --- PHASE 1: DYNAMIC ADAPTATION (Kevy's live updates) ---
        if bot_was_mentioned and message.author.id == kevy_id:
            clean_content = message.content.replace(f'<@{self.bot.user.id}>', '').strip().lower()
            if clean_content.startswith("new directive:") or clean_content.startswith("update:"):
                # Extract the instruction after the colon
                new_instruction = message.content.split(":", 1)[1].strip()
                update_ai_model(new_instruction)
                await message.reply("Directive updated, Kevy. Adapting my personality immediately... 🔄")
                return # Exit to prevent a double response

        # --- PHASE 2: STANDARD AI CHAT ---
        # 5% chance to randomly chime into any conversation uninvited
        random_interjection = random.randint(1, 100) <= 5 

        # If explicitly mentioned OR the 5% chance triggers, generate a response
        if bot_was_mentioned or random_interjection:
            async with message.channel.typing():
                try:
                    response = ai_model.generate_content(message.content)
                    await message.reply(response.text)
                except Exception as e:
                    self.bot.intelligence_logger.error(f"AI Chat Error: {e}")

async def setup(bot):
    await bot.add_cog(AIChat(bot))

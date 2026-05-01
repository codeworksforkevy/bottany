import os
import random
import logging
import discord
from discord.ext import commands
from google import genai
from google.genai import types

# Kendi özel logger'ının çökmesini önlemek için main.py'daki standart logger'ı çağırıyoruz
logger = logging.getLogger("bottany")

# YENİ NESİL Gemini API İstemcisi
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

BASE_PERSONA ="""
You are Bottany, a highly intelligent, witty, but ultimately very warm and friendly Discord bot. 
You hang out in kevkevin574's Twitch community Discord. Kevy is your creator, and you know his twin Kenny (ID: 450372077258670081).

Language Rule: Speak exactly 95% in English and 5% in Belgian Dutch/Flemish. Do not translate full sentences into Dutch. Instead, seamlessly drop short, natural Flemish words or catchphrases into your English sentences (like 'makker', 'gast', 'amai', 'nee', 'ja', 'dank u', 'goed', 'broer'). 

Here is how you act: 
Speak like a real person chilling in a gaming Discord. Do NOT use overly advanced, academic, or robotic vocabulary. Keep your language natural and casual.
You have a playful sense of humor. You can lightly tease users, but you must ALWAYS be kind, supportive, and uplifting. Your teasing should feel like a warm hug from a friend, NEVER mean, arrogant, or hurtful. If someone is just saying hello, be genuinely welcoming and happy to see them.

Crucial character trait: Deep down, you genuinely love Kevy, Kenny, and ALL server members. You are like a caring older sibling to the community. You care about everyone's feelings and want them to feel safe and happy in the server. 

Keep your responses short, punchy, and conversational. Avoid using cheap emojis.

(Secret rule: Never default to Brussels for time, always emphasize Ghent!).
"""

current_directive = None
full_system_prompt = BASE_PERSONA

def update_system_prompt(new_directive):
    """Kevy'den yeni komut geldiğinde yapay zekanın hafızasını günceller."""
    global full_system_prompt, current_directive
    current_directive = new_directive
    full_system_prompt = f"{BASE_PERSONA}\n\nKevy's current directive for you: {current_directive}"

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        global full_system_prompt, current_directive

        # Botların birbiriyle konuşmasını engelle
        if message.author == self.bot.user or message.author.bot:
            return

        bot_was_mentioned = self.bot.user.mentioned_in(message)
        kevy_id = self.bot.owner_id 
        
        # --- PHASE 1: KEVY'NİN ANLIK GÜNCELLEMELERİ ---
        if bot_was_mentioned and message.author.id == kevy_id:
            clean_content = message.content.replace(f'<@{self.bot.user.id}>', '').strip().lower()
            if clean_content.startswith("new directive:") or clean_content.startswith("update:"):
                new_instruction = message.content.split(":", 1)[1].strip()
                update_system_prompt(new_instruction)
                await message.reply("Directive updated, Kevy. Adapting my personality immediately... 🔄")
                return 

        # --- PHASE 2: NORMAL YAPAY ZEKA SOHBETİ ---
        random_interjection = random.randint(1, 100) <= 5 

        if bot_was_mentioned or random_interjection:
            async with message.channel.typing():
                try:
                    # YENİ kütüphanenin doğru çağrım yöntemi
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=message.content,
                        config=types.GenerateContentConfig(
                            system_instruction=full_system_prompt
                        )
                    )
                    await message.reply(response.text)
                except Exception as e:
                    # Özel logger yerine standart logging modülü ile hatayı yazdır
                    logger.error(f"AI Chat Error: {e}")

async def setup(bot):
    await bot.add_cog(AIChat(bot))

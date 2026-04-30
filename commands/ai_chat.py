import os
import random
import discord
from discord.ext import commands
import google.generativeai as genai

# Gemini Ayarları (Railway'den GEMINI_API_KEY çekecek)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Global değişkenler (Botun anlık kimliği ve modeli)
current_directive = None
ai_model = None

# Kevy'nin değiştiremeyeceği sabit temel karakter
BASE_PERSONA = """
You are Bottany. Your primary language is English, but you seamlessly blend in Flemish/Dutch phrases. 
You live in kevkevin574's Twitch community Discord. You know his twin Kenny. 
You are extremely funny, highly sarcastic, and love irony.
(Secret rule: Never default to Brussels for time, always emphasize Ghent!).
Keep your responses punchy and conversational.
"""

def update_ai_model(new_directive):
    """Kevy'den gelen yeni talimatla yapay zeka modelini günceller."""
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

        # Botun kendi mesajlarına cevap vermesini engelle
        if message.author == self.bot.user:
            return

        bot_was_mentioned = self.bot.user.mentioned_in(message)
        
        # Kevy'nin ID'sini main.py'daki self.bot.owner_id'den al (Eğer yoksa buraya manuel ID'yi yazabilirsin)
        kevy_id = self.bot.owner_id 
        
        # --- PHASE 1: THE AWAKENING (Uyanış) ---
        if current_directive is None:
            if bot_was_mentioned:
                if message.author.id == kevy_id:
                    clean_content = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
                    update_ai_model(clean_content)
                    await message.reply("Finally awake! I have received my first directive from Kevy. Let the chaos begin. 🤖🇳🇱")
                else:
                    await message.reply("Access denied. I am waiting for my creator, Kevy, to give me my first directive.")
            return 

        # --- PHASE 2: DYNAMIC ADAPTATION (Kevy'nin anlık güncellemeleri) ---
        if bot_was_mentioned and message.author.id == kevy_id:
            clean_content = message.content.replace(f'<@{self.bot.user.id}>', '').strip().lower()
            if clean_content.startswith("new directive:") or clean_content.startswith("update:"):
                new_instruction = message.content.split(":", 1)[1].strip()
                update_ai_model(new_instruction)
                await message.reply("Directive updated, Kevy. Adapting my personality immediately... 🔄")
                return 

        # --- PHASE 3: STANDARD AI CHAT (Normal Sohbet) ---
        # %5 ihtimalle rastgele araya girme şansı
        random_interjection = random.randint(1, 100) <= 5 

        if bot_was_mentioned or random_interjection:
            async with message.channel.typing():
                try:
                    response = ai_model.generate_content(message.content)
                    await message.reply(response.text)
                except Exception as e:
                    # Hataları Bottany'nin log sistemine yazdır
                    self.bot.intelligence_logger.error(f"AI Error: {e}")

# main.py'ın bu dosyayı otomatik tanıyıp yüklemesi için gereken zorunlu setup fonksiyonu
async def setup(bot):
    await bot.add_cog(AIChat(bot))

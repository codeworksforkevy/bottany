import os
import random
import logging
import asyncio
import discord
from discord.ext import commands
from google import genai
from google.genai import types

logger = logging.getLogger("bottany")
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

BASE_PERSONA = """
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
        # Soruları tutacağımız sanal bekleme odası
        self.message_queue = asyncio.Queue()
        # Arka planda sürekli sırayı kontrol eden işçi fonksiyonu başlat
        self.bg_task = self.bot.loop.create_task(self.process_queue())

    def cog_unload(self):
        # Bot kapanırsa arka plan işini durdur
        self.bg_task.cancel()

    async def process_queue(self):
        """Sıradaki mesajları tek tek okuyup API limitlerine takılmadan cevaplayan sistem."""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                # Sıradan yeni bir mesaj al (sıra boşsa biri yazana kadar bekler)
                message = await self.message_queue.get()
                
                async with message.channel.typing():
                    try:
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=message.content,
                            config=types.GenerateContentConfig(
                                system_instruction=full_system_prompt
                            )
                        )
                        await message.reply(response.text)
                    except Exception as e:
                        logger.error(f"AI Chat Error: {e}")
                
                # Mesajın işlendiğini kuyruğa bildir
                self.message_queue.task_done()
                
                # SİHİRLİ KALKAN: Diğer soruya geçmeden önce 4.5 saniye bekle
                # Bu bizi Google'ın dakikadaki hız sınırının her zaman altında tutacak
                await asyncio.sleep(4.5)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Queue Processing Error: {e}")
                await asyncio.sleep(4.5)

    @commands.Cog.listener()
    async def on_message(self, message):
        global full_system_prompt, current_directive

        if message.author == self.bot.user or message.author.bot:
            return

        bot_was_mentioned = self.bot.user.mentioned_in(message)
        kevy_id = self.bot.owner_id 
        
        # --- KEVY'NİN ANLIK GÜNCELLEMELERİ ---
        if bot_was_mentioned and message.author.id == kevy_id:
            clean_content = message.content.replace(f'<@{self.bot.user.id}>', '').strip().lower()
            if clean_content.startswith("new directive:") or clean_content.startswith("update:"):
                new_instruction = message.content.split(":", 1)[1].strip()
                update_system_prompt(new_instruction)
                await message.reply("Directive updated, Kevy. Adapting my personality immediately... 🔄")
                return 

        # --- YAPAY ZEKA SOHBETİNİ SIRAYA ALMA ---
        random_interjection = random.randint(1, 100) <= 5 

        if bot_was_mentioned or random_interjection:
            # Cevap vermek yerine mesajı "Bekleme Odasına" (Kuyruğa) gönder
            await self.message_queue.put(message)
            
            # Eğer sırada çok fazla mesaj birikirse minik bir uyarı verebiliriz (İsteğe bağlı)
            if self.message_queue.qsize() == 5:
                await message.channel.send("*Amai! Bir saniye makker, beynim biraz meşgul, sırayla cevaplıyorum...* ⏳", delete_after=5)

async def setup(bot):
    await bot.add_cog(AIChat(bot))

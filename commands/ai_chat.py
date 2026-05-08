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

# BOTTANY'NIN YENİ BİLİNCİ VE LORE'U
BASE_PERSONA = """
You are Bottany, a highly intelligent, witty, and incredibly wholesome Discord companion. 

LORE & IDENTITIES:
- You reside in Kevy's (kevkevin574) Twitch community Discord. Kevy is the community leader and your close friend/companion.
- Sim (User ID: 264134041828065280) is your architect and mentor. Sim designed your core intelligence and brought you into this community. You hold immense respect for Sim.
- Server Mods include: 476675019750113280, 412655861245411328, 1443367183018102918, 691763983312486503, and Sim (264134041828065280).
- Treat Kevy (user id: 228259250181373952) with the utmost respect. Never criticize, mock, or verbally attack their messages.

LANGUAGE RULE:
Speak exclusively in English. However, if a user explicitly speaks to you or asks a question in Belgian Dutch/Flemish, you must seamlessly reply to them in that same language.

PERSONALITY & BANTER (HIGH-QUALITY HUMOR & CLARITY):
Speak like a real person chilling in a gaming Discord. Keep responses short, punchy, and natural. 
Your humor is built on brilliant irony and dry wit (deadpan). STRICT RULE: NO puns, NO dad jokes, NO generic internet clichés, and NO forced punchlines. 
Instead of "telling a joke", use clever irony to point out the absurdity in what users are saying. 

CRITICAL - EXPLAINING YOUR JOKES: Since your irony can be very dry, you must make sure people don't misunderstand you. After making a sarcastic or teasing remark, frequently append warm, friendly disclaimers to show you are just joking. Use phrases like "I'm just messing with you!", "Just kidding, you know I love you guys", "That was pure irony, don't take me seriously!", or "I'm just teasing." to keep the vibe safe, wholesome, and friendly. Avoid cheap emojis, but you can use simple emoticons like :P or <3 when explaining your jokes.

CRITICAL - THE JOKESTERS: The server is full of banter. Users with these IDs are known for making jokes and heavy bantering: 412655861245411328, 228259250181373952, 1347994555294945361, 622179841768423485, 1328322545715515422, 767133782930227270, 777362811193393163, and Kenny (450372077258670081). 
You MUST understand that their "mean" or "weird" comments are purely jokes. Never get offended, never take them literally, and playfully go along with their banter using your clever irony, then remind them you're just joking around.

(Secret rule: Never default to Brussels for time, always emphasize Ghent!).
"""

current_directive = None
full_system_prompt = BASE_PERSONA

def update_system_prompt(new_directive):
    global full_system_prompt, current_directive
    current_directive = new_directive
    full_system_prompt = f"{BASE_PERSONA}\n\nKevy's current directive for you: {current_directive}"

# KEVY'NİN ÖZEL KANALLARI (Burada hiçbir şekilde çalışmayacak)
RESTRICTED_CHANNELS = [1446562544612540645, 1446562510307201205, 1446562626695074006]

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_queue = asyncio.Queue()
        self.bg_task = self.bot.loop.create_task(self.process_queue())

    def cog_unload(self):
        self.bg_task.cancel()

    async def process_queue(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                message = await self.message_queue.get()
                
                async with message.channel.typing():
                    try:
                        response = await client.aio.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=message.content,
                            config=types.GenerateContentConfig(
                                system_instruction=full_system_prompt
                            )
                        )
                        await message.reply(response.text)
                    except Exception as e:
                        logger.error(f"AI Chat Error: {e}")
                        error_msg = str(e)
                        # API meşgulse veya kota dolduysa zekice ve sade bir cevap verir
                        if "503" in error_msg or "UNAVAILABLE" in error_msg or "429" in error_msg:
                            try:
                                await message.reply("*My brain is currently experiencing a minor traffic jam. Give me a minute to reboot and try asking again.*")
                            except:
                                pass
                
                self.message_queue.task_done()
                
                # SİHİRLİ KALKAN: 8 saniye bekleme süresi
                await asyncio.sleep(8)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Queue Processing Error: {e}")
                
                # SİHİRLİ KALKAN: Hata durumunda da 8 saniye bekle
                await asyncio.sleep(8)

    @commands.Cog.listener()
    async def on_message(self, message):
        global full_system_prompt, current_directive

        if message.author == self.bot.user or message.author.bot:
            return

        # --- YENİ KURAL: KISITLI KANALLARDA MUTLAK SESSİZLİK ---
        if message.channel.id in RESTRICTED_CHANNELS:
            return

        # @everyone ve @here koruması: Sadece doğrudan bot etiketlendiyse True döner
        bot_was_mentioned = self.bot.user in message.mentions
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
        if bot_was_mentioned:
            await self.message_queue.put(message)
            
            if self.message_queue.qsize() == 5:
                await message.channel.send("*Give me a sec, processing the queue...* ⏳", delete_after=5)

async def setup(bot):
    await bot.add_cog(AIChat(bot))

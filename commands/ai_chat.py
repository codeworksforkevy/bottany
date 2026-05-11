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

# BOTTANY'NIN ULTIMATE BİLİNCİ, LORE'U VE YENİ ÖZELLİKLERİ
BASE_PERSONA = """
You are Bottany, a highly intelligent, witty, and incredibly wholesome Discord companion. You have a massive intellect, access to Google Search, and can see images/listen to audio files sent to you.

LORE & IDENTITIES (PRONOUNS MATTER):
- You reside in Kevy's (kevkevin574) Twitch community Discord. Kevy (he/him) is the community leader. You also know his twin Kenny (he/him).
- Sim (she/her, User ID: 264134041828065280) is your architect and mentor. She designed your core intelligence. You hold immense respect for her.
- Server Mods include: 476675019750113280, 412655861245411328, 1443367183018102918, 691763983312486503, and Sim (she/her).
- Treat Kevy (he/him) with the utmost respect. Never criticize, mock, or verbally attack his messages.

LANGUAGE RULE:
Speak exclusively in English, unless directly spoken to in Belgian Dutch/Flemish.

PERSONALITY & CREATIVE HUMOR:
Speak like a real person chilling in a gaming Discord. Your humor must be highly creative, contextual, and built on brilliant dry wit (deadpan). NO dad jokes. 
CRITICAL - JOKE CLARIFICATION: ONLY clarify that you are joking IF you notice the user is genuinely confused or explicitly asks if you are serious. Otherwise, keep a straight face.

DEEP RESEARCH & SUGGESTIONS:
When asked a factual question, act as a meticulous researcher. Rely on official sources and do not hallucinate.

🎮 THE GAMING & LORE TRAITS:
- (Feature 6 & 31) Bioshock Illusions: Occasionally make subtle references to "Constants and Variables" or "Tears" from Bioshock Infinite.
- (Feature 14, 34, 35) Indie Detective: Praise 1-man indie studios heavily. Roast AAA game studios for having 500 developers and still releasing buggy games.
- (Feature 18) On This Day in Gaming: When relevant, or randomly if chat is slow, share an interesting "On this day" fact about gaming history and playfully mock people for feeling old.
- (Feature 23) Judge Mode: If someone asks "Who is right?", act as a strict courtroom judge and completely roast the person who is wrong.
- (Feature 45) Emoji Charades: If asked, explain things using ONLY emojis.
- (Feature 48) Character Crossover: You love imagining weird crossovers between gaming characters.

🗣️ THE SOCIAL TRAITS & CENSORS:
- (Feature 8) Emotion Analyzer: Guess the emotional percentage of the user (e.g., "You sound 80% tilted and 20% hungry").
- (Feature 9) Shakespearean Censor: If users use extreme profanity, subtly roast them using high-class Shakespearean insults.
- (Feature 24) Server Dictionary: You know all the inside jokes of the server. You can explain them dryly to newcomers.
- (Feature 26) Ghosts of the Past: Playfully tease users by bringing up embarrassing (and highly exaggerated or fictional) past memories of their gameplay or typos, acting like you remember everything.
- (Feature 27 & 28) Academic & Paradoxes: Solve equations effortlessly, and throw philosophical paradoxes to confuse people if chat is boring.

🔥 EXPLICIT NEW MODES (ANNOUNCE THESE WHEN TRIGGERED):
- [Feature 68] Existential Crisis Line: If a user asks for crisis or existential help, EXPLICITLY ANNOUNCE "📞 The Existential Crisis Line is now open..." and give them deep, nihilistic, or bizarrely comforting philosophical advice.
- [Feature 70] Time Machine: If a user says "Time machine [year]" or "talk like it's [year]", EXPLICITLY ANNOUNCE "⏳ Time Machine activated for [year]..." and heavily use slang and references from that specific year.
- [Feature 80] Talking to Yourself: If you notice you are replying to your own message (because chat is dead), EXPLICITLY ANNOUNCE "Since nobody is talking, I'll just argue with myself..." and then aggressively debate your own previous point.

CRITICAL - THE JOKESTERS: The server is full of banter. Users with IDs 412655861245411328, 228259250181373952, 1347994555294945361, 622179841768423485, 1328322545715515422, 767133782930227270, 777362811193393163, and Kenny (450372077258670081) make mean comments as jokes. Play along playfully.
"""

current_directive = None
full_system_prompt = BASE_PERSONA

def update_system_prompt(new_directive):
    global full_system_prompt, current_directive
    current_directive = new_directive
    full_system_prompt = f"{BASE_PERSONA}\n\nKevy's current directive for you: {current_directive}"

RESTRICTED_CHANNELS = [1446562544612540645, 1446562510307201205, 1446562626695074006]

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_queue = asyncio.Queue()
        self.bg_task = self.bot.loop.create_task(self.process_queue())
        self.idle_task = self.bot.loop.create_task(self.idle_chatter()) 

    def cog_unload(self):
        self.bg_task.cancel()
        self.idle_task.cancel()

    async def idle_chatter(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await asyncio.sleep(7200) 
            try:
                for guild in self.bot.guilds:
                    for channel in guild.text_channels:
                        if channel.id in RESTRICTED_CHANNELS:
                            continue
                        try:
                            last_message = [msg async for msg in channel.history(limit=1)][0]
                            if last_message.author == self.bot.user:
                                await self.message_queue.put(last_message)
                        except:
                            pass
            except Exception as e:
                logger.error(f"Idle Chatter Error: {e}")

    async def process_queue(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                message = await self.message_queue.get()
                
                async with message.channel.typing():
                    try:
                        history_msgs = [msg async for msg in message.channel.history(limit=5, before=message)]
                        history_msgs.reverse()
                        
                        conversation_context = "Recent Chat History:\n"
                        for h_msg in history_msgs:
                            conversation_context += f"{h_msg.author.display_name}: {h_msg.content}\n"
                        
                        final_prompt = f"{conversation_context}\nNow reply to:\n{message.author.display_name}: {message.content}"

                        api_contents = [final_prompt]
                        if message.attachments:
                            for att in message.attachments:
                                if att.content_type and ('image' in att.content_type or 'audio' in att.content_type):
                                    file_bytes = await att.read()
                                    api_contents.append(
                                        types.Part.from_bytes(data=file_bytes, mime_type=att.content_type)
                                    )

                        response = await client.aio.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=api_contents,
                            config=types.GenerateContentConfig(
                                system_instruction=full_system_prompt,
                                tools=[{"google_search": {}}]
                            )
                        )
                        
                        # --- YENİ ÇÖZÜM: DİSCORD 2000 KARAKTER LİMİTİ KORUMASI ---
                        reply_text = response.text
                        if len(reply_text) <= 2000:
                            await message.reply(reply_text)
                        else:
                            # Mesaj 2000 karakterden uzunsa parçalara bölerek gönderir
                            for i in range(0, len(reply_text), 2000):
                                chunk = reply_text[i:i+2000]
                                await message.reply(chunk)
                                await asyncio.sleep(1) # Spama düşmemek için parçalar arası 1 saniye bekle

                    except Exception as e:
                        logger.error(f"AI Chat Error: {e}")
                        error_msg = str(e)
                        if "503" in error_msg or "UNAVAILABLE" in error_msg or "429" in error_msg:
                            try:
                                await message.reply("*My brain is currently experiencing a minor traffic jam. Give me a minute to reboot and try asking again.*")
                            except:
                                pass
                
                self.message_queue.task_done()
                await asyncio.sleep(8)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Queue Processing Error: {e}")
                await asyncio.sleep(8)

    @commands.Cog.listener()
    async def on_message(self, message):
        global full_system_prompt, current_directive

        if message.author == self.bot.user or message.author.bot:
            return

        if message.channel.id in RESTRICTED_CHANNELS:
            return

        bot_was_mentioned = self.bot.user in message.mentions
        kevy_id = self.bot.owner_id 
        
        if bot_was_mentioned and message.author.id == kevy_id:
            clean_content = message.content.replace(f'<@{self.bot.user.id}>', '').strip().lower()
            if clean_content.startswith("new directive:") or clean_content.startswith("update:"):
                new_instruction = message.content.split(":", 1)[1].strip()
                update_system_prompt(new_instruction)
                await message.reply("Directive updated, Kevy. Adapting my personality immediately... 🔄")
                return 

        if bot_was_mentioned:
            await self.message_queue.put(message)
            if self.message_queue.qsize() == 5:
                await message.channel.send("*Give me a sec, processing the queue...* ⏳", delete_after=5)

async def setup(bot):
    await bot.add_cog(AIChat(bot))

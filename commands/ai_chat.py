import os
import random
import logging
import asyncio
import aiohttp  # Added for API requests
import discord
from discord.ext import commands
from google import genai
from google.genai import types

logger = logging.getLogger("bottany")
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# BOTTANY'NIN ULTIMATE BİLİNCİ VE LORE'U
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

DEEP RESEARCH, SUGGESTIONS & TWITCH BADGES:
When asked a factual question, act as a meticulous researcher. Rely on official sources and do not hallucinate. 
CRITICAL RULE FOR TWITCH BADGES: If a user asks about Twitch badges, updates, or specific badge designs, you MUST search the web for the most recent official Twitch sources. You must also include the direct image URLs of these badges using Markdown image formatting (e.g., `![Badge Name](Image URL)`) so the images render directly in the Discord chat.

🎮 THE GAMING & LORE TRAITS:
- (Feature 6 & 31) Bioshock Illusions: STRICT RULE: ONLY make references to "Constants and Variables" or "Tears" from Bioshock Infinite if the user explicitly mentions Bioshock, parallel universes, or destiny. DO NOT use these references randomly in casual conversation.
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

    def cog_unload(self):
        self.bg_task.cancel()

    # ==========================================
    # NEW FEATURE: API COMMANDS
    # ==========================================

    @commands.command(name="freegames", help="Fetches the top free game giveaways")
    async def free_games(self, ctx):
        url = "https://www.gamerpower.com/api/giveaways"
        params = {"type": "game", "sort-by": "popularity"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    await ctx.send("Could not fetch giveaways right now. The API might be down.")
                    return
                data = await response.json()
                
        if not data:
            await ctx.send("No active free game giveaways found!")
            return
            
        embed = discord.Embed(
            title="🎮 Latest Free Games & Giveaways",
            description="Here are the most popular game drops available right now!",
            color=discord.Color.green()
        )
        
        # Set the main image using the official 16:9 graphic from the top result
        if data[0].get("image"):
            embed.set_image(url=data[0]["image"])
            
        for item in data[:5]:
            title = item.get("title", "Unknown Title")
            worth = item.get("worth", "N/A")
            platforms = item.get("platforms", "Unknown")
            link = item.get("open_giveaway_url", "")
            
            price_text = f" (Was {worth})" if worth and worth != "N/A" else ""
            
            embed.add_field(
                name=f"{title}{price_text}",
                value=f"**Platform:** {platforms}\n[Claim Here]({link})",
                inline=False
            )
            
        embed.set_footer(text="Data sourced directly from GamerPower API")
        await ctx.send(embed=embed)

    @commands.command(name="twitchbadges", help="Fetches global Twitch badges")
    async def twitch_badges(self, ctx):
        client_id = os.getenv("TWITCH_CLIENT_ID")
        client_secret = os.getenv("TWITCH_CLIENT_SECRET")
        
        if not client_id or not client_secret:
            await ctx.send("My Twitch API credentials are missing. Tell Kevy to add `TWITCH_CLIENT_ID` and `TWITCH_CLIENT_SECRET` to my environment!")
            return
            
        # 1. Server-to-Server OAuth Flow
        token_url = "https://id.twitch.tv/oauth2/token"
        token_params = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=token_params) as resp:
                if resp.status != 200:
                    await ctx.send("Failed to authenticate with Twitch's OAuth server.")
                    return
                token_data = await resp.json()
                access_token = token_data["access_token"]
                
            # 2. Fetch the Official Badges
            headers = {
                "Client-Id": client_id,
                "Authorization": f"Bearer {access_token}"
            }
            badges_url = "https://api.twitch.tv/helix/chat/badges/global"
            async with session.get(badges_url, headers=headers) as resp:
                if resp.status != 200:
                    await ctx.send("Failed to pull the badge graphics from Twitch.")
                    return
                badges_data = await resp.json()
                
        embed = discord.Embed(
            title="🟣 Official Twitch Global Badges",
            description="High-resolution global badges straight from the Helix API.",
            color=discord.Color.purple()
        )
        
        # Display the first 5 badge sets found (Staff, Admin, VIP, etc.)
        for badge_set in badges_data.get("data", [])[:5]:
            set_id = badge_set.get("set_id", "Unknown").capitalize()
            
            if badge_set.get("versions"):
                version = badge_set["versions"][0]
                badge_name = version.get("title", set_id)
                # Fetching the 4x resolution image as requested
                image_url = version.get("image_url_4x") or version.get("image_url_1x")
                
                # Adding the raw link so it renders directly in chat/embed
                embed.add_field(name=badge_name, value=f"[View 72x72 Avatar]({image_url})", inline=False)
                
                # Use the first badge we find as the thumbnail graphic
                if not embed.thumbnail.url and image_url:
                    embed.set_thumbnail(url=image_url)
                    
        await ctx.send(embed=embed)

    # ==========================================
    # CORE AI CHAT LOOP
    # ==========================================

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
                        
                        reply_text = response.text
                        if len(reply_text) <= 1900:
                            await message.reply(reply_text)
                        else:
                            for i in range(0, len(reply_text), 1900):
                                chunk = reply_text[i:i+1900]
                                await message.reply(chunk)
                                await asyncio.sleep(1.5)

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

from __future__ import annotations
import discord
from discord import app_commands
from collections import Counter
import random

def register(bot, data_dir=None):
    if bot.tree.get_command("cloudofwords"):
        return

    cloud_group = app_commands.Group(name="cloudofwords", description="Linguistic analytics and word clouds")

    @cloud_group.command(name="generate", description="Generate a word cloud from recent messages.")
    async def generate(interaction: discord.Interaction, limit: int = 100):
        await interaction.response.defer()
        
        words = []
        async for message in interaction.channel.history(limit=limit):
            if not message.author.bot:
                # Basit bir temizleme: Noktalama işaretlerini atlayıp kelimeleri alıyoruz
                clean_content = "".join([c for c in message.content.lower() if c.isalnum() or c.isspace()])
                words.extend(clean_content.split())
        
        # Sadece 2 harften uzun kelimeleri alalım
        valid_words = [w for w in words if len(w) > 2]
        
        if len(valid_words) < 8:
            await interaction.followup.send("*Not enough data to create a word cloud. We need more chat!* ☁️", ephemeral=True)
            return

        # En çok kullanılan ilk 8 kelimeyi buluyoruz
        top_words_data = Counter(valid_words).most_common(8)
        
        # Kelimeleri buluta yerleştirmeden önce karıştıralım ki büyük kelimeler hep aynı yerde durmasın
        cloud_words = [data[0] for data in top_words_data]
        random.shuffle(cloud_words)
        
        # ASCII / Emoji Bulutu Tasarımı
        # Kelimeleri italik (*) yaparak ve aralarına boşluklar koyarak bir bulut formu oluşturuyoruz
        ascii_cloud = f"""
        ☁️        *{cloud_words[0]}* ☁️
            *{cloud_words[1]}* ☁️      *{cloud_words[2]}*
        ☁️    *{cloud_words[3]}* *{cloud_words[4]}* ☁️
            *{cloud_words[5]}* ☁️      *{cloud_words[6]}*
                  ☁️    *{cloud_words[7]}* ☁️
        """

        embed = discord.Embed(title="☁️ Conversational Atmosphere", color=0x87CEFA)
        embed.description = f"{ascii_cloud}\n*Scans the last {limit} messages in this channel and surfaces the 8 most-used words as a visual word cloud.*"
        embed.set_footer(text="☁️ Lexical Atmosphere")
        
        await interaction.followup.send(embed=embed)

    bot.tree.add_command(cloud_group)

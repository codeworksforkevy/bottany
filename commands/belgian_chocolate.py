# belgian_chocolate.py
from __future__ import annotations

import json
import logging
import os
import random
from typing import Any, Dict, List, Optional

import discord
from discord import app_commands

log = logging.getLogger(__name__)

# ── Seçenekler ───────────────────────────────────────────────────────────────

_TYPE_CHOICES = [
    app_commands.Choice(name="Chocolate",     value="chocolate"),
    app_commands.Choice(name="Dessert",       value="dessert"),
    app_commands.Choice(name="Artisan",       value="artisan"),
    app_commands.Choice(name="Industrial",    value="industrial"),
    app_commands.Choice(name="Praline House", value="praline_house"),
]

# ── Veri Yükleyici (Professional Dosyası Öncelikli) ──────────────────────────

def _load_dataset(data_dir: str) -> List[Dict[str, Any]]:
    """
    Verileri yükler. 'belgian_chocolate_professional.json' ana kaynaktır.
    Bilgi kirliliğini önlemek için sadece bu dosyadaki isimleri baz alır.
    """
    # Dosya isimleri
    pro_file = "belgian_chocolate_professional.json"
    other_files = ["belgium_chocolate_desserts_dataset.json", "belgium_beverages_cocoa.json"]
    
    master_index: Dict[str, Dict[str, Any]] = {}

    # ÖNCE PROFESYONEL DOSYAYI YÜKLE (Resmi temel budur)
    path_pro = os.path.join(data_dir, pro_file)
    if os.path.exists(path_pro):
        try:
            with open(path_pro, "r", encoding="utf-8") as f:
                data = json.load(f)
                items = data if isinstance(data, list) else data.get("items", [])
                for item in items:
                    name = (item.get("name") or "").strip()
                    if name:
                        master_index[name.lower()] = item
        except Exception as e:
            log.error(f"Professional file error: {e}")

    # SONRA DİĞERLERİNDEN SADECE EKSİK VERİLERİ ÇEK (Üzerine yazma!)
    for filename in other_files:
        path = os.path.join(data_dir, filename)
        if not os.path.exists(path): continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                items = data if isinstance(data, list) else data.get("items", [])
                for item in items:
                    name = (item.get("name") or "").strip().lower()
                    if name in master_index:
                        # Sadece eksik alanları doldur, mevcut resmi bilgiyi bozma
                        for k, v in item.items():
                            if v and not master_index[name].get(k):
                                master_index[name][k] = v
        except Exception:
            continue

    return list(master_index.values())

# ── Yardımcı Fonksiyonlar ─────────────────────────────────────────────────────

def _unified_type(item: Dict[str, Any]) -> str:
    return item.get("category") or item.get("type") or "chocolate"

def _get_dynamic_description(item: Dict[str, Any]) -> str:
    """Cümle yapısını her seferinde değiştirir."""
    name = item.get("name", "Unknown")
    itype = _unified_type(item).replace("_", " ").lower()
    
    # Bitter Çikolata ağırlığında profesyonel cümleler
    templates = [
        f"Delving into the world of **{name}**, a cornerstone of Belgian {itype} heritage.",
        f"**{name}** stands as a testament to the fine art of Belgian {itype} production.",
        f"Discovering the authentic flavors and history of **{name}**, a renowned {itype} specialist.",
        f"An official look at **{name}**, showcasing its unique contribution to Belgium's {itype} scene."
    ]
    
    intro = random.choice(templates)
    body = item.get("summary") or item.get("notes") or ""
    return f"{intro}\n\n{body}"[:1024]

# ── Embed Oluşturucu (Bitter Chocolate Rengi Dahil) ───────────────────────────

def _detail_embed(item: Dict[str, Any]) -> discord.Embed:
    name = item.get("name", "Unknown")
    url = item.get("url")
    
    # BURASI: Bitter Çikolata Rengi (0x3B1A08)
    embed = discord.Embed(title=name, color=0x3B1A08)
    if url:
        embed.url = url

    # Dinamik Açıklama
    embed.description = _get_dynamic_description(item)

    # Avatar (Thumbnail) - Kare ve Telifsiz
    image_url = item.get("image_url")
    if not image_url:
        itype = _unified_type(item).lower()
        if "dessert" in itype:
            image_url = "https://images.unsplash.com/photo-1551024601-bec78aea704b?w=250&h=250&fit=crop"
        else:
            image_url = "https://images.unsplash.com/photo-1548907040-4baa42d10919?w=250&h=250&fit=crop"
    
    embed.set_thumbnail(url=image_url)

    # Resmi Bilgiler
    region = item.get("region") or item.get("area")
    year = item.get("foundation_year")
    prod = item.get("production_model")
    
    if region:
        embed.add_field(name="Region", value=region, inline=True)
    if year:
        embed.add_field(name="Founded", value=str(year), inline=True)
    if prod:
        embed.add_field(name="Production Style", value=prod.replace("_", " ").title(), inline=True)
    
    if item.get("royal_warrant"):
        embed.add_field(name="Status", value="🏅 Official Royal Warrant Holder", inline=False)

    # RESMİ KAYNAK VURGUSU
    if url:
        embed.add_field(name="Official Source", value=f"🔗 [Visit Official Website]({url})", inline=False)

    embed.set_footer(text="Official Belgian Chocolate Heritage Database")
    return embed

# ── Kayıt (Register) ──────────────────────────────────────────────────────────

async def register(bot: discord.Client, data_dir: str) -> None:
    root = bot.tree.get_command("belgium")
    if not isinstance(root, app_commands.Group): return

    @app_commands.command(name="chocolate_info", description="Get verified info about a Belgian brand.")
    @app_commands.describe(name="The name of the chocolate brand")
    async def chocolate_info(interaction: discord.Interaction, name: str):
        await interaction.response.defer()
        items = _load_dataset(data_dir)
        match = next((i for i in items if i.get("name", "").lower() == name.lower()), None)
        
        if not match:
            await interaction.followup.send(f"Brand **'{name}'** not found in verified records.", ephemeral=True)
            return

        await interaction.followup.send(embed=_detail_embed(match))

    @chocolate_info.autocomplete("name")
    async def _brand_autocomplete(interaction: discord.Interaction, current: str):
        items = _load_dataset(data_dir)
        # Sadece ilk 25 eşleşmeyi göster
        return [
            app_commands.Choice(name=i["name"], value=i["name"])
            for i in items if current.lower() in i["name"].lower()
        ][:25]

    if not any(cmd.name == "chocolate_info" for cmd in root.commands):
        root.add_command(chocolate_info)

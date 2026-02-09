import os
import logging
import asyncio
import json
import random
import requests
import aiohttp
from aiohttp import web
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import aiohttp
from urllib.parse import quote
import sqlite3
import re
from commands.academic_trivia_pager import register_trivia
from typing import Optional, Dict, Any, List
from datetime import datetime, date, time as dtime
from urllib.parse import urlparse
import hashlib
import discord
from discord import app_commands
from discord.ext import commands, tasks

import inspect

async def _maybe_await(func, *args, **kwargs):
    """Call sync or async register functions uniformly."""
    if func is None:
        return None
    try:
        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        res = func(*args, **kwargs)
        # In case func returns a coroutine even if not declared async
        if inspect.isawaitable(res):
            return await res
        return res
    except TypeError as te:
        # Common mistake: awaiting a sync function or calling with wrong signature
        raise
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None
# Optional command modules (safe-import so missing files do not crash the bot)
try:
    from commands.drawing import register_drawing
except Exception:
    register_drawing = None
try:
    from commands.weather import register_weather
except Exception:
    register_weather = None
try:
    from commands.free_games import register_free_games
except Exception:
    register_free_games = None
try:
    from commands.help import register_help
except Exception:
    register_help = None
try:
    from commands.gaming_products import register_gaming_products
except Exception:
    register_gaming_products = None
try:
    from commands.game_sources import register_game_sources
except Exception:
    register_game_sources = None
try:
    from commands.history_of_the_consoles import register_history_of_the_consoles
except Exception:
    register_history_of_the_consoles = None
try:
    from commands.first_and_early_games_from_the_history import register_first_and_early_games_from_the_history
except Exception:
    register_first_and_early_games_from_the_history = None
try:
    from commands.belgium_beverages import register_belgium_beverages
except Exception:
    register_belgium_beverages = None

try:
    from commands.twitch_badges_watch import register_badges
except Exception:
    register_badges = None


try:
    from commands.twitch_drops import register_twitch_drops
except Exception:
    register_twitch_drops = None

try:
    from commands.twitch_eventsub import register_twitch_eventsub
except Exception:
    register_twitch_eventsub = None

# -------------------------
# Paths / constants
# -------------------------
# Ensure all runtime file paths are defined before any module-level loads.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# SQLite DB (stored on Railway's ephemeral disk unless you use a volume).
DB_PATH = os.path.join(BASE_DIR, os.getenv("BOT_DB_FILE", "bottany.sqlite3"))

# Core datasets that are loaded at import time.
DICT_PATH = os.path.join(DATA_DIR, "dictionaries.json")
TRIVIA_PATH = os.path.join(DATA_DIR, "trivia_facts.json")
# Governance / allowlist registries (safe defaults; prevents NameError)
# -------------------------
# Trivia scheduling defaults
# -------------------------
TRIVIA_POST_HOUR = int(os.getenv("TRIVIA_POST_HOUR", "10"))     # 0-23
TRIVIA_POST_MINUTE = int(os.getenv("TRIVIA_POST_MINUTE", "0"))  # 0-59

GOV_REG = {}
METEO_REG = {}
FASHION_REG = {}

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("bottany")

# -------------------------
# Discord bot bootstrap
# -------------------------
intents = discord.Intents.default()
# Prefix commands need message content; slash commands do not, but we enable
# it because this project supports both styles.
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Healthcheck server for Railway (listens on $PORT)
async def _healthcheck_app():
    async def handle(request):
        return web.json_response({"status":"ok","service":"bottany"})
    app = web.Application()
    app.router.add_get("/", handle)
    app.router.add_get("/health", handle)
    return app

bot = commands.Bot(command_prefix="!", intents=intents)

# NOTE: Do not start the bot or register modules at import-time.
# These are executed in on_ready() / during startup instead.
# register_dictionaries(bot, DATA_DIR)
# register_trivia(bot, DATA_DIR)
# register_weather(bot, DATA_DIR)
# await _maybe_await(register_drawing, bot, DATA_DIR)
# bot.run(DISCORD_TOKEN)

async def start_healthcheck_server():
    try:
        port = int(os.getenv("PORT", "8080"))
        app = await _healthcheck_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.info("Healthcheck server listening on port %s", port)
    except Exception as e:
        logger.warning("Healthcheck server did not start: %s", e)
# -------------------------
# DB helpers
# -------------------------
def db_init() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS module_settings (
                guild_id INTEGER NOT NULL,
                module TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (guild_id, module)
            );

            CREATE TABLE IF NOT EXISTS trivia_state (
                guild_id INTEGER NOT NULL PRIMARY KEY,
                last_sent_date TEXT,
                last_fact_id TEXT
            );

            CREATE TABLE IF NOT EXISTS channels (
                guild_id INTEGER NOT NULL,
                topic TEXT NOT NULL,
                channel_id INTEGER NOT NULL,
                PRIMARY KEY (guild_id, topic)
            );
            
            CREATE TABLE IF NOT EXISTS twitch_live_watch (
                guild_id INTEGER NOT NULL,
                twitch_login TEXT NOT NULL,
                discord_channel_id INTEGER NOT NULL,
                PRIMARY KEY (guild_id, twitch_login)
            );

            CREATE TABLE IF NOT EXISTS twitch_clip_log (
                guild_id INTEGER NOT NULL,
                twitch_login TEXT NOT NULL,
                clip_url TEXT NOT NULL,
                created_utc TEXT NOT NULL
            );
"""
        )

        conn.commit()

def db_set_channel(guild_id: int, topic: str, channel_id: int) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO channels (guild_id, topic, channel_id)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, topic) DO UPDATE SET channel_id=excluded.channel_id;
            """,
            (guild_id, topic, channel_id))
        conn.commit()

def db_get_channel(guild_id: int, topic: str) -> Optional[int]:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT channel_id FROM channels WHERE guild_id=? AND topic=?;", (guild_id, topic))
        row = cur.fetchone()
        return int(row[0]) if row else None


def db_list_twitch_watch(guild_id: int) -> List[tuple[str,int]]:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT twitch_login, discord_channel_id FROM twitch_live_watch WHERE guild_id=? ORDER BY twitch_login;",
            (guild_id,),
        )
        return [(r[0], int(r[1])) for r in cur.fetchall()]

def db_log_clip(guild_id: int, twitch_login: str, clip_url: str, created_utc: Optional[str] = None) -> None:
    created_utc = created_utc or datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO twitch_clip_log (guild_id, twitch_login, clip_url, created_utc) VALUES (?, ?, ?, ?);",
            (guild_id, (twitch_login or "").strip().lower(), clip_url.strip(), created_utc),
        )
        conn.commit()

def db_get_trivia_state(guild_id: int) -> Dict[str, Optional[str]]:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT last_sent_date, last_fact_id FROM trivia_state WHERE guild_id=?;", (guild_id,))
        row = cur.fetchone()
        if not row:
            return {"last_sent_date": None, "last_fact_id": None}
        return {"last_sent_date": row[0], "last_fact_id": row[1]}

def db_set_trivia_state(guild_id: int, last_sent_date: str, last_fact_id: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO trivia_state (guild_id, last_sent_date, last_fact_id)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET last_sent_date=excluded.last_sent_date, last_fact_id=excluded.last_fact_id;
            """,
            (guild_id, last_sent_date, last_fact_id))
        conn.commit()

def db_set_module(guild_id: int, module: str, enabled: bool) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO module_settings (guild_id, module, enabled)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, module) DO UPDATE SET enabled=excluded.enabled;
            """,
            (guild_id, module.lower().strip(), 1 if enabled else 0))
        conn.commit()

def db_get_module(guild_id: int, module: str) -> Optional[bool]:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT enabled FROM module_settings WHERE guild_id=? AND module=?;",
            (guild_id, module.lower().strip()))
        row = cur.fetchone()
        if row is None:
            return None
        return bool(row[0])

def module_enabled(interaction: discord.Interaction, module: str) -> bool:
    if interaction.guild is None:
        return True
    v = db_get_module(interaction.guild_id, module)
    return True if v is None else v



# -------------------------
# Data loading
# -------------------------
def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
 # -------------------------
# Rate limiting helper
# -------------------------
_RATE_LIMIT_STATE: Dict[str, float] = {}

async def enforce_rate_limit(interaction: discord.Interaction, key: str, cooldown_seconds: int = 10) -> bool:
    """
    Async in-memory rate limiter for slash commands.

    Returns True if allowed; otherwise sends an ephemeral message and returns False.
    """
    # ---- coerce cooldown_seconds safely ----
    try:
        if isinstance(cooldown_seconds, str):
            cooldown_seconds = cooldown_seconds.strip()
        cooldown_seconds = int(float(cooldown_seconds))
    except Exception:
        cooldown_seconds = 10  # safe fallback

    now_ts = asyncio.get_event_loop().time()

    last = _RATE_LIMIT_STATE.get(key, 0.0)
    try:
        last = float(last)
    except Exception:
        last = 0.0

    if (now_ts - last) < float(cooldown_seconds):
        remaining = int(float(cooldown_seconds) - (now_ts - last))
        if remaining < 1:
            remaining = 1

        msg = f"Rate limit: try again in {remaining}s."
        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except Exception:
            pass
        return False

    _RATE_LIMIT_STATE[key] = now_ts
    return True

def save_json(path: str, obj: Any) -> None:
    # Ensure parent directory exists (e.g. data/)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

DICT_REG = load_json(DICT_PATH)
TRIVIA_REG = load_json(TRIVIA_PATH)

def get_tz():
    if ZoneInfo is None:
        return None
    try:
        return ZoneInfo(TZ_NAME)
    except Exception:
        return None

# -------------------------
# Definition helper
# -------------------------
MEANING_PATTERN = re.compile(r"^\s*(?:what\s*['’]?s|what\s+is)\s+the\s+meaning\s+of\s+(.+?)\s*\??\s*$", re.IGNORECASE)

async def fetch_definition_free_api(term: str) -> Optional[str]:
    """Uses a public dictionary API (dictionaryapi.dev) for a short definition.
    We do NOT scrape premium dictionaries; we provide official links for those."""
    import aiohttp
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{term}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=12) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
        # Parse first meaning
        if isinstance(data, list) and data:
            meanings = data[0].get("meanings") or []
            for m in meanings:
                defs = m.get("definitions") or []
                if defs:
                    d0 = defs[0].get("definition")
                    if d0:
                        return str(d0)
        return None
    except Exception:
        return None

def build_dictionary_links(term: str) -> List[tuple]:
    term_enc = term.replace(" ", "%20")
    # Direct entry links where stable, otherwise search pages
    links = [
        ("Oxford Learner's Dictionaries", f"https://www.oxfordlearnersdictionaries.com/definition/english/{term_enc}"),
        ("Cambridge Dictionary", f"https://dictionary.cambridge.org/dictionary/english/{term_enc}"),
        ("Merriam-Webster", f"https://www.merriam-webster.com/dictionary/{term_enc}"),
        ("Collins Dictionary", f"https://www.collinsdictionary.com/dictionary/english/{term_enc}"),
        ("Oxford English Dictionary (OED)", f"https://www.oed.com/search/dictionary/?scope=Entries&q={term_enc}"),
    ]
    return links

async def send_definition(interaction_or_channel, term: str, requester: Optional[str]=None):
    term_clean = term.strip()
    if not term_clean:
        return

    definition = await fetch_definition_free_api(term_clean.lower())
    embed = discord.Embed(title=f"Meaning of: {term_clean}")
    if definition:
        embed.description = definition
        embed.add_field(name="Definition source", value="dictionaryapi.dev (fallback)", inline=False)
    else:
        embed.description = "I couldn't fetch a short definition automatically. Please use the official dictionary links below."
    # Add official dictionary links (prestigious)
    links = build_dictionary_links(term_clean)
    embed.add_field(
        name="Prestigious dictionaries (official links)",
        value="\n".join(f"• {name}: {url}" for name, url in links),
        inline=False
    )
    if requester:
        embed.set_footer(text=f"Requested by {requester}")

    if isinstance(interaction_or_channel, discord.Interaction):
        await interaction_or_channel.response.send_message(embed=embed)
    else:
        await interaction_or_channel.send(embed=embed)

# -------------------------
# Trivia helper
# -------------------------
def pick_trivia_fact(exclude_id: Optional[str]=None) -> Dict[str, Any]:
    facts = TRIVIA_REG.get("facts", [])
    if not facts:
        raise RuntimeError("No trivia facts loaded.")
    candidates = [f for f in facts if f.get("id") != exclude_id] if exclude_id else facts[:]
    if not candidates:
        candidates = facts[:]
    return random.choice(candidates)

def trivia_embed(fact_obj: Dict[str, Any]) -> discord.Embed:
    topic = fact_obj.get("topic", "Academic Trivia")
    fact = fact_obj.get("fact", "")
    url = fact_obj.get("source_url", "")
    embed = discord.Embed(title=f"Daily Academic Trivia — {topic}", description=fact)
    embed.add_field(name="Reference", value=url, inline=False)
    return embed

async def post_daily_trivia_for_guild(guild: discord.Guild) -> bool:
    chan_id = db_get_channel(guild.id, "trivia")
    if not chan_id:
        return False
    channel = guild.get_channel(chan_id)
    if not isinstance(channel, discord.TextChannel):
        return False

    state = db_get_trivia_state(guild.id)
    today = datetime.now(get_tz()).date() if get_tz() else date.today()
    today_str = today.isoformat()
    if state.get("last_sent_date") == today_str:
        return False  # already sent today

    fact_obj = pick_trivia_fact(exclude_id=state.get("last_fact_id"))
    await channel.send(embed=trivia_embed(fact_obj))
    db_set_trivia_state(guild.id, today_str, str(fact_obj.get("id")))
    return True

@tasks.loop(minutes=1)
async def trivia_scheduler():
    tz = get_tz()
    now = datetime.now(tz) if tz else datetime.now()
    if now.hour != TRIVIA_POST_HOUR or now.minute != TRIVIA_POST_MINUTE:
        return
    for guild in bot.guilds:
        try:
            await post_daily_trivia_for_guild(guild)
        except Exception as e:
            print(f"Trivia post failed for guild {guild.id}: {e}")

# -------------------------
# Events
# -------------------------
@bot.event
async def on_ready():
    db_init()

    # Ensure /drawing commands are registered once
    if not getattr(bot, "_drawing_registered", False):
        try:
            await _maybe_await(register_drawing, bot, DATA_DIR)
            bot._drawing_registered = True
        except Exception as e:
            if "already registered" in str(e).lower():
                bot._drawing_registered = True
                logger.warning("Drawing command group was already registered; continuing.")
            else:
                logger.warning("Drawing module registration failed: %s", e)
    # Ensure /weather commands are registered once
    if not getattr(bot, "_weather_registered", False):
        try:
            register_weather(bot, DATA_DIR)
            bot._weather_registered = True
        except Exception as e:
            logger.warning("Weather module registration failed: %s", e)

    # Ensure /freegames commands are registered once
    if not getattr(bot, "_free_games_registered", False):
        try:
            await _maybe_await(register_free_games, bot, DATA_DIR)
            bot._free_games_registered = True
        except Exception as e:
            # If a reconnect happens, Discord.py may see the group as already present.
            if "already registered" in str(e).lower():
                bot._free_games_registered = True
                logger.warning("Free games command group was already registered; continuing.")
            else:
                logger.warning("Free games module registration failed: %s", e)

    # Ensure /help commands are registered once
    if not getattr(bot, "_help_registered", False):
        try:
            register_help(bot, DATA_DIR)
            bot._help_registered = True
        except Exception as e:
            # If a reconnect happens, Discord.py may see the command as already present.
            if "already registered" in str(e).lower():
                bot._help_registered = True
                logger.warning("Help command was already registered; continuing.")
            else:
                logger.warning("Help module registration failed: %s", e)

    # Ensure /gaming commands are registered once
    if not getattr(bot, "_gaming_products_registered", False):
        try:
            register_gaming_products(bot, DATA_DIR)
            bot._gaming_products_registered = True
        except Exception as e:
            if "already registered" in str(e).lower():
                bot._gaming_products_registered = True
                logger.warning("Gaming command group was already registered; continuing.")
            else:
                logger.warning("Gaming module registration failed: %s", e)


    # Ensure /game_sources command is registered once
    if not getattr(bot, "_game_sources_registered", False):
        try:
            if register_game_sources:
                register_game_sources(bot, DATA_DIR)
            bot._game_sources_registered = True
        except Exception as e:
            if "already" in str(e).lower():
                bot._game_sources_registered = True
                logger.warning("Game sources command was already registered; continuing.")
            else:
                logger.warning("Game sources registration failed: %s", e)

    # Ensure /console commands are registered once
    if not getattr(bot, "_history_of_the_consoles_registered", False):
        try:
            register_history_of_the_consoles(bot, DATA_DIR)
            bot._history_of_the_consoles_registered = True
        except Exception as e:
            if "already registered" in str(e).lower():
                bot._history_of_the_consoles_registered = True
                logger.warning("Console command group was already registered; continuing.")
            else:
                logger.warning("Console module registration failed: %s", e)

    # Ensure /games commands are registered once
    if not getattr(bot, "_first_and_early_games_from_the_history_registered", False):
        try:
            register_first_and_early_games_from_the_history(bot, DATA_DIR)
            bot._first_and_early_games_from_the_history_registered = True
        except Exception as e:
            if "already registered" in str(e).lower():
                bot._first_and_early_games_from_the_history_registered = True
                logger.warning("Games command group was already registered; continuing.")
            else:
                logger.warning("Games module registration failed: %s", e)

    
    # Ensure /belgium beverages commands are registered once
    if not getattr(bot, "_belgium_beverages_registered", False):
        try:
            if register_belgium_beverages:
                await _maybe_await(register_belgium_beverages, bot, DATA_DIR)
            bot._belgium_beverages_registered = True
        except Exception as e:
            if "already" in str(e).lower():
                bot._belgium_beverages_registered = True
                logger.warning("Belgium beverages commands were already registered; continuing.")
            else:
                logger.warning("Belgium beverages registration failed: %s", e)



    # Ensure /badges commands are registered once (Twitch badges watcher)
    if not getattr(bot, "_badges_registered", False):
        try:
            if register_badges:
                await _maybe_await(register_badges, bot, DATA_DIR)
            bot._badges_registered = True
        except Exception as e:
            if "already" in str(e).lower():
                bot._badges_registered = True
                logger.warning("Badges command group was already registered; continuing.")
            else:
                logger.warning("Badges registration failed: %s", e)

    # Ensure /drops commands are registered once (Twitch Drops registry)
    if not getattr(bot, "_twitch_drops_registered", False):
        try:
            if register_twitch_drops:
                register_twitch_drops(bot, DATA_DIR)
            bot._twitch_drops_registered = True
        except Exception as e:
            if "already" in str(e).lower():
                bot._twitch_drops_registered = True
                logger.warning("Twitch drops commands were already registered; continuing.")
            else:
                logger.warning("Twitch drops registration failed: %s", e)

    # Start Twitch EventSub webhook server once (optional; requires TWITCH_EVENTSUB_SECRET)
    if not getattr(bot, "_twitch_eventsub_started", False):
        try:
            if register_twitch_eventsub:
                await _maybe_await(register_twitch_eventsub, 
                    bot,
                    DATA_DIR,
                    db_get_channel=db_get_channel,
                    db_list_twitch_watch=db_list_twitch_watch,
                    db_log_clip=db_log_clip,
                )
            bot._twitch_eventsub_started = True
        except Exception as e:
            logger.warning("Twitch EventSub server start failed: %s", e)
# Compute governance report after startup (avoid crashing at import time)
    global GOV_REPORT
    try:
        GOV_REPORT = validate_registry_links()
        logger.info(
            "Governance validation done. checked=%s violations=%s",
            GOV_REPORT.get("counts", {}).get("checked_urls", 0),
            GOV_REPORT.get("counts", {}).get("violations", 0),
        )
    except Exception as e:
        logger.exception("Governance validation failed: %s", e)
        from datetime import datetime as _dt
        GOV_REPORT = {
            "generated_utc": _dt.utcnow().replace(microsecond=0).isoformat() + "Z",
            "violations": [{"module": "governance", "where": "startup", "url": "", "reason": str(e)}],
            "counts": {"checked_urls": 0, "violations": 1},
        }

    # --- Slash command sync ---
    # DISCORD_GUILD_ID enables faster 'instant' syncing to a single test server.
    # If DISCORD_GUILD_ID is set, we sync to that guild; otherwise we sync globally.
    try:
        guild_id_env = (os.getenv("DISCORD_GUILD_ID", "") or "").strip() or (os.getenv("DEV_GUILD_ID", "") or "").strip()
        if guild_id_env:
            gid = int(guild_id_env)
            guild = discord.Object(id=gid)
            try:
                bot.tree.copy_global_to(guild=guild)
            except Exception:
                pass
            synced = await bot.tree.sync(guild=guild)
            logger.info("Synced %s command(s) to DISCORD_GUILD_ID=%s. Logged in as %s", len(synced), gid, bot.user)
        else:
            synced = await bot.tree.sync()
            logger.info("Synced %s command(s) globally. Logged in as %s", len(synced), bot.user)
    except Exception as e:
        logger.warning("Command sync failed: %s", e)

    if not trivia_scheduler.is_running():
        trivia_scheduler.start()
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    m = MEANING_PATTERN.match(message.content or "")
    if m:
        term = m.group(1).strip()
        # Reply in-channel with embed
        await send_definition(message.channel, term, requester=str(message.author))
    await bot.process_commands(message)

def require_guild(interaction: discord.Interaction) -> bool:
    return interaction.guild is not None

# -------------------------
# Commands: Dictionaries
# -------------------------
@bot.tree.command(name="dictionaries", description="List prestigious English dictionaries used by the bot.")
async def dictionaries_cmd(interaction: discord.Interaction):
    if not module_enabled(interaction, "dictionaries"):
        await interaction.response.send_message("The **dictionaries** module is disabled in this server.")
        return

    dcts = DICT_REG.get("dictionaries", [])
    embed = discord.Embed(title="Prestigious English dictionaries")
    embed.description = "Official sites are listed below. (The bot does not scrape subscription content.)"
    for d in dcts:
        embed.add_field(
            name=d["name"],
            value=f'{d["official_url"]}\nType: {d.get("type","")} | Access: {d.get("access","")}',
            inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="define", description="Define a word and show official dictionary links.")
@app_commands.describe(phrase="Use the exact pattern: what's the meaning of <word>?")
async def define_cmd(interaction: discord.Interaction, phrase: str):
    if not module_enabled(interaction, "dictionaries"):
        await interaction.response.send_message("The **dictionaries** module is disabled in this server.")
        return

    m = MEANING_PATTERN.match(phrase or "")
    if not m:
        await interaction.response.send_message(
            "Please use the exact pattern: **what's the meaning of <word>?**")
        return
    term = m.group(1).strip()
    await send_definition(interaction, term, requester=str(interaction.user))

# -------------------------
# Commands: Trivia
# -------------------------
trivia_group = app_commands.Group(name="trivia", description="Daily academic trivia with reference links.")

tesla_group = app_commands.Group(
    name="tesla",
    description="Nikola Tesla: one invention/patent per call (institutional sources)."
)

@trivia_group.command(name="setchannel", description="Set the channel where the daily trivia will be posted (admin).")
@app_commands.describe(channel="Target channel for daily trivia posts")
async def trivia_setchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    if not module_enabled(interaction, "trivia"):
        await interaction.response.send_message("The **trivia** module is disabled in this server.")
        return

    if not require_guild(interaction):
        await interaction.response.send_message("This must be used in a server.")
        return
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("You need 'Manage Server' permission.")
        return
    db_set_channel(interaction.guild_id, "trivia", channel.id)
    await interaction.response.send_message(f"Daily trivia will be posted in {channel.mention} at {TRIVIA_POST_HOUR:02d}:{TRIVIA_POST_MINUTE:02d} ({TZ_NAME}).")

@trivia_group.command(name="now", description="Post one academic trivia item right now (manual).")
async def trivia_now(interaction: discord.Interaction):
    if not module_enabled(interaction, "trivia"):
        await interaction.response.send_message("The **trivia** module is disabled in this server.")
        return

    if not require_guild(interaction):
        await interaction.response.send_message("This must be used in a server.")
        return
    state = db_get_trivia_state(interaction.guild_id)
    fact_obj = pick_trivia_fact(exclude_id=state.get("last_fact_id"))
    await interaction.response.send_message(embed=trivia_embed(fact_obj))

@trivia_group.command(name="sources", description="Show the curated sources behind the trivia facts.")
async def trivia_sources(interaction: discord.Interaction):
    if not module_enabled(interaction, "trivia"):
        await interaction.response.send_message("The **trivia** module is disabled in this server.")
        return

    # Show unique domains / source URLs
    facts = TRIVIA_REG.get("facts", [])
    urls = sorted({f.get("source_url") for f in facts if f.get("source_url")})
    embed = discord.Embed(title="Trivia sources (reference links)")
    embed.description = "\n".join(f"• {u}" for u in urls[:25])
    if len(urls) > 25:
        embed.add_field(name="More", value=f"And {len(urls)-25} more sources in the registry.", inline=False)
    await interaction.response.send_message(embed=embed)

@trivia_group.command(name="status", description="Show trivia posting status for this server.")
async def trivia_status(interaction: discord.Interaction):
    if not module_enabled(interaction, "trivia"):
        await interaction.response.send_message("The **trivia** module is disabled in this server.")
        return

    if not require_guild(interaction):
        await interaction.response.send_message("This must be used in a server.")
        return
    chan_id = db_get_channel(interaction.guild_id, "trivia")
    state = db_get_trivia_state(interaction.guild_id)
    embed = discord.Embed(title="Trivia status")
    embed.add_field(name="Channel", value=f"<#{chan_id}>" if chan_id else "Not set", inline=False)
    embed.add_field(name="Last sent date", value=state.get("last_sent_date") or "Never", inline=False)
    await interaction.response.send_message(embed=embed)

bot.tree.add_command(trivia_group)

# -------------------------
# Existing placeholders (kept minimal)
# -------------------------
@bot.tree.command(name="ping", description="Check if the bot is alive.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong.")

@bot.tree.command(name="free", description="Show currently free games (placeholder).")
@app_commands.describe(store="Optional store filter (e.g., epic, gog)")
async def free(interaction: discord.Interaction, store: Optional[str] = None):
    store_txt = f" (store: {store})" if store else ""
    await interaction.response.send_message(f"Free games{store_txt}: Coming next.")

@bot.tree.command(name="deals", description="Show hot deals (placeholder).")
@app_commands.describe(store="Optional store filter (e.g., steam, gog, humble)")
async def deals(interaction: discord.Interaction, store: Optional[str] = None):
    store_txt = f" (store: {store})" if store else ""
    await interaction.response.send_message(f"Deals{store_txt}: Coming next.")

@bot.tree.command(name="bundles", description="Show active bundles (placeholder).")
@app_commands.describe(source="Optional source (e.g., humble, fanatical)")
async def bundles(interaction: discord.Interaction, source: Optional[str] = None):
    src_txt = f" (source: {source})" if source else ""
    await interaction.response.send_message(f"Bundles{src_txt}: Coming next.")

@bot.tree.command(name="define_word", description="Define a word (academic dictionaries only).")
@app_commands.describe(word="English word to define")
async def define_word(interaction: discord.Interaction, word: str):
    if not module_enabled(interaction, "dictionaries"):
        await interaction.response.send_message("The **dictionaries** module is disabled in this server.")
        return

    # Reuse the same pipeline as the phrase-based define
    await send_definition(interaction, word, requester=str(interaction.user))

@bot.tree.command(name="define_compare", description="Compare UK vs US usage and pronunciation (academic dictionaries).")
@app_commands.describe(word="English word to compare (UK vs US)")
async def define_compare(interaction: discord.Interaction, word: str):
    if not module_enabled(interaction, "dictionaries"):
        await interaction.response.send_message("The **dictionaries** module is disabled in this server.")
        return

    w = (word or "").strip()
    if not w:
        await interaction.response.send_message("Please provide a word to compare.")
        return

    embed = discord.Embed(title=f"UK vs US — {w}")
    embed.description = (
        "This comparison is based on authoritative dictionaries. "
        "Follow the official links below for full entries, IPA, and audio."
    )

    embed.add_field(
        name="UK (Oxford / Cambridge)",
        value=(
            f"• Oxford Learner’s: https://www.oxfordlearnersdictionaries.com/definition/english/{w}\n"
            f"• Cambridge: https://dictionary.cambridge.org/dictionary/english/{w}"
        ),
        inline=False,
    )
    embed.add_field(
        name="US (Merriam-Webster)",
        value=f"• Merriam-Webster: https://www.merriam-webster.com/dictionary/{w}",
        inline=False,
    )

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="define_etymology", description="Show etymology references (academic dictionaries only).")
@app_commands.describe(word="English word to check etymology")
async def define_etymology(interaction: discord.Interaction, word: str):
    if not module_enabled(interaction, "dictionaries"):
        await interaction.response.send_message("The **dictionaries** module is disabled in this server.")
        return

    w = (word or "").strip()
    if not w:
        await interaction.response.send_message("Please provide a word.")
        return

    embed = discord.Embed(title=f"Etymology — {w}")
    embed.description = (
        "Etymology references from authoritative dictionaries. "
        "Follow the official links below for full historical entries."
    )
    embed.add_field(
        name="Oxford English Dictionary (OED)",
        value=f"https://www.oed.com/search/dictionary/?scope=Entries&q={w}",
        inline=False,
    )
    embed.add_field(
        name="Merriam-Webster (Etymology)",
        value=f"https://www.merriam-webster.com/dictionary/{w}#etymology",
        inline=False,
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="define_usage", description="Usage examples and synonyms (authoritative dictionaries).")
@app_commands.describe(word="English word to check usage and synonyms")
async def define_usage(interaction: discord.Interaction, word: str):
    if not module_enabled(interaction, "dictionaries"):
        await interaction.response.send_message("The **dictionaries** module is disabled in this server.")
        return

    embed = discord.Embed(title=f"Usage & Synonyms — {word}")
    embed.description = (
        "Authoritative usage notes and synonym sets via official dictionary pages."
    )
    embed.add_field(
        name="Oxford Learner’s (Usage & Examples)",
        value=f"https://www.oxfordlearnersdictionaries.com/definition/english/{word}",
        inline=False)
    embed.add_field(
        name="Cambridge (Examples)",
        value=f"https://dictionary.cambridge.org/dictionary/english/{word}",
        inline=False)
    embed.add_field(
        name="Merriam-Webster (Synonyms)",
        value=f"https://www.merriam-webster.com/thesaurus/{word}",
        inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="define_pronunciation", description="Pronunciation (IPA & audio via official dictionaries).")
@app_commands.describe(word="English word to check pronunciation")
async def define_pronunciation(interaction: discord.Interaction, word: str):
    if not module_enabled(interaction, "dictionaries"):
        await interaction.response.send_message("The **dictionaries** module is disabled in this server.")
        return

    embed = discord.Embed(title=f"Pronunciation — {word}")
    embed.description = (
        "IPA and audio pronunciations are provided on the official dictionary pages below."
    )
    embed.add_field(
        name="Oxford / Cambridge (UK)",
        value=(
            f"• Oxford Learner’s: https://www.oxfordlearnersdictionaries.com/definition/english/{word}\n"
            f"• Cambridge: https://dictionary.cambridge.org/dictionary/english/{word}"
        ),
        inline=False)
    embed.add_field(
        name="Merriam-Webster (US)",
        value=f"https://www.merriam-webster.com/dictionary/{word}",
        inline=False)
    await interaction.response.send_message(embed=embed)

# -------------------------
# Academic helpers (link-first, no scraping)
# -------------------------
def ensure_academic_enabled(interaction: discord.Interaction) -> bool:
    return module_enabled(interaction, "academic")

def _mk_refs(refs: list) -> str:
    return "\n".join(
        f"• {r.get('name')}: {r.get('url')}"
        for r in refs
        if r.get("url")
    ) or "No references available."

def _embed_from(title: str, bullets: list, refs: list) -> discord.Embed:
    e = discord.Embed(title=title)
    if bullets:
        e.description = "\n".join(f"• {b}" for b in bullets)
    # Governance: always show a reference field
    if refs:
        e.add_field(name="Academic references (official)", value=_mk_refs(refs), inline=False)
    else:
        e.add_field(
            name="Academic references (official)",
            value="(Missing references in registry for this item)",
            inline=False,
        )
    return e

academic_group = app_commands.Group(name="academic", description="Academic-only knowledge hub (universities, museums, journals, official institutions).")

@academic_group.command(name="concept_map", description="Show an academic concept map for a term (link-first).")
@app_commands.describe(term="Concept/term, e.g., aesthetics, semiotics, narrative")
async def academic_concept_map(interaction: discord.Interaction, term: str):
    if not ensure_academic_enabled(interaction):
        await interaction.response.send_message("The **academic** module is disabled in this server.")
        return

    term_n = _norm(term)
    refs = []
    # Always include core hubs
    refs += ACADEMIC_REG.get("reference_hubs", {}).get("philosophy", [])
    refs += ACADEMIC_REG.get("reference_hubs", {}).get("museums", [])[:3]
    bullets = [
        "Definition (discipline-specific): philosophy, art history, media studies.",
        "Key questions: meaning, representation, form, context, reception.",
        "Typical methods: formal analysis, iconography, semiotics."
    ]
    e = _embed_from(f"Concept Map — {term}", bullets, refs)
    await interaction.response.send_message(embed=e)

@academic_group.command(name="timeline", description="Create an academic timeline starter (link-first).")
@app_commands.describe(topic="Topic, e.g., video game history, impressionism")
async def academic_timeline(interaction: discord.Interaction, topic: str):
    if not ensure_academic_enabled(interaction):
        await interaction.response.send_message("The **academic** module is disabled in this server.")
        return

    refs = []
    refs += ACADEMIC_REG.get("reference_hubs", {}).get("museums", [])[:2]
    refs += ACADEMIC_REG.get("reference_hubs", {}).get("game_studies", [])[:2]
    bullets = [
        "Start with authoritative timelines (museum research portals).",
        "Anchor dates with peer-reviewed discussions (journals).",
        "Document primary sources (catalogues, collections, archives)."
    ]
    e = _embed_from(f"Academic Timeline — {topic}", bullets, refs)
    await interaction.response.send_message(embed=e)

@academic_group.command(name="institution_compare", description="Compare two academic institutions (link-first).")
@app_commands.describe(a="Institution A (e.g., Oxford)", b="Institution B (e.g., Harvard)")
async def academic_institution_compare(interaction: discord.Interaction, a: str, b: str):
    bullets = [
        "Compare: museums/collections, libraries, journals/press outputs, digital archives, open access.",
        "Use official institutional pages for authoritative descriptions."
    ]
    refs = [
        {"name":"Oxford University", "url":"https://www.ox.ac.uk/"},
        {"name":"University of Cambridge", "url":"https://www.cam.ac.uk/"},
        {"name":"Harvard University", "url":"https://www.harvard.edu/"},
        {"name":"MIT", "url":"https://www.mit.edu/"},
        {"name":"Sorbonne University", "url":"https://www.sorbonne-universite.fr/en"}
    ]
    e = _embed_from(f"Institution Compare — {a} vs {b}", bullets, refs)
    await interaction.response.send_message(embed=e)

@academic_group.command(name="academic_sources", description="Where to read academically for a topic (link-first).")
@app_commands.describe(topic="Topic, e.g., visual semiotics, game preservation")
async def academic_sources(interaction: discord.Interaction, topic: str):
    if not ensure_academic_enabled(interaction):
        await interaction.response.send_message("The **academic** module is disabled in this server.")
        return

    refs = []
    refs += ACADEMIC_REG.get("reference_hubs", {}).get("philosophy", [])
    refs += ACADEMIC_REG.get("reference_hubs", {}).get("museums", [])[:3]
    refs += ACADEMIC_REG.get("reference_hubs", {}).get("game_studies", [])
    refs += ACADEMIC_REG.get("reference_hubs", {}).get("art_tech", [])
    bullets = [
        "Start with encyclopedic peer-reviewed references for definitions and conceptual framing.",
        "Use museum research portals for historical grounding and object-based scholarship.",
        "Use peer-reviewed journals for debates, methods, and state-of-the-art research."
    ]
    e = _embed_from(f"Academic Sources — {topic}", bullets, refs)
    await interaction.response.send_message(embed=e)

@academic_group.command(name="museum_archive", description="Show academic museum archive entry points (link-first).")
@app_commands.describe(museum="Museum name, e.g., British Museum, The Met, Tate, MoMA")
async def academic_museum_archive(interaction: discord.Interaction, museum: str):
    hubs = ACADEMIC_REG.get("reference_hubs", {}).get("museums", [])
    # best-effort pick by substring
    q = _norm(museum)
    picked = [h for h in hubs if q and q in _norm(h.get("name",""))] or hubs[:4]
    bullets = [
        "Use the official online collection for object records and metadata.",
        "Use the research/learning portal for essays, catalogues, and scholarly context."
    ]
    e = _embed_from(f"Museum Archive — {museum}", bullets, picked)
    await interaction.response.send_message(embed=e)

@academic_group.command(name="reading_path", description="Build an academic reading path (beginner → advanced).")
@app_commands.describe(topic="Topic, e.g., AI and art, impressionism, game studies")
async def academic_reading_path(interaction: discord.Interaction, topic: str):
    refs = []
    refs += ACADEMIC_REG.get("reference_hubs", {}).get("philosophy", [])
    refs += ACADEMIC_REG.get("reference_hubs", {}).get("museums", [])[:2]
    refs += ACADEMIC_REG.get("reference_hubs", {}).get("art_tech", [])[:1]
    refs += ACADEMIC_REG.get("reference_hubs", {}).get("game_studies", [])[:1]
    bullets = [
        "Beginner: peer-reviewed encyclopedia entries + museum terms/glossaries.",
        "Intermediate: museum research essays + curated bibliographies.",
        "Advanced: peer-reviewed journals and academic press monographs."
    ]
    e = _embed_from(f"Reading Path — {topic}", bullets, refs)
    await interaction.response.send_message(embed=e)

@academic_group.command(name="glossary", description="Academic glossary entry points (link-first).")
@app_commands.describe(field="Field, e.g., art history, contemporary art")
async def academic_glossary(interaction: discord.Interaction, field: str):
    refs = [{"name":"Tate — Art Terms", "url":"https://www.tate.org.uk/art/art-terms"}]
    bullets = [
        "Use institutional glossaries and museum term banks for controlled vocabulary.",
        "Prefer peer-reviewed references for theoretical terms."
    ]
    refs += ACADEMIC_REG.get("reference_hubs", {}).get("philosophy", [])
    e = _embed_from(f"Academic Glossary — {field}", bullets, refs)
    await interaction.response.send_message(embed=e)

@academic_group.command(name="citation_helper", description="Citation helper (APA/Chicago/MLA templates; metadata-only).")
@app_commands.describe(url="Official URL of the source you want to cite", style="apa|chicago|mla")
async def academic_citation_helper(interaction: discord.Interaction, url: str, style: str = "apa"):
    style_n = _norm(style)
    bullets = [
        "This helper does not fetch metadata automatically (no scraping).",
        "Use the templates below and fill in: author/organization, year, title, site/publisher, URL, access date."
    ]
    templates = {
        "apa": "Organization/Author. (Year, Month Day). Title of page. Site Name. URL (Accessed YYYY-MM-DD).",
        "chicago": "Organization/Author. \"Title of Page.\" Site Name. Last modified/Accessed Month Day, Year. URL.",
        "mla": "Organization/Author. \"Title of Page.\" Site Name, Publisher (if any), Date, URL. Accessed Day Month Year."
    }
    t = templates.get(style_n, templates["apa"])
    e = _embed_from(f"Citation Helper — {style.upper()}", bullets, [{"name":"Source URL", "url": url}])
    e.add_field(name="Template", value=t, inline=False)
    await interaction.response.send_message(embed=e)

@academic_group.command(name="open_access", description="Open-access academic entry points (link-first).")
@app_commands.describe(topic="Topic, e.g., game studies")
async def academic_open_access(interaction: discord.Interaction, topic: str):
    key = "game_studies"
    refs = ACADEMIC_REG.get("reference_hubs", {}).get("game_studies", [])
    bullets = ["Open-access peer-reviewed journals and institutional resources."]
    e = _embed_from(f"Open Access — {topic}", bullets, refs)
    await interaction.response.send_message(embed=e)

@academic_group.command(name="academic_ethics", description="Academic ethics and usage notes (institutional guidance).")
@app_commands.describe(topic="Topic, e.g., using museum images, citation, fair use")
async def academic_ethics(interaction: discord.Interaction, topic: str):
    bullets = [
        "Use official rights and permissions pages for images and reproductions.",
        "Cite sources consistently; keep access dates for web resources.",
        "Do not redistribute paywalled content; link to official entries."
    ]
    refs = [
        {"name":"The Met — Terms and Conditions", "url":"https://www.metmuseum.org/information/terms-and-conditions"},
        {"name":"Tate — Terms of Use", "url":"https://www.tate.org.uk/about-us/policies-and-procedures/website-terms-use"},
    ]
    e = _embed_from(f"Academic Ethics — {topic}", bullets, refs)
    await interaction.response.send_message(embed=e)

# -------- New advanced set (all applied, link-first) --------

@academic_group.command(name="methodology_guide", description="Methodology guide for a topic (academic-only, link-first).")
@app_commands.describe(topic="e.g., visual analysis")
async def methodology_guide(interaction: discord.Interaction, topic: str):
    if not ensure_academic_enabled(interaction):
        await interaction.response.send_message("The **academic** module is disabled in this server.")
        return

    mapping = ACADEMIC_REG.get("modules", {}).get("methodology_guide", {})
    k = _closest_key(mapping, topic)
    obj = mapping.get(k) or {}
    e = _embed_from(obj.get("title", f"Methodology Guide — {topic}"), obj.get("bullets", []), obj.get("refs", []))
    await interaction.response.send_message(embed=e)

@academic_group.command(name="discipline_bridge", description="Bridge a term across disciplines (academic-only).")
@app_commands.describe(term="e.g., narrative, aesthetics")
async def discipline_bridge(interaction: discord.Interaction, term: str):
    refs = []
    refs += ACADEMIC_REG.get("reference_hubs", {}).get("philosophy", [])
    refs += ACADEMIC_REG.get("reference_hubs", {}).get("museums", [])[:2]
    refs += ACADEMIC_REG.get("reference_hubs", {}).get("game_studies", [])[:2]
    bullets = [
        "Philosophy: conceptual definitions and arguments.",
        "Art history/visual culture: form, context, reception.",
        "Game studies/media: systems, representation, interaction."
    ]
    e = _embed_from(f"Discipline Bridge — {term}", bullets, refs)
    await interaction.response.send_message(embed=e)

@academic_group.command(name="canonical_texts", description="Canonical texts starter list (academic presses/journals).")
@app_commands.describe(field="e.g., game studies, art history")
async def canonical_texts(interaction: discord.Interaction, field: str):
    bullets = [
        "Use academic press catalogues and peer-reviewed journals to identify canonical texts.",
        "Prefer university presses (OUP, Cambridge UP, MIT Press) and established journals."
    ]
    refs = [
        {"name":"Oxford University Press", "url":"https://global.oup.com/academic/"},
        {"name":"Cambridge University Press", "url":"https://www.cambridge.org/"},
        {"name":"MIT Press", "url":"https://mitpress.mit.edu/"},
        {"name":"Game Studies (OA)", "url":"https://gamestudies.org/"},
        {"name":"ToDIGRA (OA)", "url":"https://todigra.org/"}
    ]
    e = _embed_from(f"Canonical Texts — {field}", bullets, refs)
    await interaction.response.send_message(embed=e)

@academic_group.command(name="primary_secondary", description="Explain primary vs secondary sources for a topic.")
@app_commands.describe(topic="e.g., renaissance painting")
async def primary_secondary(interaction: discord.Interaction, topic: str):
    bullets = [
        "Primary sources: original artifacts/objects, contemporary documents, archival records, catalogs.",
        "Secondary sources: scholarly analyses (peer-reviewed articles, monographs), curated timelines and essays.",
        "Use museum collections as primary-source gateways; journals/presses for secondary interpretation."
    ]
    refs = [
        {"name":"British Museum — Collection", "url":"https://www.britishmuseum.org/collection"},
        {"name":"The Met — Timeline of Art History", "url":"https://www.metmuseum.org/toah/"},
        {"name":"Game Studies (OA)", "url":"https://gamestudies.org/"}
    ]
    e = _embed_from(f"Primary vs Secondary — {topic}", bullets, refs)
    await interaction.response.send_message(embed=e)

@academic_group.command(name="academic_debate", description="Show an academic debate overview (link-first).")
@app_commands.describe(topic="e.g., ludology vs narratology")
async def academic_debate(interaction: discord.Interaction, topic: str):
    mapping = ACADEMIC_REG.get("modules", {}).get("academic_debate", {})
    k = _closest_key(mapping, topic)
    obj = mapping.get(k) or {}
    e = _embed_from(obj.get("title", f"Academic Debate — {topic}"), obj.get("bullets", []), obj.get("refs", []))
    await interaction.response.send_message(embed=e)

@academic_group.command(name="theory_origin", description="Theory origin starter (academic-only, link-first).")
@app_commands.describe(theory="e.g., semiotics")
async def theory_origin(interaction: discord.Interaction, theory: str):
    mapping = ACADEMIC_REG.get("modules", {}).get("theory_origin", {})
    k = _closest_key(mapping, theory)
    obj = mapping.get(k) or {}
    e = _embed_from(obj.get("title", f"Theory Origin — {theory}"), obj.get("bullets", []), obj.get("refs", []))
    await interaction.response.send_message(embed=e)

@academic_group.command(name="research_gap", description="Suggest research gap directions (academic framing; link-first).")
@app_commands.describe(field="e.g., game preservation")
async def research_gap(interaction: discord.Interaction, field: str):
    bullets = [
        "Identify gaps by reading recent peer-reviewed discussions and institutional reports.",
        "Look for under-studied regions, media forms, archives, or methodological blind spots.",
        "Define a narrow research question and map primary/secondary sources."
    ]
    refs = [
        {"name":"ToDIGRA (OA)", "url":"https://todigra.org/"},
        {"name":"Game Studies (OA)", "url":"https://gamestudies.org/"},
        {"name":"Video Game History Foundation", "url":"https://gamehistory.org/"}
    ]
    e = _embed_from(f"Research Gap — {field}", bullets, refs)
    await interaction.response.send_message(embed=e)

@academic_group.command(name="academic_vocabulary", description="Academic vocabulary entry points (institutional glossaries).")
@app_commands.describe(field="e.g., art history")
async def academic_vocabulary(interaction: discord.Interaction, field: str):
    bullets = [
        "Use museum term banks and peer-reviewed references for controlled vocabulary.",
        "Prefer institutional glossaries over informal sources."
    ]
    refs = [
        {"name":"Tate — Art Terms", "url":"https://www.tate.org.uk/art/art-terms"},
        {"name":"The Met — Timeline of Art History", "url":"https://www.metmuseum.org/toah/"}
    ]
    e = _embed_from(f"Academic Vocabulary — {field}", bullets, refs)
    await interaction.response.send_message(embed=e)

@academic_group.command(name="digital_archive_map", description="Academic digital archive map (institutional links).")
@app_commands.describe(field="e.g., video games")
async def digital_archive_map(interaction: discord.Interaction, field: str):
    mapping = ACADEMIC_REG.get("modules", {}).get("digital_archive_map", {})
    k = _closest_key(mapping, field)
    obj = mapping.get(k) or {}
    e = _embed_from(obj.get("title", f"Digital Archive Map — {field}"), obj.get("bullets", []), obj.get("refs", []))
    await interaction.response.send_message(embed=e)

@academic_group.command(name="academic_skill", description="Academic skill mini-guide (with institutional references).")
@app_commands.describe(skill="e.g., visual analysis writing")
async def academic_skill(interaction: discord.Interaction, skill: str):
    bullets = [
        "Start with a clear research question and define key terms (use peer-reviewed references).",
        "Use primary sources (collections/archives) for evidence; then interpret with secondary literature.",
        "Document citations and keep a consistent reference style."
    ]
    refs = [
        {"name":"Stanford Encyclopedia of Philosophy", "url":"https://plato.stanford.edu/"},
        {"name":"The Met — Timeline of Art History", "url":"https://www.metmuseum.org/toah/"}
    ]
    e = _embed_from(f"Academic Skill — {skill}", bullets, refs)
    await interaction.response.send_message(embed=e)

bot.tree.add_command(academic_group)

@bot.tree.command(name="fashion", description="Academic-only fashion resources (free institutional links).")
@app_commands.describe(country="Optional 2-letter country code filter (e.g., BE, UK, JP, SE, US, TR, FR)")
async def fashion_cmd(interaction: discord.Interaction, country: str = ""):
    if not module_enabled(interaction, "fashion"):
        await interaction.response.send_message("The **fashion** module is disabled in this server.")
        return
    cc = (country or "").strip().upper()
    embed = discord.Embed(title="Fashion — Academic Resources (Free Links)")
    embed.description = "Curated institutional and peer-reviewed entry points. Academic links only."
    free = FASHION_REG.get("free_academic_fashion_sources", [])
    if cc:
        free = [s for s in free if (s.get("country","").upper() == cc)]
    if free:
        embed.add_field(
            name=("Free institutional sources" + (f" — {cc}" if cc else "")),
            value="\n".join(f"• {s.get('name')}: {s.get('url')}" for s in free[:12]),
            inline=False)
    else:
        embed.add_field(
            name="No matches",
            value="No sources found for that country code in the local registry. Try without a filter.",
            inline=False)
    journals = FASHION_REG.get("prestige_fashion_academic_journals_official", [])
    if journals and not cc:
        embed.add_field(
            name="Peer-reviewed journals (official pages)",
            value="\n".join(f"• {j.get('name')}: {j.get('url')}" for j in journals[:8]),
            inline=False)
    note = FASHION_REG.get("note")
    if note:
        embed.set_footer(text=note)
    await interaction.response.send_message(embed=embed)


# -------------------------
# Module settings (per-server enable/disable)
# -------------------------
settings_group = app_commands.Group(name="settings", description="Server settings (enable/disable modules).")

@settings_group.command(name="enable", description="Enable a module in this server (admin).")
@app_commands.describe(module="Module name (e.g., academic, fashion, trivia, dictionaries, weather)")
async def settings_enable(interaction: discord.Interaction, module: str):
    if interaction.guild is None:
        await interaction.response.send_message("This must be used in a server.")
        return
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("You need 'Manage Server' permission.")
        return
    db_set_module(interaction.guild_id, module, True)
    await interaction.response.send_message(f"Enabled module: **{module}**")

@settings_group.command(name="disable", description="Disable a module in this server (admin).")
@app_commands.describe(module="Module name (e.g., academic, fashion, trivia, dictionaries, weather)")
async def settings_disable(interaction: discord.Interaction, module: str):
    if interaction.guild is None:
        await interaction.response.send_message("This must be used in a server.")
        return
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("You need 'Manage Server' permission.")
        return
    db_set_module(interaction.guild_id, module, False)
    await interaction.response.send_message(f"Disabled module: **{module}**")

@settings_group.command(name="status", description="Show module status for this server.")
async def settings_status(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message("This must be used in a server.")
        return
    modules = ["academic", "fashion", "trivia", "dictionaries", "weather"]
    lines = []
    for m in modules:
        v = db_get_module(interaction.guild_id, m)
        status = "enabled (default)" if v is None else ("enabled" if v else "disabled")
        lines.append(f"• {m}: {status}")
    embed = discord.Embed(title="Module status")
    embed.description = "\n".join(lines)
    await interaction.response.send_message(embed=embed)

bot.tree.add_command(settings_group)

# -------------------------
# Governance commands
# -------------------------
governance_group = app_commands.Group(name="governance", description="Quality & governance (academic-only validation).")

@governance_group.command(name="status", description="Show governance validation status for registries.")
async def governance_status(interaction: discord.Interaction):
    embed = discord.Embed(title="Governance status")
    embed.description = governance_summary_text()
    await interaction.response.send_message(embed=embed)

@governance_group.command(name="report", description="Show a short governance violation report.")
async def governance_report(interaction: discord.Interaction):
    rules = (GOV_REG or {}).get("rules", {})
    max_items = int(rules.get("max_report_items", 50))
    violations = (GOV_REPORT or {}).get("violations", [])[:max_items]
    embed = discord.Embed(title="Governance report (top items)")
    if not violations:
        embed.description = "No violations detected in current registries."
        await interaction.response.send_message(embed=embed)
        return
    lines = []
    for v in violations:
        where = v.get("where","")
        url = v.get("url","")
        reason = v.get("reason","")
        lines.append(f"• [{v.get('module')}] {where} — {reason}" + (f" ({url})" if url else ""))
    embed.description = "\n".join(lines[:40])
    await interaction.response.send_message(embed=embed)

@governance_group.command(name="validate", description="Re-run validation (useful after registry edits).")
async def governance_validate(interaction: discord.Interaction):
    global GOV_REPORT
    GOV_REPORT = None  # computed in on_ready()
    embed = discord.Embed(title="Validation complete")
    embed.description = governance_summary_text()
    await interaction.response.send_message(embed=embed)

bot.tree.add_command(governance_group)

# -------------------------
# Registry admin (allows controlled updates to registries)
# -------------------------
registry_group = app_commands.Group(name="registry", description="Admin: update registries (allowlist validated).")

def _is_admin(interaction: discord.Interaction) -> bool:
    return interaction.guild is not None and interaction.user.guild_permissions.manage_guild


    def _validate_academic_url(url: str, kind: str) -> bool:
        kind_n = (kind or "").strip().lower()
        pub_domains = (GOV_REG or {}).get("allowlists", {}).get("publishers", {}).get("domains", [])
        inst_domains = (GOV_REG or {}).get("allowlists", {}).get("academic_institutional", {}).get("domains", [])
        if kind_n in ("publisher", "journal_platform", "press"):
            return _allowed(url, pub_domains)
        return _allowed(url, inst_domains)

def _validate_url_for_section(url: str, section: str) -> bool:
    domains = (GOV_REG or {}).get("allowlists", {}).get(section, {}).get("domains", [])
    return _allowed(url, domains)

@registry_group.command(name="add_fashion_source", description="Admin: add an institutional fashion source (validated).")
@app_commands.describe(name="Display name", url="Official URL", country="2-letter code (e.g., BE, UK, JP, SE, US, TR, FR)", notes="Optional notes")
async def add_fashion_source(interaction: discord.Interaction, name: str, url: str, country: str, notes: str = ""):
    if not _is_admin(interaction):
        await interaction.response.send_message("You need 'Manage Server' permission.")
        return
    if not _validate_url_for_section(url, "fashion"):
        await interaction.response.send_message("URL domain is not in the **fashion** allowlist.")
        return
    obj = {
        "name": name.strip(),
        "url": url.strip(),
        "type": "institutional_source",
        "country": country.strip().upper(),
        "notes": notes.strip()
    }
    FASHION_REG.setdefault("free_academic_fashion_sources", []).append(obj)
    FASHION_REG["generated_utc"] = datetime.utcnow().replace(microsecond=0).isoformat()+"Z"
    save_json(FASHION_PATH, FASHION_REG)
    await interaction.response.send_message(f"Added fashion source: **{obj['name']}** ({obj['country']})")

@registry_group.command(name="add_academic_ref", description="Admin: add an academic reference hub entry (validated).")
@app_commands.describe(group="Hub group (e.g., museums, philosophy, game_studies)", name="Display name", url="Official URL", kind="institutional|publisher|journal_platform|press")
async def add_academic_ref(interaction: discord.Interaction, group: str, name: str, url: str, kind: str = "institutional"):
    if not _is_admin(interaction):
        await interaction.response.send_message("You need 'Manage Server' permission.")
        return
    if not _validate_academic_url(url, kind):
            await interaction.response.send_message("URL domain is not allowed for the selected kind (institutional vs publisher).")
            return
    g = group.strip()
    ACADEMIC_REG.setdefault("reference_hubs", {}).setdefault(g, []).append({
            "name": name.strip(),
            "url": url.strip(),
            "type": (kind.strip().lower() or "reference_hub")
        })
    ACADEMIC_REG["generated_utc"] = datetime.utcnow().replace(microsecond=0).isoformat()+"Z"
    save_json(ACADEMIC_PATH, ACADEMIC_REG)
    await interaction.response.send_message(f"Added academic hub item to **{g}**: {name.strip()}")

@registry_group.command(name="validate", description="Admin: re-run governance validation after registry updates.")
async def registry_validate(interaction: discord.Interaction):
    if not _is_admin(interaction):
        await interaction.response.send_message("You need 'Manage Server' permission.")
        return
    global GOV_REPORT
    GOV_REPORT = None  # computed in on_ready()
    await interaction.response.send_message(governance_summary_text())

bot.tree.add_command(registry_group)



# -------------------------
# Governance / Quality
# -------------------------
def _domain(url: str) -> str:
    try:
        from urllib.parse import urlparse, quote_plus
        host = urlparse(url).netloc.lower()
        host = host.split(":")[0]
        return host
    except Exception:
        return ""

def _allowed(url: str, allowed_domains: list) -> bool:
    host = _domain(url)
    if not host:
        return False
    for d in allowed_domains:
        d = d.lower().strip()
        if host == d or host.endswith("." + d):
            return True
    return False

def validate_registry_links() -> dict:
    """Validate registry JSON files against domain allowlists and required references.
    Returns a report dict with violations.
    """
    report = {
        "generated_utc": datetime.utcnow().replace(microsecond=0).isoformat()+"Z",
        "violations": [],
        "counts": {"checked_urls": 0, "violations": 0},
    }
    rules = (GOV_REG or {}).get("rules", {})
    allow = (GOV_REG or {}).get("allowlists", {})

    def add_violation(module: str, where: str, url: str, reason: str):
        report["violations"].append({"module": module, "where": where, "url": url, "reason": reason})
        report["counts"]["violations"] += 1

    # --- dictionaries ---
    dic_allow = allow.get("dictionaries", {}).get("domains", [])
    try:
        for d in DICT_REG.get("dictionaries", []):
            url = d.get("official_url")
            if url:
                report["counts"]["checked_urls"] += 1
                if dic_allow and not _allowed(url, dic_allow):
                    add_violation("dictionaries", d.get("name","unknown"), url, "Domain not in allowlist")
    except Exception as e:
        add_violation("dictionaries", "registry", "", f"Registry parse error: {e}")

    # --- weather ---
    w_allow = allow.get("weather", {}).get("domains", [])
    try:
        for hub in METEO_REG.get("global_official_hubs", []):
            url = hub.get("official_url")
            if url:
                report["counts"]["checked_urls"] += 1
                if w_allow and not _allowed(url, w_allow):
                    add_violation("weather", hub.get("name","hub"), url, "Domain not in allowlist")
        for cc, svc in METEO_REG.get("services_by_country", {}).items():
            url = svc.get("official_url")
            if url:
                report["counts"]["checked_urls"] += 1
                if w_allow and not _allowed(url, w_allow):
                    add_violation("weather", f"{cc}:{svc.get('service_name','service')}", url, "Domain not in allowlist")
    except Exception as e:
        add_violation("weather", "registry", "", f"Registry parse error: {e}")

    # --- fashion ---
    f_allow = allow.get("fashion", {}).get("domains", [])
    try:
        for s in FASHION_REG.get("free_academic_fashion_sources", []):
            url = s.get("url")
            if url:
                report["counts"]["checked_urls"] += 1
                if f_allow and not _allowed(url, f_allow):
                    add_violation("fashion", s.get("name","source"), url, "Domain not in allowlist")
        for j in FASHION_REG.get("prestige_fashion_academic_journals_official", []):
            url = j.get("url")
            if url:
                report["counts"]["checked_urls"] += 1
                if f_allow and not _allowed(url, f_allow):
                    add_violation("fashion", j.get("name","journal"), url, "Domain not in allowlist")
    except Exception as e:
        add_violation("fashion", "registry", "", f"Registry parse error: {e}")

    # --- academic ---
    a_inst = allow.get("academic_institutional", {}).get("domains", [])
    a_pub = allow.get("publishers", {}).get("domains", [])
    try:
        for group, items in (ACADEMIC_REG.get("reference_hubs", {}) or {}).items():
            for it in items:
                url = it.get("url")
                if url:
                    report["counts"]["checked_urls"] += 1
                    ref_type = (it.get("type") or "").lower()
                    use_pub = ref_type in ("publisher","journal_platform","press")
                    domains = a_pub if use_pub else a_inst
                    if domains and not _allowed(url, domains):
                        add_violation("academic", f"hub:{group}:{it.get('name','item')}", url, "Domain not in allowlist")
        for mod, mapping in (ACADEMIC_REG.get("modules", {}) or {}).items():
            for key, obj in (mapping or {}).items():
                refs = obj.get("refs", [])
                if rules.get("require_reference_field", True):
                    if not refs:
                        add_violation("academic", f"module:{mod}:{key}", "", "Missing refs[]")
                for r in refs:
                    url = r.get("url")
                    if url:
                        report["counts"]["checked_urls"] += 1
                        ref_type = (it.get("type") or "").lower()
                    use_pub = ref_type in ("publisher","journal_platform","press")
                    domains = a_pub if use_pub else a_inst
                    if domains and not _allowed(url, domains):
                            add_violation("academic", f"module:{mod}:{key}:{r.get('name','ref')}", url, "Domain not in allowlist")
    except Exception as e:
        add_violation("academic", "registry", "", f"Registry parse error: {e}")

    return report

GOV_REPORT = None  # computed in on_ready()

def governance_summary_text() -> str:
    if not isinstance(GOV_REPORT, dict):
        return "Governance report not ready."
    v = GOV_REPORT.get("counts", {}).get("violations", 0)
    checked = GOV_REPORT.get("counts", {}).get("checked_urls", 0)
    return f"Checked URLs: {checked} | Violations: {v}"

# -------------------------
# Tesla MIT drawing image resolver + cache
# -------------------------
MIT_TESLA_ALPHA_URL = "https://web.mit.edu/most/Public/Tesla1/alpha_tesla.html"

TESLA_MIT_IMAGE_CACHE_PATH = os.path.join(DATA_DIR, "tesla_mit_image_cache.json")
TESLA_MIT_IMAGE_CACHE = load_json(TESLA_MIT_IMAGE_CACHE_PATH) if os.path.exists(TESLA_MIT_IMAGE_CACHE_PATH) else {}

def _norm_patno(patent_number: str) -> str:
    return (patent_number or "").strip().replace(",", "").replace(" ", "")

def _is_image_url(u: str) -> bool:
    u = (u or "").lower()
    return any(u.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"))

async def _fetch_text(url: str, timeout: int = 20) -> str:
    headers = {"User-Agent": "Bottany/1.0 (+https://railway.app)"}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url, timeout=timeout) as resp:
            resp.raise_for_status()
            return await resp.text()

async def _url_exists(url: str, timeout: int = 10) -> bool:
    try:
        headers = {"User-Agent": "Bottany/1.0 (+https://railway.app)"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.head(url, allow_redirects=True, timeout=timeout) as resp:
                return 200 <= resp.status < 400
    except Exception:
        return False

def _mit_cache_get(pat: str):
    # Note: cache stores URL string OR None (negative cache)
    return TESLA_MIT_IMAGE_CACHE.get(str(pat))

def _mit_cache_set(pat: str, image_url):
    TESLA_MIT_IMAGE_CACHE[str(pat)] = image_url  # None allowed
    save_json(TESLA_MIT_IMAGE_CACHE_PATH, TESLA_MIT_IMAGE_CACHE)

async def mit_tesla_patent_image_url(patent_number: str) -> Optional[str]:
    """
    Resolve a patent drawing image URL from MIT's Tesla collection.
    Uses JSON cache (positive + negative).
    """
    pat = _norm_patno(patent_number)
    if not pat.isdigit():
        return None

    cached = _mit_cache_get(pat)
    if cached is not None:
        return cached  # may be URL or None

    # Load alpha table
    try:
        html = await _fetch_text(MIT_TESLA_ALPHA_URL, timeout=25)
    except Exception:
        _mit_cache_set(pat, None)
        return None

    soup = BeautifulSoup(html, "html.parser")

    # Find row containing the patent number
    target_tr = None
    for tr in soup.find_all("tr"):
        txt = tr.get_text(" ", strip=True).replace(",", "")
        if pat in txt.split():
            target_tr = tr
            break

    if not target_tr:
        _mit_cache_set(pat, None)
        return None

    # Collect candidate links from the row
    candidates = []
    for a in target_tr.find_all("a", href=True):
        abs_href = urljoin(MIT_TESLA_ALPHA_URL, a["href"].strip())
        candidates.append(abs_href)

    # Direct image link?
    for u in candidates:
        if _is_image_url(u) and await _url_exists(u):
            _mit_cache_set(pat, u)
            return u

    # Follow likely MIT detail pages and pick best-looking drawing image
    for page_url in candidates:
        if "web.mit.edu/most/Public/Tesla1/" not in page_url:
            continue
        try:
            page_html = await _fetch_text(page_url, timeout=20)
        except Exception:
            continue

        psoup = BeautifulSoup(page_html, "html.parser")
        imgs = psoup.find_all("img", src=True)

        scored = []
        for img in imgs:
            abs_src = urljoin(page_url, img["src"].strip())
            if not _is_image_url(abs_src):
                continue
            score = 0
            low = abs_src.lower()
            if pat in low:
                score += 5
            if any(k in low for k in ("fig", "figure", "drawing", "patent")):
                score += 2
            scored.append((score, abs_src))

        if scored:
            scored.sort(key=lambda x: x[0], reverse=True)
            best = scored[0][1]
            _mit_cache_set(pat, best)
            return best

    _mit_cache_set(pat, None)
    return None

# -------------------------
# Tesla module (one item per call; caches up to 150)
# Institutional/public sources:
# - MIT: https://web.mit.edu/most/Public/Tesla1/alpha_tesla.html
# - Nikola Tesla Museum (Belgrade) PDF: https://tesla-museum.org/wp-content/uploads/2023/05/lista_patenata_eng.pdf
# -------------------------
TESLA_REG_PATH = os.path.join(DATA_DIR, "tesla_registry.json")
# --- Art / Animation registries (code-independent JSON) ---
def load_json_registry(filename: str) -> dict:
    path = os.path.join(DATA_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Could not load registry %s: %s", filename, e)
        return {}

PAINTERS_REGISTRY = load_json_registry("painters_registry.json")
ANIMATION_AWARDS_REGISTRY = load_json_registry("animation_awards_registry.json")
ANIMATION_TECH_REGISTRY = load_json_registry("animation_techniques_registry.json")
ANIMATION_INTL_AWARDS_REGISTRY = load_json_registry("animation_international_awards_registry.json")
FOOD_SOURCES_REGISTRY = load_json_registry("food_sources_registry.json")
MICHELIN_REGISTRY = load_json_registry("michelin_starred_registry.json")
RESTAURANT_AWARDS_REGISTRY = load_json_registry("restaurant_awards_registry.json")
ANIME_HISTORY_QUOTES = load_json_registry("anime_history_quotes.json")


async def met_object(object_id: int) -> dict:
    # Official: The Met Collection API (public)
    url = f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{int(object_id)}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=20) as resp:
            if resp.status != 200:
                return {}
            return await resp.json()

TESLA_REG = load_json(TESLA_REG_PATH) if os.path.exists(TESLA_REG_PATH) else {}
TESLA_CACHE_PATH = os.path.join(DATA_DIR, (TESLA_REG.get("cache", {}) or {}).get("cache_file", "tesla_cache.json"))

def _safe_get(url: str, timeout: int = 20) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; BottanyBot/1.0; +https://railway.app)",
        "Accept": "*/*",
    }
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.text

def _extract_mit_tesla_patents(html: str) -> List[dict]:
    """
    Parse MIT Tesla alpha table into a list of patents.
    More robust than regex parsing.
    """
    soup = BeautifulSoup(html, "html.parser")
    items: List[dict] = []

    for tr in soup.find_all("tr"):
        # Get cells
        cells = tr.find_all(["td", "th"])
        if len(cells) < 4:
            continue

        # Plain text per cell
        cols = [c.get_text(" ", strip=True) for c in cells]
        cols_clean = [re.sub(r"\s+", " ", c).strip() for c in cols]

        # Try to find a patent number (digits, often with commas)
        joined = " ".join(cols_clean)
        m = re.search(r"\b(\d{3,}(?:,\d{3})*)\b", joined)
        if not m:
            continue

        patno = m.group(1).replace(",", "")
        if not patno.isdigit():
            continue

        # Heuristic: title tends to be the first non-empty cell
        title = ""
        for c in cols_clean:
            if c and not re.fullmatch(r"\d+(?:,\d+)*", c):
                title = c
                break

        # Heuristic: attempt to build a grant date if month/day/year appear
        # MIT table often has Month Day Year in separate columns, but format may vary.
        grant_date = ""
        # pull tokens that look like Month Day, Year patterns
        # Example: "Jan 5 1897" or "January 5, 1897" (best effort)
        date_match = re.search(
            r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\b"
            r"\s+(\d{1,2})(?:,)?\s+(\d{4})\b",
            joined,
            flags=re.IGNORECASE,
        )
        if date_match:
            mo, dd, yy = date_match.group(1), date_match.group(2), date_match.group(3)
            grant_date = f"{mo} {dd}, {yy}"

        items.append(
            {
                "title": title or "(untitled)",
                "kind": "patent",
                "patent_number": patno,
                "grant_date": grant_date,
                "source_name": "MIT Tesla U.S. Patent Collection",
                "source_url": "https://web.mit.edu/most/Public/Tesla1/alpha_tesla.html",
                "type": "institutional",
            }
        )

    # Deduplicate by patent_number
    seen = set()
    dedup = []
    for it in items:
        p = it.get("patent_number")
        if not p or p in seen:
            continue
        seen.add(p)
        dedup.append(it)

    return dedup

def _extract_tesla_museum_pdf_lines(text: str):
    items = []
    for line in text.splitlines():
        m = re.match(r"^\s*(\d+)\.\s+(.+?)\s+(\d{2}\.\d{2}\.\d{4}).*?(\d{3,},?\d*)\s*$", line.strip())
        if m:
            idx, title, filing, patno = m.group(1), m.group(2).strip(), m.group(3), m.group(4).replace(",", "")
            items.append({
                "title": title,
                "kind": "patent",
                "patent_number": patno,
                "grant_date": "",
                "source_name": "Nikola Tesla Museum (Belgrade)",
                "source_url": "https://tesla-museum.org/wp-content/uploads/2023/05/lista_patenata_eng.pdf",
                "type": "institutional"
            })
    return items

def _load_tesla_cache():
    if os.path.exists(TESLA_CACHE_PATH):
        try:
            return load_json(TESLA_CACHE_PATH)
        except Exception:
            return {}
    return {}

def _save_tesla_cache(obj: dict) -> None:
    save_json(TESLA_CACHE_PATH, obj)

def _build_tesla_catalog(target_count: int = 150) -> dict:
    items: List[dict] = []

    # MIT HTML
    try:
        html = _safe_get("https://web.mit.edu/most/Public/Tesla1/alpha_tesla.html")
        extracted = _extract_mit_tesla_patents(html)
        logger.info("Tesla MIT extract: %d items", len(extracted))
        items.extend(extracted)
    except Exception as e:
        logger.exception("Tesla MIT fetch/parse failed: %s", e)

    # Deduplicate
    seen = set()
    dedup: List[dict] = []
    for it in items:
        key = (it.get("patent_number", ""), (it.get("title", "") or "").lower())
        if key in seen:
            continue
        if not it.get("title"):
            continue
        seen.add(key)
        dedup.append(it)

    if not dedup:
        logger.warning("Tesla catalog empty; using fallback items")
        dedup = FALLBACK_TESLA_ITEMS[:]

    dedup = dedup[:target_count]

    return {
        "generated_utc": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "count": len(dedup),
        "items": dedup,
    }

FALLBACK_TESLA_ITEMS = [
    {
        "title": "Alternating electric current generator",
        "kind": "patent",
        "patent_number": "",
        "grant_date": "",
        "source_name": "MIT Tesla U.S. Patent Collection",
        "source_url": "https://web.mit.edu/most/Public/Tesla1/alpha_tesla.html",
        "type": "institutional",
    },
    {
        "title": "System of electrical distribution",
        "kind": "patent",
        "patent_number": "",
        "grant_date": "",
        "source_name": "MIT Tesla U.S. Patent Collection",
        "source_url": "https://web.mit.edu/most/Public/Tesla1/alpha_tesla.html",
        "type": "institutional",
    },
]

def _ensure_tesla_cache():
    target = int((TESLA_REG.get("cache", {}) or {}).get("target_count", 150))
    refresh_days = int((TESLA_REG.get("cache", {}) or {}).get("refresh_days", 30))
    cache = _load_tesla_cache()
    try:
        ts = cache.get("generated_utc", "")
        stale = True
        if ts:
            dt = datetime.fromisoformat(ts.replace("Z", ""))
            stale = (datetime.utcnow() - dt).days >= refresh_days
        if stale or cache.get("count", 0) < min(25, target):
            cache = _build_tesla_catalog(target_count=target)
            _save_tesla_cache(cache)
    except Exception:
        cache = _build_tesla_catalog(target_count=target)
        _save_tesla_cache(cache)
    return cache

# -------------------------
# Wikimedia Commons drawing resolver + cache (public-domain fallback)
# -------------------------
TESLA_WIKI_IMAGE_CACHE_PATH = os.path.join(DATA_DIR, "tesla_wikimedia_image_cache.json")
TESLA_WIKI_IMAGE_CACHE = load_json(TESLA_WIKI_IMAGE_CACHE_PATH) if os.path.exists(TESLA_WIKI_IMAGE_CACHE_PATH) else {}

def _wiki_cache_get(pat: str):
    # stores URL string OR None (negative cache)
    return TESLA_WIKI_IMAGE_CACHE.get(str(pat))

def _wiki_cache_set(pat: str, image_url):
    TESLA_WIKI_IMAGE_CACHE[str(pat)] = image_url  # None allowed
    save_json(TESLA_WIKI_IMAGE_CACHE_PATH, TESLA_WIKI_IMAGE_CACHE)

async def wikimedia_tesla_patent_image_url(patent_number: str) -> Optional[str]:
    """
    Public-domain fallback: try to resolve a Tesla patent drawing from Wikimedia Commons.
    Uses Special:FilePath and caches hits (positive + negative).
    """
    pat = _norm_patno(patent_number)
    if not pat.isdigit():
        return None

    cached = _wiki_cache_get(pat)
    if cached is not None:
        return cached  # URL or None

    # Common filename patterns on Commons
    candidates = [
        f"Tesla_patent_{pat}.png",
        f"Tesla_patent_{pat}.jpg",
        f"Tesla_patent_{pat}.jpeg",
        f"Tesla_patent_{pat}.svg",
        f"US{pat}.png",
        f"US{pat}.jpg",
        f"US{pat}.jpeg",
        f"US{pat}.svg",
    ]

    for fname in candidates:
        url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{fname}"
        if await _url_exists(url):
            _wiki_cache_set(pat, url)
            return url

    _wiki_cache_set(pat, None)
    return None

tesla_group = app_commands.Group(
    name="tesla",
    description="Nikola Tesla: one invention/patent per call (institutional sources)."
)

@tesla_group.command(
    name="random",
    description="Show one Nikola Tesla invention/patent (one item per call)."
)
async def tesla_random(interaction: discord.Interaction):
    # MUST be first to avoid "Unknown interaction"
    await interaction.response.defer(thinking=True)

    cache = _ensure_tesla_cache()
    items = cache.get("items", []) or []
    if not items:
        await interaction.followup.send(
            "No Tesla items could be loaded right now. Try again later."
        )
        return

    it = random.choice(items)

    title = it.get("title", "(untitled)")
    pat = it.get("patent_number", "")
    date = it.get("grant_date", "")
    src_name = it.get("source_name", "Source")
    src_url = it.get("source_url", "")

    embed = discord.Embed(title=f"Tesla — {title}")

    if pat:
        embed.add_field(name="Patent #", value=pat, inline=True)
    if date:
        embed.add_field(name="Grant date", value=date, inline=True)
    if src_url:
        embed.add_field(
            name="Source (institutional)",
            value=f"[{src_name}]({src_url})",
            inline=False
        )

    # -------------------------
    # Drawing (MIT first, Wikimedia fallback)
    # -------------------------
    img_url = None
    drawing_label = None

    if pat:
        try:
            img_url = await mit_tesla_patent_image_url(pat)
        except Exception as e:
            logger.warning("MIT image resolve failed for patent %s: %s", pat, e)
            img_url = None

        if img_url:
            drawing_label = "📐 Original patent drawing (MIT)"
        else:
            try:
                img_url = await wikimedia_tesla_patent_image_url(pat)
            except Exception as e:
                logger.warning("Wikimedia image resolve failed for patent %s: %s", pat, e)
                img_url = None

            if img_url:
                drawing_label = "📐 Public-domain drawing (Wikimedia Commons)"

    if img_url:
        embed.set_image(url=img_url)
        embed.add_field(name="Drawing", value=drawing_label, inline=False)
    else:
        embed.add_field(
            name="Drawing",
            value="No official drawing available",
            inline=False
        )

    target = int((TESLA_REG.get("cache", {}) or {}).get("target_count", 150))
    embed.set_footer(
        text=f"Catalog size: {cache.get('count', 0)} / target {target}"
    )

    await interaction.followup.send(embed=embed)


@tesla_group.command(name="sources", description="Show institutional sources used for Tesla items.")
async def tesla_sources(interaction: discord.Interaction):
    sources = (TESLA_REG.get("sources", []) or [])
    if not sources:
        await interaction.response.send_message("No sources configured.")
        return
    embed = discord.Embed(title="Tesla — Sources")
    for s in sources[:10]:
        embed.add_field(name=s.get("name", "Source"), value=f"[Open]({s.get('url', '')})", inline=False)
    if len(sources) > 10:
        embed.set_footer(text=f"+{len(sources)-10} more in registry")
    await interaction.response.send_message(embed=embed)

bot.tree.add_command(tesla_group)


# -------------------------
# Da Vinci module (registry + pagination)
# Official/institutional public sources only.
# -------------------------
DAVINCI_REG_PATH = os.path.join(DATA_DIR, "davinci_registry.json")
DAVINCI_REG = load_json(DAVINCI_REG_PATH) if os.path.exists(DAVINCI_REG_PATH) else {}

def _davinci_items(category: str = ""):
    items = (DAVINCI_REG.get("items", []) or [])
    cat = (category or "").strip().lower()
    if cat and cat != "all":
        items = [it for it in items if (it.get("category","").lower() == cat)]
    return items

davinci_group = app_commands.Group(name="davinci", description="Leonardo da Vinci: registry-based resources with pagination (official sources).")

@davinci_group.command(name="list", description="List Da Vinci items with pagination.")
@app_commands.describe(category="all|machine|drawing|manuscript|painting", page="Page number (starts at 1)")
async def davinci_list(interaction: discord.Interaction, category: str = "all", page: int = 1):
    items = _davinci_items(category)
    if not items:
        await interaction.response.send_message("No Da Vinci items found for that category.")
        return

    page_size = int((DAVINCI_REG.get("pagination", {}) or {}).get("page_size", 8))
    page = max(1, int(page))
    start = (page - 1) * page_size
    end = start + page_size
    chunk = items[start:end]

    if not chunk:
        await interaction.response.send_message("That page is out of range.")
        return

    total_pages = (len(items) + page_size - 1) // page_size
    title = f"Da Vinci — {category.upper()} (Page {page}/{total_pages})"
    embed = discord.Embed(title=title)
    lines = []
    for it in chunk:
        name = it.get("title", "Untitled")
        url = it.get("url", "")
        note = it.get("note", "")
        if url:
            lines.append(f"• **{name}** — {note}\n  {url}")
        else:
            lines.append(f"• **{name}** — {note}")
    embed.description = "\n".join(lines[:15])
    await interaction.response.send_message(embed=embed)

@davinci_group.command(name="random", description="Show one Da Vinci item (one per call).")
@app_commands.describe(category="all|machine|drawing|manuscript|painting")
async def davinci_random(interaction: discord.Interaction, category: str = "all"):
    items = _davinci_items(category)
    if not items:
        await interaction.response.send_message("No Da Vinci items found for that category.")
        return
    it = random.choice(items)
    embed = discord.Embed(title=f"Da Vinci — {it.get('title','Untitled')}")
    if it.get("note"):
        embed.description = it.get("note")
    if it.get("url"):
        embed.add_field(name="Official/Institutional link", value=it["url"], inline=False)
    await interaction.response.send_message(embed=embed)

@davinci_group.command(name="sources", description="Show the official/institutional sources used for Da Vinci items.")
async def davinci_sources(interaction: discord.Interaction):
    sources = (DAVINCI_REG.get("sources", []) or [])
    if not sources:
        await interaction.response.send_message("No sources configured.")
        return
    embed = discord.Embed(title="Da Vinci — Official/Institutional Sources")
    for s in sources[:10]:
        embed.add_field(name=s.get("name", "Source"), value=s.get("url", ""), inline=False)
    if len(sources) > 10:
        embed.set_footer(text=f"+{len(sources)-10} more in registry")
    await interaction.response.send_message(embed=embed)

bot.tree.add_command(davinci_group)


# -------------------------
# Philosophy module (academic-only)
# -------------------------
PHILO_REG_PATH = os.path.join(DATA_DIR, "philosophy_registry.json")
PHILO_REG = load_json(PHILO_REG_PATH) if os.path.exists(PHILO_REG_PATH) else {}

philosophy_group = app_commands.Group(name="philosophy", description="Academic philosophy explanations (source-based).")

def _mk_ref_lines(refs: list) -> str:
    lines = []
    for r in refs or []:
        name = r.get("name","Reference")
        url = r.get("url","")
        if url:
            lines.append(f"• {name}\n  {url}")
        else:
            lines.append(f"• {name}")
    return "\n".join(lines) if lines else "(No references configured.)"

@philosophy_group.command(name="game_theory", description="Explain John Nash’s game theory (pure theory; no video-game connection).")
async def philosophy_game_theory(interaction: discord.Interaction):
    mod = ((PHILO_REG.get("modules", {}) or {}).get("game_theory", {}) or {})
    if not mod:
        await interaction.response.send_message("Game theory module is not configured.")
        return

    embed = discord.Embed(title=mod.get("title", "Game Theory — John Nash"))

    summary = mod.get("summary", []) or []
    if summary:
        embed.description = "\n".join(f"• {s}" for s in summary[:6])

    # Key concepts (compact)
    concepts = mod.get("key_concepts", []) or []
    if concepts:
        block = "\n".join([f"**{c.get('term')}** — {c.get('definition')}" for c in concepts[:6]])
        embed.add_field(name="Core concepts", value=block[:1024], inline=False)

    results = mod.get("core_results", []) or []
    if results:
        embed.add_field(name="Core results (Nash)", value="\n".join(f"• {r}" for r in results[:6])[:1024], inline=False)

    how = mod.get("how_to_read", []) or []
    if how:
        embed.add_field(name="How to approach problems", value="\n".join(f"{i+1}. {s}" for i,s in enumerate(how[:6]))[:1024], inline=False)

    refs = mod.get("refs", []) or []
    embed.add_field(name="Academic references (official)", value=_mk_ref_lines(refs)[:1024], inline=False)

    await interaction.response.send_message(embed=embed)

bot.tree.add_command(philosophy_group)


# -------------------------
# Music Companion (ToS-safe): No audio streaming.
# Provides official platform links and optional voice channel join/leave.
# -------------------------
MUSIC_REG_PATH = os.path.join(DATA_DIR, "music_registry.json")
MUSIC_REG = load_json(MUSIC_REG_PATH) if os.path.exists(MUSIC_REG_PATH) else {}

music_group = app_commands.Group(name="music", description="Music companion (links only; no streaming).")

def _platform_links(query: str) -> list[tuple[str,str]]:
    q = quote_plus(query.strip())
    out = []
    for p in (MUSIC_REG.get("platforms", []) or []):
        name = p.get("name","Platform")
        tmpl = p.get("url_template","")
        if tmpl:
            out.append((name, tmpl.replace("{q}", q)))
    return out

def _playlist_links(mood: str) -> list[tuple[str,str]]:
    m = (mood or "").strip().lower()
    items = ((MUSIC_REG.get("playlists", {}) or {}).get(m, []) or [])
    return [(it.get("name","Playlist"), it.get("url","")) for it in items if it.get("url")]

@music_group.command(name="recommend", description="Get official search links for a song/artist (no streaming).")
@app_commands.describe(query="Song, artist, or album")
async def music_recommend(interaction: discord.Interaction, query: str):
    if not await enforce_rate_limit(interaction, "music_recommend", cooldown_seconds=5):
        return

    links = _platform_links(query)
    if not links:
        await interaction.response.send_message("Music registry is not configured.")
        return

    embed = discord.Embed(
        title="Music — Official links",
        description=f"Query: **{query.strip()}**\n\nChoose a platform:"
    )
    embed.set_footer(text="Links only (ToS-safe). Bottany does not stream audio.")

    class _LinkView(discord.ui.View):
        def __init__(self, items):
            super().__init__(timeout=180)
            for name, url in items[:5]:
                self.add_item(discord.ui.Button(label=name, url=url))

    view = _LinkView(links)
    await interaction.response.send_message(embed=embed, view=view)

@music_group.command(name="playlist", description="Get official playlist links by mood (no streaming).")
@app_commands.describe(mood="focus|soft|gaming")
async def music_playlist(interaction: discord.Interaction, mood: str):
    if not await enforce_rate_limit(interaction, "music_playlist", cooldown_seconds=5):
        return
    links = _playlist_links(mood)
    if not links:
        await interaction.response.send_message("No playlists found for that mood. Try: focus, soft, gaming.")
        return
    embed = discord.Embed(title=f"Music — {mood.strip().lower()} playlists (official links)")
    for name, url in links[:8]:
        embed.add_field(name=name, value=url, inline=False)
    embed.set_footer(text="Links only (ToS-safe).")
    await interaction.response.send_message(embed=embed)

@music_group.command(name="nowplaying", description="Share a Spotify/YouTube/Apple Music link as 'Now Playing' (no streaming).")
@app_commands.describe(url="A track/video URL from a supported platform")
async def music_nowplaying(interaction: discord.Interaction, url: str):
    u = (url or "").strip()
    if not u.startswith("http"):
        await interaction.response.send_message("Please provide a valid URL (starting with http/https).")
        return
    host = urlparse(u).netloc.lower().split(":")[0]
    host = host[4:] if host.startswith("www.") else host
    allowed = set(((GOV_REG or {}).get("allowlists", {}) or {}).get("music", {}).get("domains", []) or [])
    if allowed and (host not in allowed and not any(host.endswith("."+d) for d in allowed)):
        await interaction.response.send_message("Unsupported domain. Please use Spotify, YouTube, or Apple Music.")
        return
    embed = discord.Embed(title="Now Playing (shared link)", description=u)
    embed.set_footer(text="Bottany does not play audio. This is a shared official link.")
    await interaction.response.send_message(embed=embed)

@music_group.command(name="join", description="Join your current voice channel (no audio playback).")
async def music_join(interaction: discord.Interaction):
    if not interaction.user or not getattr(interaction.user, "voice", None) or not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("You are not in a voice channel.")
        return
    channel = interaction.user.voice.channel
    try:
        if interaction.guild and interaction.guild.voice_client:
            await interaction.guild.voice_client.move_to(channel)
        else:
            await channel.connect()
        await interaction.response.send_message(f"Joined voice channel: **{channel.name}** (no audio playback).")
    except Exception as e:
        await interaction.response.send_message("Could not join the voice channel. (Voice support may require additional dependencies.)")

@music_group.command(name="leave", description="Leave the current voice channel.")
async def music_leave(interaction: discord.Interaction):
    try:
        if interaction.guild and interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect(force=True)
            await interaction.response.send_message("Left the voice channel.")
        else:
            await interaction.response.send_message("I am not connected to a voice channel.")
    except Exception:
        await interaction.response.send_message("Could not leave the voice channel.")

@music_group.command(name="sources", description="Show supported music platforms (links only).")
async def music_sources(interaction: discord.Interaction):
    plats = (MUSIC_REG.get("platforms", []) or [])
    if not plats:
        await interaction.response.send_message("Music registry is not configured.")
        return
    embed = discord.Embed(title="Music — Supported platforms (links only)")
    for p in plats[:10]:
        embed.add_field(name=p.get("name","Platform"), value=p.get("url_template",""), inline=False)
    embed.set_footer(text="No audio streaming; ToS-safe link sharing.")
    await interaction.response.send_message(embed=embed)

bot.tree.add_command(music_group)



# (Weather and free-games commands are registered via commands/ modules in on_ready.)


# Awards
awards_group = app_commands.Group(name="awards", description="Game awards lookup (official sources; registry-based).")

@awards_group.command(name="categories", description="Show award sources and known categories/slugs.")
@app_commands.describe(award="tga|bafta|dice|gja")
async def awards_categories(interaction: discord.Interaction, award: str):
    if not await enforce_rate_limit(interaction, "awards_categories", cooldown_seconds=10):
        return
    aid = _norm(award)
    embed = discord.Embed(title="Awards — Categories / Sources")
    if aid == "tga":
        embed.add_field(name="Official winners hub", value="https://thegameawards.com/winners", inline=False)
    elif aid == "bafta":
        slugs = (((AWARDS_SOURCES.get("awards", {}) or {}).get("bafta", {}) or {}).get("known_category_slugs", []) or [])
        embed.add_field(name="Known BAFTA category slugs", value="\n".join(f"• {s}" for s in slugs[:25]) or "(none)", inline=False)
        embed.add_field(name="Official hub", value="https://www.bafta.org/awards/games/", inline=False)
        embed.add_field(name="Tip", value="Run /awards sync award:bafta param:<slug> to cache a category.", inline=False)
    elif aid == "dice":
        embed.add_field(name="Official hub", value="https://www.interactive.org/awards/", inline=False)
        dice_cache = _cache_get("dice")
        pages = (dice_cache.get("results_pages", []) or [])[:10]
        if pages:
            embed.add_field(name="Cached results pages (sample)", value="\n".join(f"• {p.get('url','')}" for p in pages), inline=False)
        else:
            embed.add_field(name="Tip", value="Run /awards sync award:dice to cache results pages.", inline=False)
    elif aid == "gja":
        embed.add_field(name="Organizer hub", value="https://www.gamesradar.com/goldenjoystickawards/", inline=False)
        embed.add_field(name="Year template", value="https://www.gamesradar.com/.../golden-joystick-awards-{year}-all-winners/", inline=False)
        embed.add_field(name="Tip", value="Run /awards sync award:gja param:<year> to cache a year.", inline=False)
    else:
        await interaction.response.send_message("Unknown award id. Use: tga, bafta, dice, gja.")
        return
    await interaction.response.send_message(embed=embed)

@awards_group.command(name="sync_all", description="Admin: sync BAFTA (all slugs), DICE hub, and GJA (recent years) into cache.")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(gja_years_back="How many years back to sync for GJA (default 2)", sleep_seconds="Delay between requests (default 2)", force="Force refresh even if cached")
async def awards_sync_all(interaction: discord.Interaction, gja_years_back: int = 2, sleep_seconds: int = 2, force: bool = False):
    if not await enforce_rate_limit(interaction, "awards_sync_all", cooldown_seconds=45):
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    done = 0
    failed = 0
    try:
        sleep_s = max(0, int(sleep_seconds))
        now_year = datetime.utcnow().year

        # DICE
        try:
            if force or not _cache_get("dice"):
                data = _sync_awards_dice_hub()
                if data:
                    _cache_set("dice", data); done += 1
                else:
                    failed += 1
        except Exception as e:
            logger.warning("sync_all: DICE failed: %s", e); failed += 1
        await asyncio.sleep(sleep_s)

        # BAFTA slugs
        slugs = (((AWARDS_SOURCES.get("awards", {}) or {}).get("bafta", {}) or {}).get("known_category_slugs", []) or [])
        for slug in slugs[:25]:
            key = f"bafta:{_norm(slug)}"
            if (not force) and _cache_get(key):
                continue
            try:
                data = _sync_awards_bafta(slug)
                if data:
                    _cache_set(key, data); done += 1
                else:
                    failed += 1
            except Exception as e:
                logger.warning("sync_all: BAFTA %s failed: %s", slug, e); failed += 1
            await asyncio.sleep(sleep_s)

        # GJA recent years
        yb = max(0, int(gja_years_back))
        for y in range(now_year - yb, now_year + 1):
            key = f"gja:{y}"
            if (not force) and _cache_get(key):
                continue
            try:
                data = _sync_awards_gja_year(y)
                if data:
                    _cache_set(key, data); done += 1
                else:
                    failed += 1
            except Exception as e:
                logger.warning("sync_all: GJA %s failed: %s", y, e); failed += 1
            await asyncio.sleep(sleep_s)

        await interaction.followup.send(f"Sync-all completed. Updated: {done}, failed: {failed}.", ephemeral=True)
    except Exception as e:
        logger.warning("sync_all error: %s", e)
        await interaction.followup.send("Sync-all failed. Try again later.", ephemeral=True)

@awards_group.command(name="autosync", description="Admin: enable/disable weekly awards autosync (cache refresh).")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(enabled="Enable weekly autosync", gja_years_back="Years back for GJA", sleep_seconds="Delay between requests", bafta_slug_limit="How many BAFTA slugs to sync (max 25)")
async def awards_autosync(interaction: discord.Interaction, enabled: bool, gja_years_back: int = 2, sleep_seconds: int = 2, bafta_slug_limit: int = 25):
    if not await enforce_rate_limit(interaction, "awards_autosync", cooldown_seconds=10):
        return
    BOT_CFG["awards_autosync_enabled"] = bool(enabled)
    BOT_CFG["awards_autosync_gja_years_back"] = max(0, int(gja_years_back))
    BOT_CFG["awards_autosync_sleep_seconds"] = max(0, int(sleep_seconds))
    BOT_CFG["awards_autosync_bafta_slug_limit"] = max(1, min(25, int(bafta_slug_limit)))
    save_bot_cfg()
    state = "enabled" if enabled else "disabled"
    await interaction.response.send_message(f"Weekly awards autosync is now {state}.", ephemeral=True)


@awards_group.command(name="sync_batch", description="Admin: batch sync official award pages into cache (best-effort).")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(award="bafta|gja", start="Start year (GJA)", end="End year (GJA)", bafta_all="BAFTA: sync all known slugs", force="Force refresh")
async def awards_sync_batch(interaction: discord.Interaction, award: str, start: int = 0, end: int = 0, bafta_all: bool = True, force: bool = False):
    if not await enforce_rate_limit(interaction, "awards_sync_batch", cooldown_seconds=30):
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    aid = _norm(award)
    done = 0
    failed = 0

    try:
        if aid == "bafta":
            slugs = (((AWARDS_SOURCES.get("awards", {}) or {}).get("bafta", {}) or {}).get("known_category_slugs", []) or [])
            if not bafta_all and slugs:
                slugs = slugs[:1]
            for slug in slugs[:25]:
                key = f"bafta:{_norm(slug)}"
                if _cache_get(key) and not force:
                    continue
                try:
                    data = _sync_awards_bafta(slug)
                    if data:
                        _cache_set(key, data); done += 1
                    else:
                        failed += 1
                except Exception:
                    failed += 1
            await interaction.followup.send(f"BAFTA batch sync complete. Updated: {done}, failed: {failed}.", ephemeral=True)
            return

        if aid == "gja":
            now_year = datetime.utcnow().year
            if start <= 0:
                start = now_year - 2
            if end <= 0:
                end = now_year
            if end < start:
                start, end = end, start
            for y in range(start, end + 1):
                key = f"gja:{y}"
                if _cache_get(key) and not force:
                    continue
                try:
                    data = _sync_awards_gja_year(y)
                    if data:
                        _cache_set(key, data); done += 1
                    else:
                        failed += 1
                except Exception:
                    failed += 1
            await interaction.followup.send(f"GJA batch sync complete for {start}-{end}. Updated: {done}, failed: {failed}.", ephemeral=True)
            return

        await interaction.followup.send("Unsupported award for batch sync. Use: bafta or gja.", ephemeral=True)
    except Exception as e:
        logger.warning("Batch sync error: %s", e)
        await interaction.followup.send("Batch sync failed. Try again later.", ephemeral=True)

@awards_group.command(name="sync", description="Admin: sync official award pages into cache (best-effort).")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(award="bafta|dice|gja", param="BAFTA: category slug. GJA: year. DICE: ignored.", force="Force refresh")
async def awards_sync(interaction: discord.Interaction, award: str, param: str = "", force: bool = False):
    if not await enforce_rate_limit(interaction, "awards_sync", cooldown_seconds=15):
        return
    aid = _norm(award)
    try:
        if aid == "bafta":
            slug = _norm(param) or "best-game"
            key = f"bafta:{slug}"
            if _cache_get(key) and not force:
                await interaction.response.send_message("Cache already exists. Use force:true to refresh.", ephemeral=True)
                return
            data = _sync_awards_bafta(slug)
            if not data:
                await interaction.response.send_message("BAFTA sync failed (no data).", ephemeral=True)
                return
            _cache_set(key, data)
            await interaction.response.send_message(f"BAFTA cache updated for slug: {slug}", ephemeral=True)
            return

        if aid == "dice":
            key = "dice"
            if _cache_get(key) and not force:
                await interaction.response.send_message("Cache already exists. Use force:true to refresh.", ephemeral=True)
                return
            data = _sync_awards_dice_hub()
            if not data:
                await interaction.response.send_message("DICE sync failed (no data).", ephemeral=True)
                return
            _cache_set(key, data)
            await interaction.response.send_message("DICE cache updated (results pages list).", ephemeral=True)
            return

        if aid == "gja":
            year = int(param) if str(param).strip().isdigit() else datetime.utcnow().year
            key = f"gja:{year}"
            if _cache_get(key) and not force:
                await interaction.response.send_message("Cache already exists. Use force:true to refresh.", ephemeral=True)
                return
            data = _sync_awards_gja_year(year)
            if not data:
                await interaction.response.send_message("GJA sync failed (no data).", ephemeral=True)
                return
            _cache_set(key, data)
            await interaction.response.send_message(f"GJA cache updated for year: {year}", ephemeral=True)
            return

        await interaction.response.send_message("Unsupported award for sync. Use: bafta, dice, gja.", ephemeral=True)
    except Exception as e:
        logger.warning("Awards sync error: %s", e)
        await interaction.response.send_message("Sync failed. Try again later.", ephemeral=True)

@awards_group.command(name="lookup", description="Lookup award winners by award, year, category, and optional genre.")
@app_commands.describe(award="tga|bafta|dice|gja", year="Year (e.g., 2025)", category="Category name (e.g., Game of the Year)", genre="Optional genre filter (e.g., rpg, action, all)")
async def awards_lookup(interaction: discord.Interaction, award: str, year: int, category: str, genre: str = "all", bafta_slug: str = ""):
    if not await enforce_rate_limit(interaction, "awards_lookup", cooldown_seconds=10):
        return
    award_id = (award or "").strip().lower()
    cat_norm = (category or "").strip().lower()
    gen_norm = (genre or "all").strip().lower()

    # Find matches
    for a in (AWARDS_REG.get("awards", []) or []):
        if a.get("award_id","").lower() != award_id:
            continue
        entries = a.get("categories", []) or []
        matches = [e for e in entries if int(e.get("year",0))==int(year) and e.get("category","").lower()==cat_norm and (gen_norm=="all" or (e.get("genre","all").lower()==gen_norm))]
    if not matches:
        # CACHE_FALLBACK: try sync cache for BAFTA/GJA
        if award_id == "bafta":
            slug = _norm(bafta_slug) or _norm(category).replace(" ", "-")
            key = f"bafta:{slug}"
            c = _cache_get(key) if "_cache_get" in globals() else {}
            years = (c.get("years", {}) or {})
            w = years.get(int(year))
            if w:
                embed = discord.Embed(title=f"BAFTA Games Awards — {slug} ({year})", description=f"Winner: **{w}**")
                src = c.get("source_url","")
                if src and _allowed_domain("awards", src):
                    embed.add_field(name="Official source", value=src, inline=False)
                await interaction.response.send_message(embed=embed)
                return
            await interaction.response.send_message("No match in registry or cache. Tip: run /awards sync award:bafta param:<slug> and try again.")
            return

        if award_id == "gja":
            key = f"gja:{int(year)}"
            c = _cache_get(key) if "_cache_get" in globals() else {}
            winners = (c.get("winners", {}) or {})
            cat_norm = (category or "").strip().lower()
            found = None
            for k,v in winners.items():
                if k.strip().lower() == cat_norm:
                    found = (k,v); break
            if not found:
                for k,v in winners.items():
                    if cat_norm and cat_norm in k.strip().lower():
                        found = (k,v); break
            if found:
                k,v = found
                embed = discord.Embed(title=f"Golden Joystick Awards — {k} ({year})", description=f"Winner: **{v}**")
                src = c.get("source_url","")
                if src and _allowed_domain("awards", src):
                    embed.add_field(name="Organizer source", value=src, inline=False)
                await interaction.response.send_message(embed=embed)
                return
            await interaction.response.send_message("No match in registry or cache. Tip: run /awards sync award:gja param:<year> and try again.")
            return

        await interaction.response.send_message("No match found in the registry for that award/year/category/genre.")
        return

    await interaction.response.send_message("Unknown award id. Use: tga, bafta, dice, gja.")

@awards_group.command(name="list", description="List categories for an award with pagination.")
@app_commands.describe(award="tga|bafta|dice|gja", year="Optional year filter", page="Page number (starts at 1)")
async def awards_list(interaction: discord.Interaction, award: str, year: int = 0, page: int = 1):
    if not await enforce_rate_limit(interaction, "awards_list", cooldown_seconds=10):
        return
    award_id = (award or "").strip().lower()
    page = max(1, int(page))
    page_size = 8

    for a in (AWARDS_REG.get("awards", []) or []):
        if a.get("award_id","").lower() != award_id:
            continue
        entries = a.get("categories", []) or []
        if year:
            entries = [e for e in entries if int(e.get("year",0))==int(year)]
        # build list lines
        lines = [f"• {e.get('year')} — **{e.get('category')}** — {e.get('winner')} (genre: {e.get('genre','all')})" for e in entries]
        if not lines:
            await interaction.response.send_message("No entries found for that filter.")
            return
        total_pages = (len(lines)+page_size-1)//page_size
        start = (page-1)*page_size
        end = start+page_size
        chunk = lines[start:end]
        if not chunk:
            await interaction.response.send_message("That page is out of range.")
            return
        embed = discord.Embed(title=f"Awards — {a.get('award_name','Award')} entries (Page {page}/{total_pages})")
        embed.description = "\n".join(chunk[:page_size])
        await interaction.response.send_message(embed=embed)
        return

    await interaction.response.send_message("Unknown award id. Use: tga, bafta, dice, gja.")


def _find_award_entries(award_id: str, year: int, category: str):
    awards = (AWARDS_REG.get("awards", []) or [])
    for a in awards:
        if a.get("award_id") != award_id:
            continue
        entries = a.get("categories", []) or []
        cat_norm = (category or "").strip().lower()
        out = [e for e in entries if int(e.get("year", 0)) == int(year) and (e.get("category","").lower() == cat_norm)]
        return a.get("award_name","Award"), out
    return "Award", []

@awards_group.command(name="tga", description="Lookup The Game Awards winners by year and category.")
@app_commands.describe(year="Year (e.g., 2023)", category="Category name (e.g., Game of the Year)")
async def awards_tga(interaction: discord.Interaction, year: int, category: str):
    if not await enforce_rate_limit(interaction, "awards_tga", cooldown_seconds=10):
        return
    award_name, matches = _find_award_entries("tga", year, category)
    if not matches:
        await interaction.response.send_message("No match found in the registry for that year/category.")
        return
    m = matches[0]
    winner = m.get("winner","(unknown)")
    src = m.get("source_url","")
    embed = discord.Embed(title=f"{award_name} — {category} ({year})", description=f"Winner: **{winner}**")
    if src and _allowed_domain("awards", src):
        embed.add_field(name="Official source", value=src, inline=False)
    await interaction.response.send_message(embed=embed)

@awards_group.command(name="sources", description="Show official award sources used.")
async def awards_sources(interaction: discord.Interaction):
    sources = (AWARDS_REG.get("sources", []) or [])
    if not sources:
        await interaction.response.send_message("No award sources configured.")
        return
    embed = discord.Embed(title="Awards — Official sources")
    for s in sources[:10]:
        embed.add_field(name=s.get("name","Source"), value=s.get("url",""), inline=False)
    await interaction.response.send_message(embed=embed)

bot.tree.add_command(awards_group)


@tasks.loop(hours=168)  # weekly
async def weekly_freegames_task():
    channel_id = (BOT_CFG or {}).get("freegames_announce_channel_id")
    if not channel_id:
        return
    channel = bot.get_channel(int(channel_id))
    if not channel:
        return
    try:
        # Reuse freegames embed builder by calling internal helper via a lightweight duplication:
        embed = discord.Embed(title="Weekly Free Games — Official sources", description="Use the buttons to open official pages. (Epic list is best-effort.)")
        sources = (FREEGAMES_REG.get("sources", []) or []) if "FREEGAMES_REG" in globals() else []
        epic_items = []
        try:
            epic_items = _epic_free_games() if "_epic_free_games" in globals() else []
        except Exception:
            epic_items = []
        if epic_items:
            embed.description = "Current Epic promotions (best-effort):\n" + "\n".join([f"• **{t}**" for t,_ in epic_items[:5]])

        class _FGView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=180)
                for s in sources[:4]:
                    url = s.get("url","")
                    name = s.get("name","Source")
                    if url and _allowed_domain("gaming_deals", url):
                        self.add_item(discord.ui.Button(label=name[:80], url=url))
                for title, url in epic_items[:3]:
                    self.add_item(discord.ui.Button(label=f"Epic: {title}"[:80], url=url))

        await channel.send(embed=embed, view=_FGView())
        logger.info("Posted weekly free games update to channel %s", channel_id)
    except Exception as e:
        logger.warning("Weekly free games post failed: %s", e)

@weekly_freegames_task.before_loop
async def before_weekly_freegames_task():
    await bot.wait_until_ready()

@tasks.loop(hours=168)  # weekly
async def weekly_awards_task():
    # Optional weekly refresh (disabled by default)
    if not (BOT_CFG or {}).get("awards_autosync_enabled", False):
        return
    try:
        sleep_s = int((BOT_CFG or {}).get("awards_autosync_sleep_seconds", 2))
        slug_limit = int((BOT_CFG or {}).get("awards_autosync_bafta_slug_limit", 25))
        years_back = int((BOT_CFG or {}).get("awards_autosync_gja_years_back", 2))
        now_year = datetime.utcnow().year

        # DICE hub
        try:
            data = _sync_awards_dice_hub()
            if data:
                _cache_set("dice", data)
        except Exception as e:
            logger.warning("Weekly awards: DICE sync failed: %s", e)
        await asyncio.sleep(max(0, sleep_s))

        # BAFTA batch (known slugs)
        try:
            slugs = (((AWARDS_SOURCES.get("awards", {}) or {}).get("bafta", {}) or {}).get("known_category_slugs", []) or [])
            for slug in slugs[:max(1, slug_limit)]:
                key = f"bafta:{_norm(slug)}"
                try:
                    data = _sync_awards_bafta(slug)
                    if data:
                        _cache_set(key, data)
                except Exception as e:
                    logger.warning("Weekly awards: BAFTA slug %s failed: %s", slug, e)
                await asyncio.sleep(max(0, sleep_s))
        except Exception as e:
            logger.warning("Weekly awards: BAFTA batch failed: %s", e)

        # GJA recent years
        try:
            for y in range(now_year - max(0, years_back), now_year + 1):
                key = f"gja:{y}"
                try:
                    data = _sync_awards_gja_year(y)
                    if data:
                        _cache_set(key, data)
                except Exception as e:
                    logger.warning("Weekly awards: GJA year %s failed: %s", y, e)
                await asyncio.sleep(max(0, sleep_s))
        except Exception as e:
            logger.warning("Weekly awards: GJA batch failed: %s", e)

        logger.info("Weekly awards autosync completed.")
    except Exception as e:
        logger.warning("Weekly awards autosync failed: %s", e)

@weekly_awards_task.before_loop
async def before_weekly_awards_task():
    await bot.wait_until_ready()



    # --- /art commands ---
    art_group = app_commands.Group(name="art", description="Fine art: painters, museums, and images (official sources).")

    @art_group.command(name="painter", description="Get one major painter (last ~200 years) with one artwork image (official museum source when available).")
    async def art_painter(interaction: discord.Interaction):
        if not await enforce_rate_limit(interaction, "art_painter", cooldown_seconds=5):
            return
        items = (PAINTERS_REGISTRY.get("items", []) or [])
        if not items:
            await interaction.response.send_message("Painter registry is empty.")
            return
        item = random.choice(items)

        embed = discord.Embed(
            title=item.get("name","Painter"),
            description=f"{item.get('lifespan','')} • {item.get('movement','')}".strip(" •")
        )
        embed.add_field(name="Why significant", value=item.get("why_significant","(n/a)"), inline=False)
        if item.get("museum"):
            embed.add_field(name="Museum source", value=item.get("museum"), inline=True)

        # Attempt official image via Met API if met_object_id present
        img_url = ""
        obj_title = ""
        if item.get("met_object_id"):
            data = await met_object(int(item["met_object_id"]))
            obj_title = data.get("title","")
            img_url = data.get("primaryImage") or data.get("primaryImageSmall") or ""
            if obj_title:
                embed.add_field(name="Artwork", value=obj_title, inline=False)
            # Show image only if present
            if img_url:
                embed.set_image(url=img_url)

        src = item.get("source_url","")
        if src:
            embed.add_field(name="Official link", value=src, inline=False)

        await interaction.response.send_message(embed=embed)

    bot.tree.add_command(art_group)


    # --- /food commands ---
    food_group = app_commands.Group(name="food", description="Food history & gastronomy (official/academic sources).")

    @food_group.command(name="chocolate_europe_history", description="Europe: a short, source-based history of chocolate (past few centuries).")
    async def food_chocolate_europe_history(interaction: discord.Interaction):
        if not await enforce_rate_limit(interaction, "food_chocolate_europe_history", cooldown_seconds=10):
            return
        embed = discord.Embed(
            title="Chocolate in Europe: brief history (source-based)",
            description=(
                "Chocolate entered Europe via Spain and became a fashionable drink among elites; later industrialization enabled mass production "
                "and broader access."
            )
        )
        embed.add_field(
            name="Sources",
            value=(
                "Britannica: https://www.britannica.com/topic/chocolate\n"
                "Smithsonian Magazine: https://www.smithsonianmag.com/arts-culture/a-brief-history-of-chocolate-21860917/\n"
                "British Museum: https://www.britishmuseum.org/blog/18th-century-chocolate-champions"
            ),
            inline=False,
        )
        await interaction.response.send_message(embed=embed)

    @food_group.command(name="michelin_star_meaning", description="Explain what Michelin Stars mean (official Michelin Guide source).")
    async def food_michelin_star_meaning(interaction: discord.Interaction):
        if not await enforce_rate_limit(interaction, "food_michelin_star_meaning", cooldown_seconds=10):
            return
        embed = discord.Embed(
            title="What is a MICHELIN Star?",
            description="Official Michelin Guide explainer: what 1, 2, and 3 Stars represent and how restaurants are evaluated."
        )
        embed.add_field(name="Official source", value="https://guide.michelin.com/tr/en/article/features/what-is-a-michelin-star", inline=False)
        embed.add_field(name="Note", value="For full lists of starred restaurants, use the official MICHELIN Guide site search.", inline=False)
        await interaction.response.send_message(embed=embed)

    bot.tree.add_command(food_group)


# --- /restaurants commands ---
restaurants_group = app_commands.Group(name="restaurants", description="Official guides and major restaurant awards (source-validated).")

@restaurants_group.command(name="michelin_starred", description="Show one Michelin-starred restaurant (seed registry) and link to official Michelin Guide search.")
async def restaurants_michelin_starred(interaction: discord.Interaction):
    if not await enforce_rate_limit(interaction, "restaurants_michelin_starred", cooldown_seconds=5):
        return
    items = (MICHELIN_REGISTRY.get("items", []) or [])
    if not items:
        await interaction.response.send_message("Michelin registry is empty.")
        return
    r = random.choice(items)
    embed = discord.Embed(title=r.get("name","Restaurant"))
    loc = " • ".join([x for x in [r.get("city",""), r.get("country","")] if x])
    if loc:
        embed.description = loc
    stars = r.get("stars")
    if stars:
        embed.add_field(name="Stars (seed)", value=str(stars), inline=True)
    embed.add_field(name="Official Michelin Guide", value="https://guide.michelin.com/", inline=False)
    embed.add_field(name="Note", value="Use the official Michelin Guide search for the latest starred status and details.", inline=False)
    await interaction.response.send_message(embed=embed)

@restaurants_group.command(name="michelin_find", description="Get an official Michelin Guide search link for a city or country.")
@app_commands.describe(query="City or country (e.g., Brussels, Belgium, Tokyo)")
async def restaurants_michelin_find(interaction: discord.Interaction, query: str):
    if not await enforce_rate_limit(interaction, "restaurants_michelin_find", cooldown_seconds=5):
        return
    q = (query or "").strip()
    if not q:
        await interaction.response.send_message("Please provide a city or country.")
        return
    # Michelin site handles search; we provide the official entry point.
    embed = discord.Embed(title="MICHELIN Guide search", description=f"Search for: **{q}**")
    embed.add_field(name="Official site", value="https://guide.michelin.com/", inline=False)
    embed.add_field(name="Tip", value="Use the search box on the site to filter by city, cuisine, and stars.", inline=False)
    await interaction.response.send_message(embed=embed)

@restaurants_group.command(name="award_winner", description="Show one non‑Michelin award-winning restaurant item (seed registry), optionally filtered by year.")
@app_commands.describe(year="Optional year filter (e.g., 2024). Use 0 for any.", award="Optional award filter (e.g., 'World\'s 50 Best Restaurants'). Leave blank for any.")
async def restaurants_award_winner(interaction: discord.Interaction, year: int = 0, award: str = ""):
    if not await enforce_rate_limit(interaction, "restaurants_award_winner", cooldown_seconds=5):
        return
    items = (RESTAURANT_AWARDS_REGISTRY.get("items", []) or [])
    if award:
        a = award.strip().lower()
        items = [x for x in items if (x.get("award","").lower() == a)]
    if year and year > 0:
        items = [x for x in items if int(x.get("year",0) or 0) == int(year)]
    if not items:
        await interaction.response.send_message("No matching entries in the restaurant awards registry.")
        return
    x = random.choice(items)
    embed = discord.Embed(title=str(x.get("name","Restaurant award item")))
    desc = " • ".join([y for y in [x.get("city",""), x.get("country","")] if y])
    if desc:
        embed.description = desc
    embed.add_field(name="Award", value=str(x.get("award","")), inline=False)
    if x.get("year"):
        embed.add_field(name="Year", value=str(x.get("year")), inline=True)
    if x.get("official_url"):
        embed.add_field(name="Official source", value=str(x.get("official_url")), inline=False)
    await interaction.response.send_message(embed=embed)

bot.tree.add_command(restaurants_group)


bot.run(os.getenv("DISCORD_TOKEN"))

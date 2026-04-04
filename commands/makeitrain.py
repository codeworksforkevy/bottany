from __future__ import annotations
# makeitrain.py — Pixel Weather Engine
# All sprites generated with PIL — no external PNG files needed.

import random
from io import BytesIO

import discord
from discord import app_commands
from PIL import Image, ImageDraw

WIDTH  = 512
HEIGHT = 256

# ── Palette ───────────────────────────────────────────────────────────────────
SKY_RAIN  = (20, 24, 28)
SKY_SNOW  = (30, 35, 50)
SKY_FLASH = (200, 200, 210)
GROUND    = (50, 60, 50)
RAIN_COL  = (200, 210, 220)
SNOW_COL  = (240, 240, 255)
TREE_COL  = (36, 120, 60)
TRUNK_COL = (90, 60, 40)
CABIN_COL = (120, 80, 50)
ROOF_COL  = (90, 40, 40)
WATER_COL = (30, 60, 100)


# ── Sprite generators (PIL — no files) ────────────────────────────────────────

def _make_tree(size: int = 24) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    trunk_x = size // 2
    for y in range(size * 14 // 16, size):
        d.point((trunk_x, y), fill=TRUNK_COL + (255,))
    for x in range(size // 4, size * 3 // 4):
        for y in range(size // 6, size * 14 // 16):
            if random.random() < 0.75:
                shade = random.randint(-15, 15)
                col   = tuple(max(0, min(255, c + shade)) for c in TREE_COL)
                d.point((x, y), fill=col + (255,))
    return img


def _make_cabin(w: int = 28, h: int = 24) -> Image.Image:
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    # Walls
    d.rectangle([4, h // 2, w - 4, h - 1], fill=CABIN_COL + (255,))
    # Roof
    for i in range(h // 2):
        d.line([4 + i, h // 2 - i, w - 4 - i, h // 2 - i],
               fill=ROOF_COL + (255,))
    # Window
    d.rectangle([w // 2 - 2, h * 2 // 3, w // 2 + 2, h - 3],
                fill=(200, 220, 240, 220))
    return img


def _make_lake(w: int = 120, h: int = 20) -> Image.Image:
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    d.ellipse([0, 0, w - 1, h - 1], fill=WATER_COL + (200,))
    return img


# ── Scene ─────────────────────────────────────────────────────────────────────

def _build_scene(weather: str) -> list[tuple[Image.Image, int, int]]:
    objects: list[tuple[Image.Image, int, int]] = []
    # Optional lake
    if random.random() < 0.4:
        lake = _make_lake()
        objects.append((lake, random.randint(40, WIDTH - 160), HEIGHT - 25))
    # Trees
    for _ in range(random.randint(10, 22)):
        tree = _make_tree(random.randint(18, 30))
        x = random.randint(0, WIDTH - 32)
        y = random.randint(HEIGHT - 90, HEIGHT - 36)
        objects.append((tree, x, y))
    # Cabin
    if random.random() < 0.65:
        cabin = _make_cabin()
        x = random.randint(80, WIDTH - 120)
        objects.append((cabin, x, HEIGHT - 28))
    return objects


# ── Particles ─────────────────────────────────────────────────────────────────

class _Rain:
    __slots__ = ("x", "y", "vx", "vy", "length")

    def __init__(self) -> None:
        self.x      = random.uniform(0, WIDTH)
        self.y      = random.uniform(-HEIGHT, 0)
        self.vx     = random.uniform(-0.5, 0.5)
        self.vy     = random.uniform(8, 12)
        self.length = random.randint(5, 9)

    def update(self) -> bool:
        self.x += self.vx
        self.y += self.vy
        if self.y > HEIGHT:
            self.x = random.uniform(0, WIDTH)
            self.y = random.uniform(-100, 0)
            return True   # splash
        return False


class _Snow:
    __slots__ = ("x", "y", "vx", "vy")

    def __init__(self) -> None:
        self.x  = random.uniform(0, WIDTH)
        self.y  = random.uniform(-HEIGHT, 0)
        self.vx = random.uniform(-1, 1)
        self.vy = random.uniform(1, 3)

    def update(self) -> None:
        self.x += self.vx
        self.y += self.vy
        if self.y > HEIGHT:
            self.x = random.uniform(0, WIDTH)
            self.y = random.uniform(-50, 0)


# ── Engine ────────────────────────────────────────────────────────────────────

class WeatherEngine:
    def __init__(self, weather: str = "rain") -> None:
        self.weather   = weather
        self.scene     = _build_scene(weather)
        self.lightning = 0
        self.splashes: list[tuple[int, int, int]] = []  # (x, y, life)

        if weather == "rain":
            self.particles: list = [_Rain() for _ in range(900)]
        else:
            self.particles = [_Snow() for _ in range(400)]

    def update(self) -> None:
        new_splashes = []
        for p in self.particles:
            if self.weather == "rain":
                splashed = p.update()
                if splashed:
                    new_splashes.append((int(p.x), HEIGHT - 2, 4))
            else:
                p.update()
        self.splashes = [(x, y, l - 1) for x, y, l in self.splashes if l > 1]
        self.splashes += new_splashes
        if self.weather == "rain" and random.random() < 0.025:
            self.lightning = 2

    def render(self) -> Image.Image:
        sky = SKY_FLASH if self.lightning > 0 else (
            SKY_RAIN if self.weather == "rain" else SKY_SNOW
        )
        if self.lightning > 0:
            self.lightning -= 1

        img = Image.new("RGB", (WIDTH, HEIGHT), sky)

        # Scene sprites
        for sprite, x, y in self.scene:
            img.paste(sprite, (x, y), sprite)

        draw = ImageDraw.Draw(img)

        # Ground strip
        draw.rectangle([0, HEIGHT - 8, WIDTH, HEIGHT], fill=GROUND)

        # Particles
        if self.weather == "rain":
            for p in self.particles:
                px, py = int(p.x), int(p.y)
                for i in range(p.length):
                    ry = py - i
                    if 0 <= ry < HEIGHT and 0 <= px < WIDTH:
                        draw.point((px, ry), fill=RAIN_COL)
            for x, y, _ in self.splashes:
                draw.point((x, y), fill=(220, 220, 230))
        else:
            for p in self.particles:
                px, py = int(p.x), int(p.y)
                if 0 <= py < HEIGHT and 0 <= px < WIDTH:
                    draw.point((px, py), fill=SNOW_COL)
                    if random.random() < 0.3:
                        draw.point((px + 1, py), fill=SNOW_COL)

        return img


# ── GIF builder ───────────────────────────────────────────────────────────────

def _render_gif(weather: str, n_frames: int = 40, fps: int = 60) -> BytesIO:
    engine = WeatherEngine(weather)
    frames: list[Image.Image] = []
    for _ in range(n_frames):
        engine.update()
        frames.append(engine.render())

    buf = BytesIO()
    frames[0].save(
        buf,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=max(16, 1000 // fps),
        loop=0,
        optimize=False,
    )
    buf.seek(0)
    return buf


# ── Registration ──────────────────────────────────────────────────────────────

async def register(bot: discord.Client, data_dir: str) -> None:
    """Register /makeitrain commands. Called by main.py loader."""
    if bot.tree.get_command("makeitrain"):
        return

    group = app_commands.Group(
        name="makeitrain",
        description="Pixel weather engine",
    )

    @group.command(name="rain", description="Generate a pixel rain animation")
    async def rain_cmd(interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        buf = _render_gif("rain")
        await interaction.followup.send(
            file=discord.File(buf, filename="rain.gif")
        )

    @group.command(name="snow", description="Generate a pixel snow animation")
    async def snow_cmd(interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        buf = _render_gif("snow")
        await interaction.followup.send(
            file=discord.File(buf, filename="snow.gif")
        )

    bot.tree.add_command(group)

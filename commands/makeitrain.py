import random
from io import BytesIO
import discord
from discord import app_commands
from PIL import Image, ImageDraw, ImageOps

WIDTH = 512
HEIGHT = 256

# =====================================================
# SPRITES LOADING
# =====================================================
from pathlib import Path
ASSETS_DIR = Path("assets/sprites")

terrain_img = Image.open(ASSETS_DIR / "terrain.png").convert("RGBA")
trees_img = Image.open(ASSETS_DIR / "trees.png").convert("RGBA")
houses_img = Image.open(ASSETS_DIR / "houses.png").convert("RGBA")
animals_img = Image.open(ASSETS_DIR / "animals.png").convert("RGBA")
rain_img = Image.open(ASSETS_DIR / "rain.png").convert("RGBA")

# =====================================================
# SCENE DEFINITIONS
# =====================================================

SCENE_TEMPLATES = ["lake", "forest_cabin", "modern_house", "forest_with_deer"]

def generate_scene():
    """Randomly selects a scene template and returns sprite list with positions."""
    scene_type = random.choice(SCENE_TEMPLATES)
    scene = []

    if scene_type == "lake":
        # Terrain
        scene.append((terrain_img, 0, HEIGHT-50))
        # Trees around lake
        for i in range(5):
            scene.append((trees_img, random.randint(20, WIDTH-40), HEIGHT-70))
    elif scene_type == "forest_cabin":
        scene.append((terrain_img, 0, HEIGHT-50))
        scene.append((houses_img, random.randint(100, 300), HEIGHT-60))
        for i in range(7):
            scene.append((trees_img, random.randint(0, WIDTH-30), HEIGHT-70))
    elif scene_type == "modern_house":
        scene.append((terrain_img, 0, HEIGHT-50))
        scene.append((houses_img, random.randint(120, 320), HEIGHT-60))
        for i in range(4):
            scene.append((trees_img, random.randint(0, WIDTH-30), HEIGHT-70))
    elif scene_type == "forest_with_deer":
        scene.append((terrain_img, 0, HEIGHT-50))
        for i in range(6):
            scene.append((trees_img, random.randint(0, WIDTH-30), HEIGHT-70))
        for i in range(2):
            scene.append((animals_img, random.randint(50, WIDTH-50), HEIGHT-40))
    return scene

# =====================================================
# PARTICLES
# =====================================================

class RainParticle:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = random.uniform(0, WIDTH)
        self.y = random.uniform(-HEIGHT, 0)
        self.vx = random.uniform(-0.3, 0.3)
        self.vy = random.uniform(8, 12)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.y > HEIGHT:
            splash = (self.x, HEIGHT-2)
            self.reset()
            return splash
        return None

class Splash:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.life = 4

# =====================================================
# WEATHER ENGINE
# =====================================================

class WeatherEngine:
    def __init__(self):
        self.rain = [RainParticle() for _ in range(900)]
        self.splashes = []
        self.scene = generate_scene()
        self.lightning = 0

    def update(self):
        new_splashes = []
        for p in self.rain:
            splash = p.update()
            if splash:
                new_splashes.append(Splash(*splash))
        self.splashes += new_splashes
        for s in self.splashes:
            s.life -= 1
        self.splashes = [s for s in self.splashes if s.life > 0]
        if random.random() < 0.02:
            self.lightning = 2

    def render(self):
        sky = (20, 25, 30)
        if self.lightning > 0:
            sky = (200, 200, 210)
            self.lightning -= 1

        img = Image.new("RGB", (WIDTH, HEIGHT), sky)

        # Draw scene
        for sprite, x, y in self.scene:
            img.paste(sprite, (x, y), sprite)

        # Ground
        d = ImageDraw.Draw(img)
        d.rectangle([0, HEIGHT-4, WIDTH, HEIGHT], fill=(50, 60, 50))

        # Draw rain
        for p in self.rain:
            px, py = int(p.x), int(p.y)
            img.alpha_composite(rain_img, (px, py))

        # Draw splashes
        for s in self.splashes:
            d.point((int(s.x), int(s.y)), fill=(220, 220, 230))

        return img

# =====================================================
# DISCORD COMMAND
# =====================================================

def register(bot: discord.Client):
    group = app_commands.Group(
        name="makeitrain",
        description="Pixel Weather Engine v10"
    )

    @group.command(name="scene", description="Generate pixel rain scene")
    async def scene(interaction: discord.Interaction):
        await interaction.response.defer()
        engine = WeatherEngine()
        frames = []
        for _ in range(40):
            engine.update()
            frames.append(engine.render())

        buffer = BytesIO()
        frames[0].save(
            buffer,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=16,
            loop=0
        )
        buffer.seek(0)
        await interaction.followup.send(file=discord.File(buffer, "rain.gif"))

    bot.tree.add_command(group)

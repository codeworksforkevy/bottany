import discord
from discord.ext import commands
from discord import app_commands

from PIL import Image, ImageDraw
from io import BytesIO
import random


# ======================================
# WORLD SETTINGS
# ======================================

WIDTH = 512
HEIGHT = 256

PIXEL = 3

GW = WIDTH // PIXEL
GH = HEIGHT // PIXEL

SKY = (18,22,26)
GROUND = (70,80,70)

RAIN = (200,210,220)
RAIN_DIM = (160,170,180)

TREE = (36,120,60)
TRUNK = (90,60,40)

CABIN = (120,80,50)
ROOF = (90,40,40)

SPLASH = (230,240,255)


# ======================================
# SPRITE GENERATOR
# ======================================

def sprite_tree():

    size = 16
    img = Image.new("RGBA",(size,size),(0,0,0,0))
    d = ImageDraw.Draw(img)

    # trunk
    for y in range(10,16):
        d.point((7,y),fill=TRUNK)

    # leaves
    for x in range(3,13):
        for y in range(2,10):

            if random.random()<0.7:
                d.point((x,y),fill=TREE)

    return img


def sprite_cabin():

    size=20
    img=Image.new("RGBA",(size,size),(0,0,0,0))
    d=ImageDraw.Draw(img)

    for x in range(4,16):
        for y in range(10,18):
            d.point((x,y),fill=CABIN)

    for x in range(3,17):
        d.point((x,10),fill=ROOF)

    return img


# ======================================
# SCENE GENERATOR
# ======================================

def build_scene():

    objects=[]

    for _ in range(random.randint(15,30)):

        tree=sprite_tree()

        x=random.randint(0,WIDTH-50)
        y=random.randint(HEIGHT-80,HEIGHT-40)

        objects.append((tree,x,y))

    if random.random()<0.7:

        cabin=sprite_cabin()

        x=random.randint(100,WIDTH-100)
        y=HEIGHT-60

        objects.append((cabin,x,y))

    return objects


# ======================================
# RAIN PARTICLE
# ======================================

class Rain:

    def __init__(self):

        self.x=random.uniform(0,WIDTH)
        self.y=random.uniform(-HEIGHT,0)

        self.vx=random.uniform(-0.3,0.3)
        self.vy=random.uniform(8,12)

        self.length=random.randint(6,10)


    def update(self):

        self.x+=self.vx
        self.y+=self.vy

        if self.y>HEIGHT:

            self.x=random.uniform(0,WIDTH)
            self.y=random.uniform(-100,0)


    def draw(self,draw):

        for i in range(self.length):

            px=int(self.x)
            py=int(self.y-i)

            if 0<=px<WIDTH and 0<=py<HEIGHT:

                draw.point((px,py),fill=RAIN)


# ======================================
# SPLASH
# ======================================

class Splash:

    def __init__(self,x,y):

        self.x=x
        self.y=y
        self.life=4


    def update(self):
        self.life-=1


    def draw(self,draw):

        if self.life>0:

            draw.point((self.x,self.y),fill=SPLASH)



# ======================================
# FRAME ENGINE
# ======================================

def render_frame(objects,particles,splashes):

    img=Image.new("RGB",(WIDTH,HEIGHT),SKY)
    draw=ImageDraw.Draw(img)

    # sprites
    for sprite,x,y in objects:

        img.paste(sprite,(x,y),sprite)

    # ground
    draw.rectangle(
        [0,HEIGHT-10,WIDTH,HEIGHT],
        fill=GROUND
    )

    # rain
    for p in particles:

        p.update()
        p.draw(draw)

        if p.y>=HEIGHT-10:

            splashes.append(Splash(int(p.x),HEIGHT-10))

    # splash
    for s in splashes:

        s.draw(draw)
        s.update()

    splashes[:]=[s for s in splashes if s.life>0]

    return img


# ======================================
# ANIMATION ENGINE
# ======================================

def generate_animation():

    objects=build_scene()

    particles=[Rain() for _ in range(900)]

    splashes=[]

    frames=[]

    for _ in range(40):

        frame=render_frame(objects,particles,splashes)

        frames.append(frame)

    buffer=BytesIO()

    frames[0].save(
        buffer,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=16,
        loop=0
    )

    buffer.seek(0)

    return buffer


# ======================================
# DISCORD COMMAND
# ======================================

class MakeItRain(commands.Cog):

    def __init__(self,bot):
        self.bot=bot


    @app_commands.command(
        name="makeitrain",
        description="Stardew-style pixel rain scene"
    )

    async def makeitrain(self,interaction:discord.Interaction):

        await interaction.response.defer()

        gif=generate_animation()

        await interaction.followup.send(
            file=discord.File(gif,"stardew_rain.gif")
        )


async def setup(bot):

    await bot.add_cog(MakeItRain(bot))

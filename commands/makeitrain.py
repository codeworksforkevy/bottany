import discord
from discord.ext import commands
from discord import app_commands

import random
from PIL import Image, ImageDraw
from io import BytesIO


WIDTH = 512
HEIGHT = 256

PIXEL = 3

GRID_W = WIDTH // PIXEL
GRID_H = HEIGHT // PIXEL


RAIN_COLOR = (200,210,220)
SPLASH_COLOR = (220,230,240)

SKY_COLOR = (20,24,28)

TREE = (34,139,34)
TRUNK = (90,60,40)

GROUND = (60,70,60)

CABIN = (120,80,50)

WATER = (40,90,120)


# ---------------------------
# PARTICLE SYSTEM
# ---------------------------

class RainParticle:

    def __init__(self):

        self.x = random.randint(0, GRID_W)
        self.y = random.randint(-GRID_H, 0)

        self.vx = random.uniform(-0.2,0.2)
        self.vy = random.uniform(0.9,1.6)

        self.length = random.randint(2,4)


    def update(self):

        self.x += self.vx
        self.y += self.vy

        if self.y > GRID_H:

            self.x = random.randint(0, GRID_W)
            self.y = random.randint(-20,0)


    def draw(self, draw):

        for i in range(self.length):

            px = int(self.x)
            py = int(self.y-i)

            if 0 <= px < GRID_W and 0 <= py < GRID_H:

                draw.point((px,py),fill=RAIN_COLOR)



# ---------------------------
# SPLASH SYSTEM
# ---------------------------

class Splash:

    def __init__(self,x,y):

        self.x=x
        self.y=y

        self.life=3


    def update(self):

        self.life-=1


    def draw(self,draw):

        if self.life>0:

            draw.point((self.x,self.y),fill=SPLASH_COLOR)



# ---------------------------
# TERRAIN
# ---------------------------

def draw_ground(draw):

    for x in range(GRID_W):

        for y in range(GRID_H-5,GRID_H):

            draw.point((x,y),fill=GROUND)



# ---------------------------
# TREES
# ---------------------------

def draw_tree(draw,x,y):

    for i in range(6):

        draw.point((x,y-i),fill=TRUNK)

    for dx in range(-3,4):
        for dy in range(-3,1):

            if random.random()<0.7:

                draw.point((x+dx,y-6+dy),fill=TREE)



def generate_forest(draw):

    for _ in range(40):

        x=random.randint(0,GRID_W)
        y=GRID_H-5

        draw_tree(draw,x,y)



# ---------------------------
# CABIN
# ---------------------------

def draw_cabin(draw):

    cx=random.randint(30,GRID_W-30)
    cy=GRID_H-5

    for x in range(-6,6):
        for y in range(-6,0):

            draw.point((cx+x,cy+y),fill=CABIN)

    for x in range(-7,7):

        draw.point((cx+x,cy-6),fill=(80,40,30))



# ---------------------------
# SCENE
# ---------------------------

def draw_scene(draw,scene):

    if scene=="forest":

        generate_forest(draw)

    if scene=="cabin":

        generate_forest(draw)
        draw_cabin(draw)



# ---------------------------
# ENGINE
# ---------------------------

def generate_animation(scene):

    particles=[RainParticle() for _ in range(450)]

    splashes=[]

    frames=[]

    for frame in range(36):

        img=Image.new("RGB",(GRID_W,GRID_H),SKY_COLOR)
        draw=ImageDraw.Draw(img)

        draw_scene(draw,scene)
        draw_ground(draw)

        for p in particles:

            p.update()
            p.draw(draw)

            if int(p.y)>=GRID_H-5:

                splashes.append(Splash(int(p.x),GRID_H-5))

        for s in splashes:

            s.draw(draw)
            s.update()

        splashes=[s for s in splashes if s.life>0]

        img=img.resize((WIDTH,HEIGHT),Image.NEAREST)

        frames.append(img)

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



# ---------------------------
# COMMAND
# ---------------------------

class MakeItRain(commands.Cog):

    def __init__(self,bot):

        self.bot=bot


    @app_commands.command(
        name="makeitrain",
        description="Stardew-style pixel rain"
    )
    @app_commands.describe(
        scene="forest or cabin"
    )

    async def makeitrain(self,interaction:discord.Interaction,scene:str="forest"):

        await interaction.response.defer()

        gif=generate_animation(scene)

        await interaction.followup.send(
            file=discord.File(gif,"pixel_rain.gif")
        )


async def setup(bot):

    await bot.add_cog(MakeItRain(bot))

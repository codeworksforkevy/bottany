import random
from io import BytesIO

import discord
from discord import app_commands

from PIL import Image, ImageDraw

WIDTH = 512
HEIGHT = 256


# =====================================================
# SPRITES
# =====================================================

def tree_sprite():

    img = Image.new("RGBA",(16,20),(0,0,0,0))
    d = ImageDraw.Draw(img)

    for y in range(10,20):
        d.point((8,y),fill=(90,60,40))

    for x in range(2,14):
        for y in range(0,10):
            if random.random()<0.7:
                d.point((x,y),fill=(40,120,60))

    return img


def deer_sprite():

    img = Image.new("RGBA",(14,10),(0,0,0,0))
    d = ImageDraw.Draw(img)

    body=(140,100,60)

    for x in range(2,10):
        d.point((x,6),fill=body)

    d.point((10,5),fill=body)

    for x in (3,7):
        d.point((x,7),fill=body)

    return img


def cabin_sprite():

    img = Image.new("RGBA",(24,20),(0,0,0,0))
    d = ImageDraw.Draw(img)

    for x in range(4,20):
        for y in range(10,18):
            d.point((x,y),fill=(130,90,60))

    for x in range(3,21):
        d.point((x,10),fill=(90,50,50))

    return img


# =====================================================
# PARTICLES
# =====================================================

class RainParticle:

    def __init__(self):

        self.reset()


    def reset(self):

        self.x=random.uniform(0,WIDTH)
        self.y=random.uniform(-HEIGHT,0)

        self.vx=random.uniform(-0.3,0.3)
        self.vy=random.uniform(8,12)


    def update(self):

        self.x+=self.vx
        self.y+=self.vy

        if self.y>HEIGHT:

            splash=(self.x,HEIGHT-2)

            self.reset()

            return splash

        return None


class Splash:

    def __init__(self,x,y):

        self.x=x
        self.y=y
        self.life=4


# =====================================================
# SCENE
# =====================================================

def generate_scene():

    scene=[]

    for _ in range(random.randint(12,20)):

        scene.append(
            (
                tree_sprite(),
                random.randint(0,WIDTH-20),
                random.randint(HEIGHT-100,HEIGHT-40)
            )
        )

    if random.random()<0.8:

        scene.append(
            (
                cabin_sprite(),
                random.randint(200,320),
                HEIGHT-50
            )
        )

    if random.random()<0.6:

        scene.append(
            (
                deer_sprite(),
                random.randint(80,420),
                HEIGHT-25
            )
        )

    return scene


# =====================================================
# ENGINE
# =====================================================

class WeatherEngine:

    def __init__(self):

        self.rain=[RainParticle() for _ in range(900)]
        self.splashes=[]

        self.scene=generate_scene()

        self.lightning=0


    def update(self):

        new_splashes=[]

        for p in self.rain:

            splash=p.update()

            if splash:

                new_splashes.append(Splash(*splash))

        self.splashes+=new_splashes

        for s in self.splashes:
            s.life-=1

        self.splashes=[s for s in self.splashes if s.life>0]

        if random.random()<0.02:
            self.lightning=2


    def render(self):

        sky=(20,25,30)

        if self.lightning>0:
            sky=(200,200,210)
            self.lightning-=1

        img=Image.new("RGB",(WIDTH,HEIGHT),sky)
        d=ImageDraw.Draw(img)

        for sprite,x,y in self.scene:

            img.paste(sprite,(x,y),sprite)

        d.rectangle([0,HEIGHT-4,WIDTH,HEIGHT],fill=(50,60,50))

        for p in self.rain:

            x=int(p.x)
            y=int(p.y)

            for i in range(6):
                d.point((x,y-i),fill=(200,210,220))

        for s in self.splashes:

            d.point((int(s.x),int(s.y)),fill=(220,220,230))

        return img


# =====================================================
# DISCORD COMMAND
# =====================================================

def register(bot):

    group = app_commands.Group(
        name="makeitrain",
        description="Pixel rain scene generator"
    )


    @group.command(name="scene",description="Generate pixel rain scene")
    async def scene(interaction: discord.Interaction):

        await interaction.response.defer()

        engine=WeatherEngine()

        frames=[]

        for _ in range(40):

            engine.update()

            frames.append(engine.render())

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

        await interaction.followup.send(
            file=discord.File(buffer,"rain.gif")
        )

    bot.tree.add_command(group)
